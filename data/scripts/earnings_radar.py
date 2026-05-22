#!/usr/bin/env python3
"""
业绩预告雷达 —— 领先信号扫描。

业绩预告是 A 股强制披露、字面意义前瞻的信号：公司在正式财报前就说出利润方向。
本脚本把当期全部预告按"领先信号强度"排序，让你先看到"哪些公司正在变好/变坏"。

用法：
  python scripts/earnings_radar.py                 # 默认：最强预增 Top 30
  python scripts/earnings_radar.py --top 50
  python scripts/earnings_radar.py --negative      # 看预减/首亏（风险预警）
  python scripts/earnings_radar.py --period 20260331
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).parent.parent))

from stock_data.earnings_forecast import (
    get_earnings_forecast, classify_forecast, FORECAST_POSITIVE, FORECAST_NEGATIVE,
)


def parse_args():
    p = argparse.ArgumentParser(description="业绩预告雷达")
    p.add_argument("--top", type=int, default=30, help="输出条数")
    p.add_argument("--period", help="报告期 YYYYMMDD，默认最近季度末")
    g = p.add_mutually_exclusive_group()
    g.add_argument("--positive", action="store_true", help="只看利好预告（默认）")
    g.add_argument("--negative", action="store_true", help="只看利空预告（风险预警）")
    return p.parse_args()


def main():
    args = parse_args()
    df = get_earnings_forecast(args.period)
    if df.empty:
        print("# 业绩预告雷达\n\n暂无业绩预告数据（可能该报告期预告窗口未开启）。")
        return

    period = df["period"].iloc[0]
    rows = []
    for _, r in df.iterrows():
        cls = classify_forecast(r["forecast_type"], r["change_pct"])
        rows.append({**r.to_dict(), "direction": cls["direction"], "signal": cls["signal"]})
    radar = pd.DataFrame(rows)

    negative = args.negative
    if negative:
        radar = radar[radar["direction"] == "negative"].sort_values("signal")
        title = "利空预告（风险预警）"
    else:
        radar = radar[radar["direction"] == "positive"].sort_values("signal", ascending=False)
        title = "利好预告（领先信号）"

    radar = radar.head(args.top).reset_index(drop=True)

    directions = [classify_forecast(t, c)["direction"]
                  for t, c in zip(df["forecast_type"], df["change_pct"])]
    pos = directions.count("positive")
    neg = directions.count("negative")

    print(f"# 业绩预告雷达 · {title}（报告期 {period}）\n")
    print(f"- 当期净利润预告共 {len(df)} 家 | 利好 {pos} 家 | 利空 {neg} 家")
    print("- 业绩预告是**领先信号**：公司在正式财报前透露利润方向，是「提前预测」的核心抓手\n")

    if radar.empty:
        print("（本方向无记录）")
        return

    print("| 排名 | 股票 | 名称 | 预告类型 | 变动幅度 | 信号分 | 公告日期 | 变动原因 |")
    print("|---:|---|---|---|---:|---:|---|---|")
    for idx, r in radar.iterrows():
        cp = r["change_pct"]
        cp_str = f"{cp:+.0f}%" if cp is not None and not pd.isna(cp) else "—"
        print(f"| {idx+1} | {r['ticker']} | {r['name']} | {r['forecast_type']} "
              f"| {cp_str} | {r['signal']:+.0f} | {r['notice_date']} | {r['reason'] or '—'} |")

    print("\n> [事实] 数据来自 akshare stock_yjyg_em（东财业绩预告）。")
    print("> [推断] 信号分按预告类型+变动幅度估算；预告是方向性信号，仍需财报体检和估值验证。")
    print("> [提示] 预告利好 ≠ 买入信号——还要看估值是否已透支、趋势、行业位置。")


if __name__ == "__main__":
    main()
