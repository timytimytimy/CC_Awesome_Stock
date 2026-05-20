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


def parse_args():
    p = argparse.ArgumentParser()
    p.add_argument("--as-of", default=None, help="YYYY-MM-DD，默认今日")
    p.add_argument("--no-cache", action="store_true")
    return p.parse_args()


def regime_judgment(indices: dict, limit_stats: dict, northbound: dict) -> str:
    """简单规则判断大盘状态"""
    sz300 = indices.get("sz300", {})
    above_ma60 = sz300.get("above_ma60")
    limit_count = limit_stats.get("limit_up_count") or 0
    nb_flow = northbound.get("total_5d")

    if above_ma60 is True and limit_count >= 60:
        return "A（明确上升趋势）"
    elif above_ma60 is False and limit_count < 30:
        return "C（下降趋势/高风险）"
    else:
        return "B（震荡/分化）"


def main():
    args = parse_args()
    as_of = args.as_of or date.today().strftime("%Y-%m-%d")

    print(f"# 大盘快照 (as of {as_of})\n", flush=True)

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
    if northbound.get("error"):
        print(f"- 北上净流入: [数据获取失败] ⚠️ 降级\n")
    else:
        total = northbound.get("total_5d")
        direction = "净流入" if (total or 0) >= 0 else "净流出"
        print(f"- 近5日 {direction}: **{abs(total or 0):.1f}** 亿元\n")

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
    regime = regime_judgment(indices, limit_stats, northbound)
    print(f"- **当前状态**: {regime}")
    print(f"- **数据时间**: {as_of}")
    print()
    print("> [推断] 以上判断基于简单规则。请参考 kb/playbooks/market-regime.md 做人工复核。")


if __name__ == "__main__":
    main()
