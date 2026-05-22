#!/usr/bin/env python3
"""
大盘快照 — 供 skill 阶段 1 使用。
输出结构化 Markdown，包含指数状态、涨停统计、行业排名、北上资金。
用法：python snapshot_market.py [--as-of YYYY-MM-DD] [--no-cache]
"""

import argparse
import json
import sys
from datetime import date
from pathlib import Path

# 把 data/ 加入 path
sys.path.insert(0, str(Path(__file__).parent.parent))

from stock_data.market import (
    get_index_snapshot,
    get_limit_up_stats,
    get_sector_performance,
    get_northbound_flow,
)
from stock_data.macro import classify_credit_cycle, market_temperature
from stock_data.data_freshness import looks_broken_zero


def parse_args():
    p = argparse.ArgumentParser()
    p.add_argument("--as-of", default=None, help="YYYY-MM-DD，默认今日")
    p.add_argument("--no-cache", action="store_true")
    return p.parse_args()


def regime_judgment(indices: dict, limit_stats: dict, northbound: dict,
                    cycle: dict = None, temp: dict = None) -> str:
    """
    结合技术面 + 宏观面的大盘状态判断。
    技术面：上证/沪深300 MA60 状态 + 涨停活跃度
    宏观面：信用周期阶段 + 流动性温度
    """
    sz300 = indices.get("sz300", {})
    above_ma60 = sz300.get("above_ma60")
    limit_count = limit_stats.get("limit_up_count") or 0

    # 技术面初判
    if above_ma60 is True and limit_count >= 60:
        tech_state = "A"
    elif above_ma60 is False and limit_count < 30:
        tech_state = "C"
    else:
        tech_state = "B"

    # 宏观面修正
    notes = []
    if cycle:
        phase = cycle.get("phase", "")
        if "衰退" in phase:
            notes.append("宏观衰退期 → 警惕系统性风险")
            if tech_state == "A":
                tech_state = "B"  # 技术面强但宏观差，降级
        elif "复苏" in phase:
            notes.append("宏观复苏期 → 有利成长股")
        elif "过热" in phase:
            notes.append("宏观过热期 → 周期股占优、警惕收紧")
        elif "滞胀" in phase:
            notes.append("宏观滞胀期 → 防御为主")

    if temp:
        rating = temp.get("rating", "")
        if "极冷" in rating and tech_state == "A":
            notes.append("流动性极冷但技术面强 → 警惕假突破")
            tech_state = "B"

    state_map = {
        "A": "A（明确上升趋势）",
        "B": "B（震荡/分化）",
        "C": "C（下降趋势/高风险）",
        "D": "D（恐慌/极端低估）",
    }
    label = state_map.get(tech_state, "B（震荡/分化）")
    if notes:
        label += " | " + "；".join(notes)
    return label


