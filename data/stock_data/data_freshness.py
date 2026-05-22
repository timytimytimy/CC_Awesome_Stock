"""
数据新鲜度闸门 —— 防止系统在过期/失效数据上做决策。

2026-05 实测教训：weekly_pick 报告里 CPI 数据滞后 9 个月、北上资金=0，
却没有任何告警，被当成当期数据使用。一个做 3-6 个月真金白银决策的系统，
绝不能在几个月前的数据上下结论而毫不知情。

本模块：给定 (数据类型, as_of 日期) → 判定 新鲜/滞后/严重过期，
供各 snapshot 脚本给每个数据点打新鲜度标签、data_health.py 做总体体检。
"""

from __future__ import annotations

import re
from datetime import date, datetime
from typing import Optional

# 各类数据的最大可接受滞后（天）。超过 → 滞后；超过 2 倍 → 严重过期。
EXPECTED_MAX_LAG_DAYS = {
    "macro_monthly": 60,        # PMI/PPI/CPI/M2/社融/信贷脉冲（月度，含发布时滞）
    "market_daily": 7,          # 行情快照/国债收益率/北上资金（日度，留周末节假日缓冲）
    "financial_quarterly": 150, # 财报（季度 + 约 45 天披露窗口 + 缓冲）
    "fed_rate": 70,             # 美联储利率（约每 6 周一次 FOMC）
    "policy": 14,               # 政策事件归档
}

_STATUS_ORDER = {"fresh": 0, "stale": 1, "critical": 2, "unknown": 3}


def _parse_as_of(as_of) -> Optional[date]:
    """解析 as_of：支持 date/datetime、'YYYY-MM-DD'、'YYYY-MM'、'YYYYMMDD'。"""
    if as_of is None:
        return None
    if isinstance(as_of, datetime):
        return as_of.date()
    if isinstance(as_of, date):
        return as_of
    s = str(as_of).strip()
    if not s or s.lower() in ("nan", "none", "n/a"):
        return None
    # YYYYMMDD
    if re.fullmatch(r"\d{8}", s):
        try:
            return datetime.strptime(s, "%Y%m%d").date()
        except ValueError:
            return None
    # YYYY-MM-DD
    if re.fullmatch(r"\d{4}-\d{1,2}-\d{1,2}", s):
        try:
            return datetime.strptime(s, "%Y-%m-%d").date()
        except ValueError:
            return None
    # YYYY-MM —— 月度数据，按月初算（让滞后判定偏保守/安全）
    if re.fullmatch(r"\d{4}-\d{1,2}", s):
        try:
            return datetime.strptime(s + "-01", "%Y-%m-%d").date()
        except ValueError:
            return None
    return None


def assess_freshness(data_type: str, as_of, today: Optional[date] = None) -> dict:
    """
    判定一个数据点的新鲜度。
    返回 {data_type, as_of, lag_days, expected, status, usable, note}
      status: fresh / stale / critical / unknown
      usable: critical/unknown → False（不应作为当期数据使用）
    """
    today = today or date.today()
    expected = EXPECTED_MAX_LAG_DAYS.get(data_type)
    parsed = _parse_as_of(as_of)

    if parsed is None or expected is None:
        return {"data_type": data_type, "as_of": str(as_of), "lag_days": None,
                "expected": expected, "status": "unknown", "usable": False,
                "note": "无法解析数据时间或未知数据类型"}

    lag = (today - parsed).days
    if lag <= expected:
        status, usable, note = "fresh", True, "数据新鲜"
    elif lag <= expected * 2:
        status, usable, note = "stale", True, f"滞后 {lag} 天（超出预期 {expected} 天），谨慎使用"
    else:
        status, usable, note = "critical", False, \
            f"滞后 {lag} 天（预期 {expected} 天）—— 严重过期，不应作为当期数据"

    return {"data_type": data_type, "as_of": str(parsed), "lag_days": lag,
            "expected": expected, "status": status, "usable": usable, "note": note}


def freshness_tag(data_type: str, as_of, today: Optional[date] = None) -> str:
    """给数据点生成一个简短的 markdown 新鲜度标签。"""
    a = assess_freshness(data_type, as_of, today)
    if a["status"] == "fresh":
        return "✅最新"
    if a["status"] == "stale":
        return f"⚠️滞后{a['lag_days']}天"
    if a["status"] == "critical":
        return f"❌滞后{a['lag_days']}天·严重过期"
    return "❓时间未知"


def worst_status(statuses: list[str]) -> str:
    """一组数据里最差的新鲜度——用于总体体检结论。"""
    if not statuses:
        return "unknown"
    return max(statuses, key=lambda s: _STATUS_ORDER.get(s, 3))


def looks_broken_zero(value, label: str = "") -> Optional[str]:
    """
    值级失效检测：某些指标恒等于 0 几乎不可能（如北上资金多日净额）。
    返回告警字符串，或 None（看起来正常）。
    """
    try:
        v = float(value)
    except (TypeError, ValueError):
        return f"{label}数据无法解析为数值，可能接口失效"
    if v == 0.0:
        return f"{label}恰好为 0，接口很可能已失效（不是真实读数）"
    return None
