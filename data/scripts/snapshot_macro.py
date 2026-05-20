#!/usr/bin/env python3
"""
宏观快照报告。
对接高善文（信用周期）+ Howard Marks（市场温度计）的核心数据需求。

用法：python scripts/snapshot_macro.py
"""

from __future__ import annotations
import sys
from pathlib import Path
from datetime import date

sys.path.insert(0, str(Path(__file__).parent.parent))

from stock_data.macro import (
    get_pmi, get_ppi, get_cpi, get_m2, get_social_financing,
    get_treasury_yields, get_credit_pulse, get_fed_rate,
    classify_credit_cycle, market_temperature,
)


def _trend_arrow(series_recent, lookback: int = 3) -> str:
    """根据近 N 期变化输出箭头"""
    if len(series_recent) < lookback:
        return "→"
    return "↗" if series_recent.iloc[-1] > series_recent.iloc[-lookback] else "↘"


def main():
    as_of = date.today().strftime("%Y-%m-%d")
    print(f"# 宏观信号面板 (as of {as_of})\n")

    # ── 1. 经济活动 ────────────────────────────────────
    print("## 1. 经济活动（PMI / PPI / CPI）\n")
    pmi = get_pmi(periods=6)
    ppi = get_ppi(periods=6)
    cpi = get_cpi(periods=6)

    if not pmi.empty:
        latest_m = pmi.iloc[-1]
        prev_m = pmi.iloc[-2] if len(pmi) > 1 else latest_m
        chg = latest_m["manufacturing"] - prev_m["manufacturing"]
        status = "扩张" if latest_m["manufacturing"] >= 50 else "收缩"
        trend = _trend_arrow(pmi["manufacturing"])
        print(f"- **PMI 制造业**: {latest_m['manufacturing']:.1f} ({latest_m['date'].strftime('%Y-%m')})"
              f" | 环比 {chg:+.1f} | 趋势 {trend} | 状态：**{status}**（荣枯线 50）")
        if not pmi.empty:
            print(f"  - 近 6 期: {' → '.join(f'{x:.1f}' for x in pmi['manufacturing'])}")

    if not ppi.empty:
        latest_p = ppi.iloc[-1]
        trend = _trend_arrow(ppi["ppi_yoy"])
        sig = "通胀" if latest_p["ppi_yoy"] > 0 else "通缩"
        print(f"- **PPI 同比**: {latest_p['ppi_yoy']:+.2f}% ({latest_p['date'].strftime('%Y-%m')})"
              f" | 趋势 {trend} | 信号：**{sig}**")
        print(f"  - 近 6 期: {' → '.join(f'{x:+.2f}%' for x in ppi['ppi_yoy'])}")

    if not cpi.empty:
        latest_c = cpi.iloc[-1]
        trend = _trend_arrow(cpi["cpi_yoy"])
        print(f"- **CPI 同比**: {latest_c['cpi_yoy']:+.2f}% ({latest_c['date'].strftime('%Y-%m')})"
              f" | 趋势 {trend}")
        print(f"  - 近 6 期: {' → '.join(f'{x:+.2f}%' for x in cpi['cpi_yoy'])}")
    print()

    # ── 2. 流动性 ─────────────────────────────────────
    print("## 2. 流动性（M2 / 社融 / 信贷脉冲）\n")
    m2 = get_m2(periods=6)
    sf = get_social_financing(periods=12)
    pulse = get_credit_pulse()

    if not m2.empty:
        latest = m2.iloc[-1]
        trend = _trend_arrow(m2["m2_yoy"])
        print(f"- **M2 同比**: {latest['m2_yoy']:+.2f}% ({latest['date'].strftime('%Y-%m')}) | 趋势 {trend}")

    if not sf.empty:
        latest = sf.iloc[-1]
        print(f"- **社融最新月**: {latest['social_financing']:.0f} 亿（{latest['date'].strftime('%Y-%m')}）"
              f" | 含人民币贷款 {latest['rmb_loan']:.0f} 亿")
        print(f"  - 近 6 月社融: {' → '.join(f'{x:.0f}' for x in sf['social_financing'].tail(6))} (亿)")

    if not pulse.empty:
        latest_pulse = pulse.iloc[-1]
        trend = _trend_arrow(pulse["credit_pulse"])
        sig = "信用扩张加速" if latest_pulse["credit_pulse"] > 0 else "信用收缩"
        print(f"- **信贷脉冲**（高善文领先指标）: {latest_pulse['credit_pulse']:+.2f}% "
              f"({latest_pulse['date'].strftime('%Y-%m')}) | 趋势 {trend} | 信号：**{sig}**")
        print(f"  - 近 6 期: {' → '.join(f'{x:+.2f}%' for x in pulse['credit_pulse'].tail(6))}")
        print(f"  - [推断] 信贷脉冲领先权益市场约 6-9 个月，是判断牛熊拐点的核心指标")
    print()

    # ── 3. 利率与利差 ─────────────────────────────────
    print("## 3. 利率与利差（中美国债 / 美联储）\n")
    ty = get_treasury_yields(periods=252)
    fed = get_fed_rate(periods=12)

    if not ty.empty:
        latest = ty.iloc[-1]
        cn10y_pct = (ty["cn_10y"] < latest["cn_10y"]).mean() * 100
        print(f"- **中国10年国债**: {latest['cn_10y']:.4f}% ({latest['date'].strftime('%Y-%m-%d')})"
              f" | 近 1 年分位 {cn10y_pct:.1f}%（低分位=流动性宽松）")
        print(f"- **中国 10Y-2Y 利差**: {latest['cn_10y_2y_spread']:+.4f}%"
              f" | {'倒挂' if latest['cn_10y_2y_spread'] < 0 else '正常' if latest['cn_10y_2y_spread'] > 0.3 else '偏平'}")
        # 中美利差取最近一个非 nan（美国数据有 1-2 天滞后）
        valid_us = ty.dropna(subset=["cn_us_10y_spread"])
        if not valid_us.empty:
            us_row = valid_us.iloc[-1]
            sp = us_row["cn_us_10y_spread"]
            tag = ("深度倒挂（资本外流压力）" if sp < -2
                   else "倒挂" if sp < 0
                   else "正向（资本流入支撑）")
            print(f"- **中美 10Y 利差**: {sp:+.2f}% ({us_row['date'].strftime('%Y-%m-%d')}) | {tag}")

    if not fed.empty:
        latest_fed = fed.iloc[-1]
        print(f"- **美联储基准利率**: {latest_fed['fed_rate']:.2f}% (最近决议 {latest_fed['date'].strftime('%Y-%m-%d')})")
    print()

    # ── 4. 信用周期定位（高善文框架） ──────────────
    print("## 4. 信用周期定位（高善文框架）\n")
    cycle = classify_credit_cycle()
    print(f"- **当前阶段**: {cycle.get('phase', 'unknown')}")
    print(f"- **依据**: PMI={cycle.get('pmi')} ({cycle.get('pmi_trend')}) | "
          f"PPI同比={cycle.get('ppi_yoy', 0):+.2f}% ({cycle.get('ppi_trend')}) | "
          f"信贷脉冲={cycle.get('credit_pulse')} ({cycle.get('credit_pulse_trend')})")
    print(f"- **策略含义** [推断]: {cycle.get('strategy_implication')}")
    print(f"- **数据时间**: {cycle.get('as_of')} | 置信度: {cycle.get('confidence')}")
    print()

    # ── 5. 市场温度计（Howard Marks 框架）────────
    print("## 5. 市场温度计（Howard Marks 框架）\n")
    temp = market_temperature()
    print(f"- **温度评级**: **{temp.get('rating', 'unknown')}** (评分 {temp.get('temp_score', 'N/A')}/100)")
    print(f"- **利差解读**: {temp.get('interpretation', '')}")
    print(f"- **关键指标**:")
    print(f"  - 10Y 国债: {temp.get('cn_10y')}% (近1年分位 {temp.get('cn_10y_1y_percentile')}%)")
    print(f"  - 10Y-2Y 利差: {temp.get('cn_10y_2y_spread')}%")
    print(f"  - 中美 10Y 利差: {temp.get('cn_us_10y_spread')}%")
    if temp.get("fed_rate") is not None:
        print(f"  - 美联储基准: {temp.get('fed_rate')}%")
    print(f"- **数据时间**: {temp.get('as_of')}")
    print()

    # ── 6. 综合策略提示 ──────────────────────────
    print("## 6. 综合策略提示 [推断]\n")
    phase = cycle.get("phase", "")
    temp_rating = temp.get("rating", "")
    print(f"- **信用周期阶段**: {phase}")
    print(f"- **流动性温度**: {temp_rating}")
    print(f"- **结合建议**: {cycle.get('strategy_implication', '')}")
    print()
    print("> [事实] 以上数据来自 akshare（国家统计局/央行/同花顺源）。")
    print("> [推断] 周期判断和温度评分基于规则化框架，可能滞后于市场实际反应。")
    print("> [假设] 信贷脉冲领先权益 6-9 个月的关系来自历史规律，未来可能失效。")
    print("> 本报告仅供研究参考，不构成投资建议。")


if __name__ == "__main__":
    main()
