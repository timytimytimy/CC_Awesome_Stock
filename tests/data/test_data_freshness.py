"""
数据可靠性闸门回归测试 —— 守住"过期/失效数据必须被识别"的契约。
"""

import sys
from datetime import date
from pathlib import Path

DATA_ROOT = Path(__file__).resolve().parents[2] / "data"
if str(DATA_ROOT) not in sys.path:
    sys.path.insert(0, str(DATA_ROOT))

from stock_data import data_freshness as df   # noqa: E402

TODAY = date(2026, 5, 22)


# ════════════════════════════════════════════════════════════
# assess_freshness —— 核心判定
# ════════════════════════════════════════════════════════════
def test_fresh_macro():
    a = df.assess_freshness("macro_monthly", "2026-04", TODAY)
    assert a["status"] == "fresh"
    assert a["usable"] is True


def test_stale_macro():
    # macro_monthly 预期 60 天；91 天 → stale（60 < lag <= 120）
    a = df.assess_freshness("macro_monthly", "2026-02-20", TODAY)
    assert a["status"] == "stale"
    assert a["usable"] is True


def test_critical_macro_cpi_9_months_stale():
    """复盘那个真实事故：CPI 滞后 9 个月必须被判 critical 且 unusable。"""
    a = df.assess_freshness("macro_monthly", "2025-08", TODAY)
    assert a["status"] == "critical"
    assert a["usable"] is False
    assert a["lag_days"] > 250


def test_market_daily_thresholds():
    assert df.assess_freshness("market_daily", "2026-05-21", TODAY)["status"] == "fresh"
    assert df.assess_freshness("market_daily", "2026-05-12", TODAY)["status"] == "stale"
    assert df.assess_freshness("market_daily", "2026-04-01", TODAY)["status"] == "critical"


def test_unknown_when_unparseable():
    a = df.assess_freshness("macro_monthly", "不是日期", TODAY)
    assert a["status"] == "unknown"
    assert a["usable"] is False


def test_unknown_data_type():
    a = df.assess_freshness("不存在的类型", "2026-05-20", TODAY)
    assert a["status"] == "unknown"


# ════════════════════════════════════════════════════════════
# _parse_as_of —— 多格式解析
# ════════════════════════════════════════════════════════════
def test_parse_formats():
    assert df._parse_as_of("2026-05-20") == date(2026, 5, 20)
    assert df._parse_as_of("2026-05") == date(2026, 5, 1)        # 月度按月初
    assert df._parse_as_of("20260520") == date(2026, 5, 20)
    assert df._parse_as_of(date(2026, 5, 20)) == date(2026, 5, 20)
    assert df._parse_as_of("nan") is None
    assert df._parse_as_of("") is None
    assert df._parse_as_of(None) is None


# ════════════════════════════════════════════════════════════
# freshness_tag
# ════════════════════════════════════════════════════════════
def test_freshness_tag_strings():
    assert "最新" in df.freshness_tag("macro_monthly", "2026-04", TODAY)
    assert "滞后" in df.freshness_tag("macro_monthly", "2026-02-20", TODAY)
    tag = df.freshness_tag("macro_monthly", "2025-08", TODAY)
    assert "严重过期" in tag and "❌" in tag


# ════════════════════════════════════════════════════════════
# worst_status
# ════════════════════════════════════════════════════════════
def test_worst_status():
    assert df.worst_status(["fresh", "fresh", "stale"]) == "stale"
    assert df.worst_status(["fresh", "critical", "stale"]) == "critical"
    assert df.worst_status(["fresh", "fresh"]) == "fresh"
    assert df.worst_status([]) == "unknown"


# ════════════════════════════════════════════════════════════
# looks_broken_zero —— 值级失效检测（北上资金=0）
# ════════════════════════════════════════════════════════════
def test_broken_zero_flags_exact_zero():
    msg = df.looks_broken_zero(0.0, "北上资金")
    assert msg is not None and "失效" in msg


def test_broken_zero_passes_nonzero():
    assert df.looks_broken_zero(12.3, "北上资金") is None
    assert df.looks_broken_zero(-45.6, "北上资金") is None


def test_broken_zero_flags_non_numeric():
    msg = df.looks_broken_zero(None, "北上资金")
    assert msg is not None
