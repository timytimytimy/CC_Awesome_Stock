"""
领先信号层回归测试 —— 业绩预告分类、报告期推断、screen 注入。
"""

import sys
import types
from datetime import date
from pathlib import Path

import pandas as pd

DATA_ROOT = Path(__file__).resolve().parents[2] / "data"
for _p in (str(DATA_ROOT), str(DATA_ROOT / "scripts")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from stock_data import earnings_forecast as ef   # noqa: E402
import screen_all_market as screen               # noqa: E402


# ════════════════════════════════════════════════════════════
# classify_forecast —— 预告类型 → 方向 + 信号分
# ════════════════════════════════════════════════════════════
def test_classify_positive_types():
    assert ef.classify_forecast("预增", 120)["direction"] == "positive"
    assert ef.classify_forecast("预增", 120)["signal"] == 20.0       # 大幅预增满分
    assert ef.classify_forecast("预增", 30)["signal"] == 9.0         # 小幅预增
    assert ef.classify_forecast("扭亏", None)["direction"] == "positive"
    assert ef.classify_forecast("略增", 8)["signal"] == 5.0
    assert ef.classify_forecast("减亏", None)["direction"] == "positive"


def test_classify_negative_types():
    assert ef.classify_forecast("首亏", None)["direction"] == "negative"
    assert ef.classify_forecast("首亏", None)["signal"] == -18.0
    assert ef.classify_forecast("续亏", None)["signal"] == -15.0
    assert ef.classify_forecast("增亏", None)["direction"] == "negative"
    assert ef.classify_forecast("预减", -60)["signal"] == -12.0


def test_classify_signal_monotonic():
    """预增幅度越大，信号分越高（不递减）。"""
    s_small = ef.classify_forecast("预增", 20)["signal"]
    s_mid = ef.classify_forecast("预增", 70)["signal"]
    s_big = ef.classify_forecast("预增", 200)["signal"]
    assert s_small <= s_mid <= s_big


def test_classify_unknown_type_is_neutral():
    r = ef.classify_forecast("", None)
    assert r["direction"] == "neutral"
    assert r["signal"] == 0.0


# ════════════════════════════════════════════════════════════
# latest_report_period —— 报告期推断
# ════════════════════════════════════════════════════════════
def test_latest_report_period():
    assert ef.latest_report_period(date(2026, 5, 22)) == "20260331"   # 5月→Q1
    assert ef.latest_report_period(date(2026, 8, 1)) == "20260630"    # 8月→H1
    assert ef.latest_report_period(date(2026, 1, 15)) == "20251231"   # 1月→去年报
    assert ef.latest_report_period(date(2026, 11, 9)) == "20260930"   # 11月→Q3


def test_code_to_ticker():
    assert ef._code_to_ticker("600519") == "600519.SH"
    assert ef._code_to_ticker("000858") == "000858.SZ"
    assert ef._code_to_ticker("300750") == "300750.SZ"
    assert ef._code_to_ticker("001237") == "001237.SZ"


# ════════════════════════════════════════════════════════════
# get_earnings_forecast —— 带 mock akshare 的集成测试
# ════════════════════════════════════════════════════════════
def test_get_earnings_forecast_filters_and_dedups(tmp_path, monkeypatch):
    monkeypatch.setattr(ef, "_CACHE_DIR", tmp_path)

    fake_raw = pd.DataFrame({
        "股票代码": ["600711", "600711", "000722", "300999"],
        "股票简称": ["盛屯矿业", "盛屯矿业", "湖南发展", "测试股"],
        "预测指标": ["归属于上市公司股东的净利润", "营业收入",
                     "归属于上市公司股东的净利润", "归属于上市公司股东的净利润"],
        "预告类型": ["预增", "预增", "预增", "首亏"],
        "业绩变动幅度": [261.0, 50.0, 194.0, -300.0],
        "业绩变动原因": ["铜量价齐升", "营收增长", "来水偏丰", "需求下滑"],
        "公告日期": ["2026-04-01", "2026-04-01", "2026-04-10", "2026-04-12"],
    })
    fake_ak = types.SimpleNamespace(stock_yjyg_em=lambda date: fake_raw)
    monkeypatch.setitem(sys.modules, "akshare", fake_ak)

    df = ef.get_earnings_forecast("20260331")
    # 只保留净利润口径、按 ticker 去重 → 3 只
    assert len(df) == 3
    assert set(df["ticker"]) == {"600711.SH", "000722.SZ", "300999.SZ"}
    # 营收行被过滤掉（盛屯只剩净利润那一行，幅度 261）
    sheng = df[df["ticker"] == "600711.SH"].iloc[0]
    assert sheng["change_pct"] == 261.0


def test_get_forecast_map_shape(tmp_path, monkeypatch):
    monkeypatch.setattr(ef, "_CACHE_DIR", tmp_path)
    fake_raw = pd.DataFrame({
        "股票代码": ["600711"], "股票简称": ["盛屯矿业"],
        "预测指标": ["归属于上市公司股东的净利润"], "预告类型": ["预增"],
        "业绩变动幅度": [261.0], "业绩变动原因": ["铜涨"], "公告日期": ["2026-04-01"],
    })
    monkeypatch.setitem(sys.modules, "akshare",
                        types.SimpleNamespace(stock_yjyg_em=lambda date: fake_raw))
    fm = ef.get_forecast_map("20260331")
    assert "600711.SH" in fm
    assert fm["600711.SH"]["direction"] == "positive"
    assert fm["600711.SH"]["signal"] == 20.0


# ════════════════════════════════════════════════════════════
# screen 注入 —— 业绩预告进入个股得分
# ════════════════════════════════════════════════════════════
def _factors(**kw):
    base = dict(
        ticker="000001.SZ", name="测试股", change_pct=0.0, amount_billion=10.0,
        trend="sideways", discount_52w=-20.0, rps63=20.0, pe_percentile=50.0,
        roe=12.0, net_margin=12.0, debt=45.0, sw_industry="", macro_fit=0.0,
        forecast_type="", forecast_signal=0.0, forecast_direction="",
    )
    base.update(kw)
    return base


def test_forecast_signal_lifts_score():
    """有强预增的股票，各镜头得分都应高于无预告的同类股票。"""
    for lens in ("composite", "value", "growth", "reversal"):
        no_fc = _factors(forecast_type="", forecast_signal=0.0)
        with_fc = _factors(forecast_type="预增", forecast_signal=20.0,
                           forecast_direction="positive")
        s_no, _ = screen.score_lens(no_fc, lens)
        s_yes, reasons = screen.score_lens(with_fc, lens)
        assert s_yes > s_no, f"{lens} 镜头未体现业绩预告利好"
        assert any("业绩预告" in r for r in reasons)


def test_forecast_negative_drags_score():
    """首亏预告应拉低得分。"""
    clean = _factors(forecast_signal=0.0)
    firstloss = _factors(forecast_type="首亏", forecast_signal=-18.0,
                         forecast_direction="negative")
    s_clean, _ = screen.score_lens(clean, "composite")
    s_loss, _ = screen.score_lens(firstloss, "composite")
    assert s_clean - s_loss >= 15
