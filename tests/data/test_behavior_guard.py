"""
反人性护栏回归测试 —— 守住"行为陷阱必须被检出"的契约。
"""

import sys
from datetime import date, timedelta
from pathlib import Path

import pandas as pd

DATA_ROOT = Path(__file__).resolve().parents[2] / "data"
if str(DATA_ROOT) not in sys.path:
    sys.path.insert(0, str(DATA_ROOT))

from stock_data import behavior_guard as bg   # noqa: E402

TODAY = date(2026, 5, 22)


# ════════════════════════════════════════════════════════════
# 追高 / FOMO
# ════════════════════════════════════════════════════════════
def test_chasing_high_near_52w_high():
    w = bg.check_chasing_high("某股", discount_52w=-1.0)
    assert w is not None and w["level"] == "high" and w["type"] == "追高/FOMO"


def test_chasing_high_big_daily_gain():
    w = bg.check_chasing_high("某股", discount_52w=-25.0, change_pct=9.0)
    assert w is not None and w["type"] == "追涨"


def test_chasing_high_mild_when_approaching():
    w = bg.check_chasing_high("某股", discount_52w=-7.0)
    assert w is not None and w["level"] == "low"


def test_chasing_high_clear_when_deep_discount():
    assert bg.check_chasing_high("某股", discount_52w=-35.0) is None


# ════════════════════════════════════════════════════════════
# 反复改主意（基于预测日志）
# ════════════════════════════════════════════════════════════
def _preds(rows):
    return pd.DataFrame(rows, columns=["ticker", "date", "signal", "tier"])


def test_flip_flop_recently_rejected():
    preds = _preds([
        ("300769.SZ", "2026-04-20", "放弃", "放弃"),
    ])
    w = bg.check_flip_flop("300769.SZ", "德方纳米", preds, today=TODAY)
    assert w is not None and w["type"] == "反复改主意" and w["level"] == "high"


def test_flip_flop_old_rejection_outside_window():
    """超出回看窗口（默认90天）的旧放弃不算反复。"""
    preds = _preds([
        ("300769.SZ", "2025-12-01", "放弃", "放弃"),
    ])
    assert bg.check_flip_flop("300769.SZ", "德方纳米", preds, today=TODAY) is None


def test_flip_flop_clean_when_no_history():
    preds = _preds([("603259.SH", "2026-05-01", "可小仓试错", "B")])
    assert bg.check_flip_flop("000001.SZ", "某股", preds, today=TODAY) is None


# ════════════════════════════════════════════════════════════
# 已在观察池
# ════════════════════════════════════════════════════════════
def test_repeat_recommend_flags_active_watchlist():
    wl = [{"ticker": "603259.SH", "state": "watching"}]
    w = bg.check_repeat_recommend("603259.SH", "药明康德", wl)
    assert w is not None and w["type"] == "已在观察池"


def test_repeat_recommend_ignores_closed_entries():
    wl = [{"ticker": "603259.SH", "state": "removed"}]
    assert bg.check_repeat_recommend("603259.SH", "药明康德", wl) is None


# ════════════════════════════════════════════════════════════
# 过度交易
# ════════════════════════════════════════════════════════════
def test_overtrading_flags_when_over_cap():
    trades = [{"date": (TODAY - timedelta(days=i)).isoformat()} for i in range(10)]
    w = bg.check_overtrading(trades, today=TODAY)   # 默认上限 8
    assert w is not None and w["type"] == "过度交易"


def test_overtrading_clean_within_cap():
    trades = [{"date": (TODAY - timedelta(days=i * 3)).isoformat()} for i in range(4)]
    assert bg.check_overtrading(trades, today=TODAY) is None


# ════════════════════════════════════════════════════════════
# 连续亏损冷静期
# ════════════════════════════════════════════════════════════
def test_cooling_off_after_loss_streak():
    trades = [
        {"status": "closed", "exit_date": "2026-05-20", "pnl_pct": -5},
        {"status": "closed", "exit_date": "2026-05-15", "pnl_pct": -8},
        {"status": "closed", "exit_date": "2026-05-10", "pnl_pct": -3},
    ]
    w = bg.check_cooling_off(trades)
    assert w is not None and w["type"] == "连续亏损·冷静期"


def test_cooling_off_clean_when_recent_win():
    trades = [
        {"status": "closed", "exit_date": "2026-05-20", "pnl_pct": 6},
        {"status": "closed", "exit_date": "2026-05-15", "pnl_pct": -8},
        {"status": "closed", "exit_date": "2026-05-10", "pnl_pct": -3},
    ]
    assert bg.check_cooling_off(trades) is None


# ════════════════════════════════════════════════════════════
# 持有期过短
# ════════════════════════════════════════════════════════════
def test_short_holding_flagged():
    trades = [{"status": "closed", "name": "快进快出股",
               "date": "2026-05-10", "exit_date": "2026-05-14"}]   # 4 天
    w = bg.check_short_holding(trades)
    assert w is not None and w["type"] == "持有期过短"


def test_short_holding_clean_when_held_long_enough():
    trades = [{"status": "closed", "name": "正常持有",
               "date": "2026-04-01", "exit_date": "2026-05-10"}]   # 39 天
    assert bg.check_short_holding(trades) is None


# ════════════════════════════════════════════════════════════
# 亏损加仓
# ════════════════════════════════════════════════════════════
def test_averaging_down_flagged():
    holdings = [{"ticker": "600176.SH", "status": "open", "pnl_pct": -12}]
    w = bg.check_averaging_down("600176.SH", "中国巨石", "add", holdings)
    assert w is not None and w["type"] == "亏损加仓"


def test_averaging_down_clean_when_profitable():
    holdings = [{"ticker": "600176.SH", "status": "open", "pnl_pct": 8}]
    assert bg.check_averaging_down("600176.SH", "中国巨石", "add", holdings) is None


def test_averaging_down_clean_for_new_buy():
    """对不在持仓里的票首次 buy，不算亏损加仓。"""
    assert bg.check_averaging_down("000001.SZ", "某新股", "buy", []) is None
