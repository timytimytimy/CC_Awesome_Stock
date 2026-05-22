"""
宏观 → 行业 → 个股 评分联动。

把阶段 1 的宏观结论（信用周期 + PPI 方向）转成对个股得分的加减项：
  1. compute_industry_adjustments() —— 当前宏观状态下每个申万一级行业的加减分
  2. resolve_sw_industry()         —— 雪球/THS 细分行业名 → 申万一级
  3. get_stock_industry()          —— 个股 → 行业名（雪球接口，持久 JSON 缓存）

设计原则：全链路 fail-safe。任一环节取不到数据 → 该股宏观调整 0，不报错、不阻断选股。
政策（policy）不在此模块——按 P0.4 设计原则交给分析阶段 LLM 判断。
"""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path
from typing import Optional

import yaml

_MAPPING_FILE = (
    Path(__file__).resolve().parents[2] / "kb" / "taxonomy" / "macro-industry-mapping.yaml"
)
_CACHE_DIR = Path(__file__).resolve().parents[1] / ".cache"
_INDUSTRY_CACHE_FILE = _CACHE_DIR / "ticker_industry.json"
_INDUSTRY_CACHE_TTL_DAYS = 30

_mapping_cache: Optional[dict] = None
_ticker_industry_cache: Optional[dict] = None


# ────────────────────────────────────────────────────────────
# 映射表加载
# ────────────────────────────────────────────────────────────
def load_macro_industry_map() -> dict:
    """加载 macro-industry-mapping.yaml（带进程内缓存）。"""
    global _mapping_cache
    if _mapping_cache is not None:
        return _mapping_cache
    try:
        with open(_MAPPING_FILE, encoding="utf-8") as f:
            _mapping_cache = yaml.safe_load(f) or {}
    except Exception as e:
        print(f"[WARN] 无法加载 macro-industry-mapping.yaml: {e}", file=sys.stderr)
        _mapping_cache = {}
    return _mapping_cache


# ────────────────────────────────────────────────────────────
# 宏观状态 → 行业加减分
# ────────────────────────────────────────────────────────────
def _phase_key(credit_phase: str) -> Optional[str]:
    """把 classify_credit_cycle 的 phase 文本（如'过热（…）'）归一为 复苏/过热/滞胀/衰退。"""
    if not credit_phase:
        return None
    for key in ("复苏", "过热", "滞胀", "衰退"):
        if key in credit_phase:
            return key
    return None


def compute_industry_adjustments(
    credit_phase: str, ppi_trend: Optional[str] = None
) -> dict[str, float]:
    """
    给定信用周期象限 + PPI 方向，返回 {申万一级行业: 调整分}。
    未在映射表出现的行业 → 不在返回 dict 中（视为 0）。
    """
    mp = load_macro_industry_map()
    adjustments: dict[str, float] = {}

    phase = _phase_key(credit_phase)
    cc = (mp.get("credit_cycle") or {}).get(phase or "", {})
    for ind, score in (cc.get("favored") or {}).items():
        adjustments[ind] = adjustments.get(ind, 0.0) + float(score)
    for ind, score in (cc.get("penalized") or {}).items():
        adjustments[ind] = adjustments.get(ind, 0.0) + float(score)

    # PPI 方向叠加
    if ppi_trend in ("上行", "下行"):
        ppi_map = (mp.get("ppi_direction") or {}).get(ppi_trend, {})
        for ind, score in ppi_map.items():
            adjustments[ind] = adjustments.get(ind, 0.0) + float(score)

    return adjustments


# ────────────────────────────────────────────────────────────
# 细分行业名 → 申万一级
# ────────────────────────────────────────────────────────────
def resolve_sw_industry(raw_name: Optional[str]) -> Optional[str]:
    """雪球/THS 行业名（如'白酒''半导体'）→ 申万一级（如'食品饮料''电子'）。"""
    if not raw_name:
        return None
    mp = load_macro_industry_map()
    alias = mp.get("industry_alias") or {}
    raw = str(raw_name).strip()
    # 先精确命中申万一级名本身
    if raw in alias:
        return raw
    # 关键词包含匹配
    for sw_name, keywords in alias.items():
        for kw in keywords or []:
            if kw and kw in raw:
                return sw_name
    return None


# ────────────────────────────────────────────────────────────
# 个股 → 行业名（雪球接口 + 持久 JSON 缓存）
# ────────────────────────────────────────────────────────────
def _load_industry_cache() -> dict:
    global _ticker_industry_cache
    if _ticker_industry_cache is not None:
        return _ticker_industry_cache
    if _INDUSTRY_CACHE_FILE.exists():
        age_days = (time.time() - _INDUSTRY_CACHE_FILE.stat().st_mtime) / 86400
        if age_days <= _INDUSTRY_CACHE_TTL_DAYS:
            try:
                _ticker_industry_cache = json.loads(
                    _INDUSTRY_CACHE_FILE.read_text(encoding="utf-8")
                )
                return _ticker_industry_cache
            except Exception:
                pass
    _ticker_industry_cache = {}
    return _ticker_industry_cache


def save_industry_cache() -> None:
    """把累积的 ticker→行业 缓存落盘（screen 跑完调一次即可）。"""
    if _ticker_industry_cache is None:
        return
    try:
        _CACHE_DIR.mkdir(parents=True, exist_ok=True)
        _INDUSTRY_CACHE_FILE.write_text(
            json.dumps(_ticker_industry_cache, ensure_ascii=False, indent=0),
            encoding="utf-8",
        )
    except Exception as e:
        print(f"[WARN] 行业缓存落盘失败: {e}", file=sys.stderr)


def _to_xq_symbol(ticker: str) -> Optional[str]:
    """600519.SH → SH600519"""
    t = str(ticker).strip().upper()
    if "." not in t:
        return None
    code, ex = t.split(".")
    if ex not in ("SH", "SZ", "BJ"):
        return None
    return f"{ex}{code}"


def get_stock_industry(ticker: str) -> Optional[str]:
    """
    个股 → 原始行业名（雪球 affiliate_industry）。带持久缓存。
    fail-safe：任何异常返回 None。
    """
    cache = _load_industry_cache()
    if ticker in cache:
        return cache[ticker] or None

    sym = _to_xq_symbol(ticker)
    if not sym:
        return None

    raw_name = None
    try:
        import akshare as ak

        df = ak.stock_individual_basic_info_xq(symbol=sym)
        if df is not None and not df.empty and "item" in df.columns:
            hit = df[df["item"] == "affiliate_industry"]
            if not hit.empty:
                val = hit.iloc[0]["value"]
                if isinstance(val, dict):
                    raw_name = val.get("ind_name")
                elif isinstance(val, str) and "ind_name" in val:
                    # 偶尔是字符串化的 dict
                    try:
                        raw_name = (
                            __import__("ast").literal_eval(val).get("ind_name")
                        )
                    except Exception:
                        raw_name = None
    except Exception as e:
        print(f"[WARN] get_stock_industry {ticker}: {e}", file=sys.stderr)
        raw_name = None

    cache[ticker] = raw_name or ""  # 空串也缓存，避免重复请求失败标的
    return raw_name


def get_stock_sw_industry(ticker: str) -> Optional[str]:
    """个股 → 申万一级行业（get_stock_industry + resolve_sw_industry 组合）。"""
    return resolve_sw_industry(get_stock_industry(ticker))
