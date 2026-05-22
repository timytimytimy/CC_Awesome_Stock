"""
系统闭环回归测试 —— watchlist 状态机 + prediction log 留痕与统计。
"""

import sys
from pathlib import Path

import pytest

DATA_ROOT = Path(__file__).resolve().parents[2] / "data"
if str(DATA_ROOT) not in sys.path:
    sys.path.insert(0, str(DATA_ROOT))

from stock_data import tracking  # noqa: E402


@pytest.fixture
def tmp_store(tmp_path, monkeypatch):
    """把 watchlist / predictions 文件指到临时目录，隔离真实数据。"""
    monkeypatch.setattr(tracking, "WATCHLIST_FILE", tmp_path / "watchlist.yaml")
    monkeypatch.setattr(tracking, "PREDICTIONS_FILE", tmp_path / "predictions.csv")
    return tmp_path


# ════════════════════════════════════════════════════════════
# Watchlist
# ════════════════════════════════════════════════════════════
def test_add_and_load_watchlist(tmp_store):
    res = tracking.add_to_watchlist({
        "ticker": "603259.SH", "name": "药明康德", "tier": "B",
        "thesis": "测试逻辑", "trigger": "测试触发",
    })
    assert res == "added"
    entries = tracking.load_watchlist()
    assert len(entries) == 1
    e = entries[0]
    assert e["ticker"] == "603259.SH"
    assert e["state"] == "watching"           # 默认状态
    assert e["history"][0]["note"] == "入池"   # 首条历史


def test_add_same_ticker_updates_not_duplicates(tmp_store):
    tracking.add_to_watchlist({"ticker": "600176.SH", "name": "中国巨石", "tier": "C"})
    res = tracking.add_to_watchlist({"ticker": "600176.SH", "name": "中国巨石", "tier": "B"})
    assert res == "updated"
    entries = tracking.load_watchlist()
    assert len(entries) == 1                   # 不重复
    assert entries[0]["tier"] == "B"           # 字段已刷新
    assert len(entries[0]["history"]) == 2     # 历史累加


def test_update_watchlist_state_machine(tmp_store):
    tracking.add_to_watchlist({"ticker": "603259.SH", "name": "药明康德", "tier": "B"})
    ok = tracking.update_watchlist_entry("603259.SH", state="triggered", note="站上MA60")
    assert ok
    e = tracking.load_watchlist()[0]
    assert e["state"] == "triggered"
    assert e["history"][-1]["note"] == "站上MA60"


def test_update_rejects_invalid_state(tmp_store):
    tracking.add_to_watchlist({"ticker": "603259.SH", "name": "药明康德", "tier": "B"})
    with pytest.raises(ValueError):
        tracking.update_watchlist_entry("603259.SH", state="不存在的状态")


def test_active_entries_excludes_closed(tmp_store):
    tracking.add_to_watchlist({"ticker": "AAA.SH", "name": "甲", "tier": "B"})
    tracking.add_to_watchlist({"ticker": "BBB.SH", "name": "乙", "tier": "B"})
    tracking.update_watchlist_entry("BBB.SH", state="removed", note="证伪")
    active = tracking.active_entries()
    tickers = {e["ticker"] for e in active}
    assert "AAA.SH" in tickers
    assert "BBB.SH" not in tickers             # removed 不算活跃


def test_update_missing_ticker_returns_false(tmp_store):
    assert tracking.update_watchlist_entry("NOPE.SH", state="triggered") is False


# ════════════════════════════════════════════════════════════
# Prediction Log
# ════════════════════════════════════════════════════════════
def test_append_prediction_assigns_incrementing_id(tmp_store):
    id1 = tracking.append_prediction({"ticker": "603259.SH", "name": "药明康德",
                                      "tier": "B", "signal": "可小仓试错"})
    id2 = tracking.append_prediction({"ticker": "600176.SH", "name": "中国巨石",
                                      "tier": "C", "signal": "跟踪事件"})
    assert id1 == 1 and id2 == 2
    df = tracking.load_predictions()
    assert len(df) == 2
    assert (df["status"] == "pending").all()   # 新记录都是 pending


def test_validate_prediction_computes_return(tmp_store):
    pid = tracking.append_prediction({
        "ticker": "603259.SH", "name": "药明康德", "tier": "B",
        "signal": "可小仓试错", "price_at_prediction": 100.0,
    })
    ok = tracking.validate_prediction(pid, "correct", price_at_validation=130.0)
    assert ok
    df = tracking.load_predictions()
    row = df[df["id"] == pid].iloc[0]
    assert row["status"] == "validated"
    assert row["outcome"] == "correct"
    assert abs(float(row["return_pct"]) - 30.0) < 1e-6   # (130/100-1)*100


def test_validate_rejects_bad_outcome(tmp_store):
    pid = tracking.append_prediction({"ticker": "X.SH", "name": "X", "tier": "B",
                                      "signal": "可小仓试错"})
    with pytest.raises(ValueError):
        tracking.validate_prediction(pid, "maybe")


def test_prediction_stats_hit_rate_by_tier(tmp_store):
    # B 档：2 对 1 错；C 档：1 对
    for px0, px1, oc, tier in [
        (100, 130, "correct", "B"),
        (100, 120, "correct", "B"),
        (100, 80, "wrong", "B"),
        (100, 115, "correct", "C"),
    ]:
        pid = tracking.append_prediction({
            "ticker": f"T{px1}.SH", "name": "T", "tier": tier,
            "signal": "可小仓试错", "price_at_prediction": px0,
        })
        tracking.validate_prediction(pid, oc, price_at_validation=px1)

    stats = tracking.prediction_stats()
    assert stats["validated"] == 4
    assert stats["by_tier"]["B"]["n"] == 3
    assert stats["by_tier"]["B"]["correct"] == 2
    assert stats["by_tier"]["B"]["hit_rate"] == round(2 / 3, 3)
    assert stats["by_tier"]["C"]["hit_rate"] == 1.0
    assert stats["overall"]["n"] == 4


def test_prediction_stats_empty_is_safe(tmp_store):
    stats = tracking.prediction_stats()
    assert stats["total"] == 0
    assert stats["validated"] == 0
    assert stats["by_tier"] == {}
