"""
巨潮资讯 cninfo —— 官方法定披露源。

里海取数纪律：财报/公告/招股书以官方原始源为准，东财/同花顺是转手加工版。
巨潮（cninfo.com.cn）是证监会指定的法定披露平台，所有上市公司公告首发于此。

本模块提供：
- 公司概况（含上市日期，用于"上市 10 年内必读招股书"规则）
- 公告披露列表（带 cninfo 原文链接，供 WebFetch 核对）
- 招股说明书定位（年轻公司）
- 交易所问询函/关注函扫描（风险信号）

全链路 fail-safe：取不到返回空，不报错、不阻断分析。
"""

from __future__ import annotations

import sys
import time
from datetime import date, datetime
from pathlib import Path
from typing import Optional

import pandas as pd

_CACHE_DIR = Path(__file__).resolve().parents[1] / ".cache" / "cninfo"

# 风险类公告关键词（交易所监管类）
INQUIRY_KEYWORDS = ("问询函", "关注函", "监管工作函", "警示函", "处罚", "立案")


def _cache_get(name: str, ttl_hours: float) -> Optional[pd.DataFrame]:
    fp = _CACHE_DIR / f"{name}.pkl"
    if not fp.exists():
        return None
    if (time.time() - fp.stat().st_mtime) / 3600 > ttl_hours:
        return None
    try:
        return pd.read_pickle(fp)
    except Exception:
        return None


def _cache_put(name: str, df: pd.DataFrame) -> None:
    try:
        _CACHE_DIR.mkdir(parents=True, exist_ok=True)
        df.to_pickle(_CACHE_DIR / f"{name}.pkl")
    except Exception as e:
        print(f"[WARN] cninfo cache_put {name}: {e}", file=sys.stderr)


def _code(ticker: str) -> str:
    """600519.SH → 600519"""
    return str(ticker).strip().split(".")[0]


# ────────────────────────────────────────────────────────────
# 1. 公司概况（含上市日期）
# ────────────────────────────────────────────────────────────
def get_company_profile(ticker: str) -> dict:
    """
    巨潮公司概况：公司名称、上市日期、所属行业、主营业务、官网等。
    fail-safe：失败返回 {}。
    """
    code = _code(ticker)
    cached = _cache_get(f"profile_{code}", ttl_hours=24 * 30)
    if cached is not None and not cached.empty:
        return cached.iloc[0].to_dict()
    try:
        import akshare as ak
        df = ak.stock_profile_cninfo(symbol=code)
        if df is None or df.empty:
            return {}
        _cache_put(f"profile_{code}", df)
        return df.iloc[0].to_dict()
    except Exception as e:
        print(f"[WARN] cninfo profile {ticker}: {e}", file=sys.stderr)
        return {}


def listing_years(ticker: str, today: Optional[date] = None) -> Optional[float]:
    """距上市的年数。用于"上市 10 年内必读招股书"规则。取不到返回 None。"""
    profile = get_company_profile(ticker)
    raw = profile.get("上市日期")
    if raw is None or (isinstance(raw, float) and pd.isna(raw)):
        return None
    try:
        d = pd.to_datetime(raw).date()
    except Exception:
        return None
    today = today or date.today()
    return round((today - d).days / 365.25, 1)


# ────────────────────────────────────────────────────────────
# 2. 公告披露
# ────────────────────────────────────────────────────────────
def get_disclosures(ticker: str, start_date: str, end_date: str) -> pd.DataFrame:
    """
    巨潮公告披露列表。start_date/end_date 格式 YYYYMMDD。
    返回列：code, name, title, date, url（cninfo 原文链接）。
    """
    code = _code(ticker)
    cache_key = f"disc_{code}_{start_date}_{end_date}"
    cached = _cache_get(cache_key, ttl_hours=12)
    if cached is not None:
        return cached
    try:
        import akshare as ak
        df = ak.stock_zh_a_disclosure_report_cninfo(
            symbol=code, market="沪深京",
            start_date=start_date, end_date=end_date,
        )
    except Exception as e:
        print(f"[WARN] cninfo disclosures {ticker}: {e}", file=sys.stderr)
        return pd.DataFrame(columns=["code", "name", "title", "date", "url"])

    if df is None or df.empty:
        return pd.DataFrame(columns=["code", "name", "title", "date", "url"])

    out = df.rename(columns={
        "代码": "code", "简称": "name", "公告标题": "title",
        "公告时间": "date", "公告链接": "url",
    })
    keep = [c for c in ["code", "name", "title", "date", "url"] if c in out.columns]
    out = out[keep].reset_index(drop=True)
    _cache_put(cache_key, out)
    return out


def recent_disclosures(ticker: str, days: int = 90,
                       keyword: Optional[str] = None) -> pd.DataFrame:
    """最近 N 天公告；keyword 不为空时按标题过滤。"""
    today = date.today()
    start = (today - pd.Timedelta(days=days)).strftime("%Y%m%d")
    df = get_disclosures(ticker, start, today.strftime("%Y%m%d"))
    if keyword and not df.empty:
        df = df[df["title"].astype(str).str.contains(keyword, na=False)].reset_index(drop=True)
    return df


# ────────────────────────────────────────────────────────────
# 3. 招股说明书（年轻公司必读）
# ────────────────────────────────────────────────────────────
def find_prospectus(ticker: str) -> Optional[dict]:
    """
    定位招股说明书（在上市日期前后窗口内搜"招股"）。
    返回 {title, date, url} 或 None。
    """
    profile = get_company_profile(ticker)
    raw = profile.get("上市日期")
    if raw is None or (isinstance(raw, float) and pd.isna(raw)):
        return None
    try:
        ipo = pd.to_datetime(raw)
    except Exception:
        return None

    start = (ipo - pd.Timedelta(days=150)).strftime("%Y%m%d")
    end = (ipo + pd.Timedelta(days=14)).strftime("%Y%m%d")
    df = get_disclosures(ticker, start, end)
    if df.empty:
        return None
    hit = df[df["title"].astype(str).str.contains("招股", na=False)]
    if hit.empty:
        return None
    # 优先正式"招股说明书"，其次"招股意向书"
    formal = hit[hit["title"].astype(str).str.contains("招股说明书", na=False)]
    pick = (formal if not formal.empty else hit).iloc[0]
    return {"title": pick["title"], "date": pick["date"], "url": pick["url"]}


# ────────────────────────────────────────────────────────────
# 4. 监管类风险公告（问询函/关注函等）
# ────────────────────────────────────────────────────────────
def find_inquiry_letters(ticker: str, days: int = 180) -> pd.DataFrame:
    """
    扫描近 N 天的交易所监管类公告（问询函/关注函/警示/处罚/立案）。
    默认 180 天——半年内的监管函才是相关的风险信号；窗口过宽会拖慢 cninfo 分页查询。
    """
    today = date.today()
    start = (today - pd.Timedelta(days=days)).strftime("%Y%m%d")
    df = get_disclosures(ticker, start, today.strftime("%Y%m%d"))
    if df.empty:
        return df
    pattern = "|".join(INQUIRY_KEYWORDS)
    hit = df[df["title"].astype(str).str.contains(pattern, na=False, regex=True)]
    return hit.reset_index(drop=True)