def main():
    args = parse_args()
    as_of = args.as_of or date.today().strftime("%Y-%m-%d")

    print(f"# 大盘快照 (as of {as_of})\n", flush=True)

    # 0. 宏观背景（信用周期 + 温度计）── 必须放最前面
    print("## 宏观背景（信用周期 + 流动性温度）\n")
    try:
        cycle = classify_credit_cycle()
        temp = market_temperature()
        print(f"- **信用周期**: {cycle.get('phase', 'unknown')}")
        print(f"  - PMI={cycle.get('pmi')} ({cycle.get('pmi_trend')}) | "
              f"PPI={cycle.get('ppi_yoy', 0):+.2f}% ({cycle.get('ppi_trend')}) | "
              f"信贷脉冲={cycle.get('credit_pulse')} ({cycle.get('credit_pulse_trend')})")
        print(f"  - 策略含义: {cycle.get('strategy_implication')}")
        print(f"- **市场温度**: {temp.get('rating', 'unknown')} (评分 {temp.get('temp_score', 'N/A')}/100)")
        print(f"  - 10Y国债 {temp.get('cn_10y')}% (近1年分位 {temp.get('cn_10y_1y_percentile')}%) | "
              f"10Y-2Y利差 {temp.get('cn_10y_2y_spread')}% | "
              f"中美10Y利差 {temp.get('cn_us_10y_spread')}%")
        print(f"  - 利差解读: {temp.get('interpretation', '')}")
        print(f"- > 完整宏观面板见: `python scripts/snapshot_macro.py`")
    except Exception as e:
        print(f"- [宏观数据降级] ⚠️ {e}")
    print()

    # 1. 指数
    print("## 主要指数\n")
    indices = get_index_snapshot(as_of)
    labels = {"sh": "上证指数", "sz300": "沪深300", "cyb": "创业板指", "kcb": "科创50"}
    for key, label in labels.items():
        data = indices.get(key, {})
        if "error" in data:
            print(f"- **{label}**: [数据获取失败] ⚠️ 降级")
            continue
        arrow = "↑" if data.get("change_pct", 0) >= 0 else "↓"
        ma60_status = "均线上方" if data.get("above_ma60") else "均线下方" if data.get("above_ma60") is False else "N/A"
        print(f"- **{label}**: {data.get('close', 'N/A')} "
              f"({arrow}{abs(data.get('change_pct', 0))}%) | MA60: {data.get('ma60', 'N/A')} [{ma60_status}]")
    print()

    # 2. 涨停统计
    print("## 情绪温度计\n")
    limit_stats = get_limit_up_stats(as_of.replace("-", ""))
    if limit_stats.get("error"):
        print(f"- 涨停统计: [数据获取失败] ⚠️ 降级\n")
    else:
        print(f"- 涨停数量: **{limit_stats.get('limit_up_count', 'N/A')}** 只")
        print(f"- 最高连板高度: **{limit_stats.get('max_consecutive', 'N/A')}** 板")
        print()

    # 3. 北上资金
    print("## 北上资金（近5日）\n")
    northbound = get_northbound_flow(5)
    if northbound.get("discontinued"):
        print(f"- 北上净流入: [已停止披露] ❌ "
              f"{northbound.get('note', '北向资金实时净额自 2024-08 起不再公布')}"
              f" —— 不作为资金面判断依据\n")
    elif northbound.get("error"):
        print(f"- 北上净流入: [数据获取失败] ⚠️ 降级\n")
    else:
        total = northbound.get("total_5d")
        broken = looks_broken_zero(total, "北上资金近5日净额") if total is not None else None
        if total is None or broken:
            print(f"- 北上净流入: [数据失效] ❌ {broken or '无数据'}"
                  f" —— 不作为资金面判断依据\n")
        else:
            direction = "净流入" if total >= 0 else "净流出"
            print(f"- 近5日 {direction}: **{abs(total):.1f}** 亿元\n")

    # 4. 行业涨跌榜
    print("## 行业涨跌榜（近5日 Top 10）\n")
    sector_df = get_sector_performance(top_n=10)
    if sector_df.empty:
        print("- [数据获取失败] ⚠️ 降级\n")
    else:
        print("| 行业 | 涨跌幅(%) | 净流入(亿) | 成交额(亿) | 领涨股 |")
        print("|---|---|---|---|---|")
        for _, row in sector_df.iterrows():
            vol = f"{row.get('volume', 0):.1f}" if row.get('volume') else "N/A"
            net = f"{row.get('net_inflow', 0):.2f}" if row.get('net_inflow') is not None else "N/A"
            leader = row.get('leader_stock', '') or ''
            leader_pct = f"+{row.get('leader_pct',0):.1f}%" if row.get('leader_pct') else ''
            print(f"| {row.get('industry', '')} | {row.get('change_pct', '')} | {net} | {vol} | {leader} {leader_pct} |")
        print()

    # 5. 综合判断
    print("## 大盘状态判断\n")
    try:
        cycle_for_regime = classify_credit_cycle()
        temp_for_regime = market_temperature()
    except Exception:
        cycle_for_regime, temp_for_regime = None, None
    regime = regime_judgment(indices, limit_stats, northbound, cycle_for_regime, temp_for_regime)
    print(f"- **当前状态**: {regime}")
    print(f"- **数据时间**: {as_of}")
    print()
    print("> [推断] 以上判断综合技术面（MA60、涨停活跃度）+ 宏观面（信用周期、流动性温度）。"
          "完整宏观分析请运行 `python scripts/snapshot_macro.py`。")


if __name__ == "__main__":
    main()
