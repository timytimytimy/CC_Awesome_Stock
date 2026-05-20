#!/usr/bin/env python3
"""
行业筛选 — 供 skill 阶段 2 使用。
用法：python screen_sectors.py [--top 10] [--period 5]
"""

import argparse
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from stock_data.market import get_sector_performance


def parse_args():
    p = argparse.ArgumentParser()
    p.add_argument("--top", type=int, default=10)
    p.add_argument("--period", type=int, default=5, help="统计周期（日）")
    p.add_argument("--as-of", default=None)
    return p.parse_args()


def main():
    args = parse_args()
    as_of = args.as_of or date.today().strftime("%Y-%m-%d")

    print(f"# 行业筛选 Top {args.top}（近{args.period}日，as of {as_of}）\n")

    df = get_sector_performance(top_n=args.top, period_days=args.period)
    if df.empty:
        print("- [数据获取失败] ⚠️ 降级")
        sys.exit(2)

    print("| 排名 | 行业 | 涨跌幅(%) | 成交额(亿) |")
    print("|---|---|---|---|")
    for i, row in df.iterrows():
        vol = f"{row.get('volume', 0)/1e8:.1f}" if row.get('volume') else "N/A"
        flag = " 🔥" if row.get("change_pct", 0) > 5 else ""
        print(f"| {i+1} | {row.get('industry', '')} | {row.get('change_pct', '')}%{flag} | {vol} |")
    print()
    print(f"> [事实] 数据来自 akshare，时间: {as_of}")


if __name__ == "__main__":
    main()
