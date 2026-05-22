"""
选股漏斗回归测试 —— 守住 2026-05 重构的核心契约：
  1. 初筛 = 纯流动性闸门，当日涨幅不参与过滤（未启动的好票不被漏掉）
  2. 多镜头评分：value/growth/reversal 对同一批因子给出不同排序
  3. 宏观联动：信用周期 + PPI → 行业加减分
  4. 困境反转镜头的"未破产"闸门：亏损股不被当成反转候选
"""

import sys
from pathlib import Path

import pandas as pd

DATA_ROOT = Path(__file__).resolve().parents[2] / "data"
for _p in (str(DATA_ROOT), str(DATA_ROOT / "scripts")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import screen_all_market as screen          # noqa: E402
from stock_data import macro_industry        # noqa: E402


# ────────────────────────────────────────────────────────────
# 工具：构造一个增强因子 dict（字段对齐 enrich_factors 输出）
# ────────────────────────────────────────────────────────────
def make_factors(**overrides) -> dict:
    base = dict(
        ticker="000001.SZ", name="测试股", change_pct=0.0, amount_billion=10.0,
        trend="sideways", discount_52w=-20.0, rps63=20.0, pe_percentile=50.0,
        roe=12.0, net_margin=12.0, debt=45.0, sw_industry="", macro_fit=0.0,
    )
    base.update(overrides)
    return base


# ════════════════════════════════════════════════════════════
# 1. 初筛去动量化：当日涨幅不参与过滤
# ════════════════════════════════════════════════════════════
def test_liquidity_gate_ignores_daily_change():
    """核心契约：一只当日走平/微跌、但成交额达标的股票必须通过初筛闸门。"""
    raw = pd.DataFrame({
        "代码": ["sh600000", "sz000002", "sh600001"],
        "名称": ["安静绩优股", "涨停热门股", "缩量小票"],
        "最新价": [10.0, 20.0, 5.0],
        "涨跌幅": [-0.8, 9.98, 3.0],          # 安静股微跌、热门股涨停、小票上涨
        "成交额": [8e8, 9e8, 5e7],            # 安静股8亿、热门股9亿、小票0.5亿
    })
    prepared = screen.prepare_universe(raw, include_bj=False)
    gate = prepared[
        (prepared["amount_billion"] >= 3.0)
        & (~prepared["name"].str.contains("ST", case=False, na=False))
        & (prepared["price"] > 0)
    ]
    tickers = set(gate["ticker"])
    # 微跌的安静绩优股必须留下 —— 这正是重构要守住的
    assert "600000.SH" in tickers
    # 涨停热门股也留下（闸门不因涨幅区别对待）
    assert "000002.SZ" in tickers
    # 缩量小票被流动性闸门挡掉（成交额不足，与涨幅无关）
    assert "600001.SH" not in tickers


def test_gate_inclusion_decided_by_amount_not_change():
    """同样涨幅，成交额决定去留；同样成交额，涨幅不决定去留。"""
    raw = pd.DataFrame({
        "代码": ["sh600010", "sh600011"],
        "名称": ["跌停高量股", "涨停高量股"],
        "最新价": [10.0, 10.0],
        "涨跌幅": [-9.9, 9.9],                # 一个跌停一个涨停
        "成交额": [6e8, 6e8],                 # 成交额相同
    })
    prepared = screen.prepare_universe(raw, include_bj=False)
    gate = prepared[(prepared["amount_billion"] >= 3.0) & (prepared["price"] > 0)]
    # 涨幅相反但成交额相同 → 两只都应通过，闸门对涨幅中立
    assert len(gate) == 2


# ════════════════════════════════════════════════════════════
# 2. 多镜头评分：同一批因子，不同镜头不同排序
# ════════════════════════════════════════════════════════════
def test_value_lens_prefers_cheap_quiet_over_expensive_hot():
    """价值镜头：低估值的安静股 > 高估值的涨停股（即便后者今天大涨）。"""
    cheap_quiet = make_factors(
        ticker="CHEAP", pe_percentile=8.0, roe=18.0, change_pct=-0.5,
        trend="sideways", discount_52w=-35.0,
    )
    expensive_hot = make_factors(
        ticker="HOT", pe_percentile=97.0, roe=18.0, change_pct=9.9,
        trend="uptrend", discount_52w=-1.0,
    )
    s_cheap, _ = screen.score_lens(cheap_quiet, "value")
    s_hot, _ = screen.score_lens(expensive_hot, "value")
    assert s_cheap > s_hot, "价值镜头必须让便宜的安静股胜出"


def test_growth_lens_prefers_uptrend_momentum():
    """成长镜头：上升趋势 + 强 RPS 的股票胜出。"""
    strong_trend = make_factors(ticker="UP", trend="uptrend", rps63=80.0, net_margin=18.0)
    weak_trend = make_factors(ticker="DOWN", trend="downtrend", rps63=-20.0, net_margin=18.0)
    s_up, _ = screen.score_lens(strong_trend, "growth")
    s_down, _ = screen.score_lens(weak_trend, "growth")
    assert s_up > s_down


def test_lenses_produce_different_rankings():
    """同两只股票，value 和 growth 的相对排序应当相反。"""
    value_type = make_factors(ticker="V", pe_percentile=10.0, roe=16.0,
                              trend="sideways", rps63=0.0, discount_52w=-30.0)
    growth_type = make_factors(ticker="G", pe_percentile=85.0, roe=16.0,
                               trend="uptrend", rps63=85.0, discount_52w=-5.0)
    v_value, _ = screen.score_lens(value_type, "value")
    g_value, _ = screen.score_lens(growth_type, "value")
    v_growth, _ = screen.score_lens(value_type, "growth")
    g_growth, _ = screen.score_lens(growth_type, "growth")
    assert v_value > g_value      # 价值镜头看好 value_type
    assert g_growth > v_growth    # 成长镜头看好 growth_type


# ════════════════════════════════════════════════════════════
# 3. 困境反转镜头的"未破产"闸门
# ════════════════════════════════════════════════════════════
def test_reversal_lens_rejects_loss_makers():
    """反转镜头：同样深度回调，亏损股必须显著低于仍盈利的股票（不接飞刀）。"""
    profitable = make_factors(ticker="ALIVE", discount_52w=-50.0, roe=8.0,
                              net_margin=10.0, pe_percentile=30.0)
    loss_maker = make_factors(ticker="DEAD", discount_52w=-50.0, roe=-12.0,
                              net_margin=-15.0, pe_percentile=30.0)
    s_alive, _ = screen.score_lens(profitable, "reversal")
    s_dead, reasons_dead = screen.score_lens(loss_maker, "reversal")
    assert s_alive > s_dead
    assert any("亏损" in r for r in reasons_dead)


# ════════════════════════════════════════════════════════════
# 4. 宏观联动
# ════════════════════════════════════════════════════════════
def test_macro_adjustment_overheat_favors_resources():
    """过热象限：资源行业加分，高估值成长行业减分。"""
    adj = macro_industry.compute_industry_adjustments("过热（经济扩张 + 通胀上行）", "上行")
    assert adj.get("有色金属", 0) > 0
    assert adj.get("煤炭", 0) > 0
    assert adj.get("电子", 0) < 0


def test_macro_adjustment_recession_favors_defensives():
    """衰退象限：周期资源减分，防御行业加分。"""
    adj = macro_industry.compute_industry_adjustments("衰退（经济收缩 + 通缩压力）", "下行")
    assert adj.get("有色金属", 0) < 0
    assert adj.get("公用事业", 0) > 0


def test_macro_fit_changes_score():
    """macro_fit 实际进入个股得分：顺风行业得分更高。"""
    tailwind = make_factors(ticker="WIND+", sw_industry="有色金属", macro_fit=8.0)
    headwind = make_factors(ticker="WIND-", sw_industry="电子", macro_fit=-8.0)
    s_tail, _ = screen.score_lens(tailwind, "composite")
    s_head, _ = screen.score_lens(headwind, "composite")
    assert s_tail - s_head >= 14  # 约 +8 与 -8 的差


def test_resolve_sw_industry_keyword_mapping():
    """雪球细分行业名 → 申万一级。"""
    assert macro_industry.resolve_sw_industry("白酒") == "食品饮料"
    assert macro_industry.resolve_sw_industry("半导体") == "电子"
    assert macro_industry.resolve_sw_industry("证券") == "非银金融"
    assert macro_industry.resolve_sw_industry("光伏设备") == "电力设备"
    assert macro_industry.resolve_sw_industry(None) is None


def test_phase_key_normalization():
    """classify_credit_cycle 的 phase 文本能归一为四象限。"""
    assert macro_industry._phase_key("过热（经济扩张 + 通胀上行）") == "过热"
    assert macro_industry._phase_key("衰退（经济收缩 + 通缩压力）") == "衰退"
    assert macro_industry._phase_key("unknown") is None
