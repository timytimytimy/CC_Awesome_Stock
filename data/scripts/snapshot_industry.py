#!/usr/bin/env python3
"""
行业基本面快照 — 对接邱国鹭"好行业低预期"框架。

用法：
    python scripts/snapshot_industry.py                  # 全部申万一级 + 主线行业
    python scripts/snapshot_industry.py --industry 半导体  # 单个行业深度

输出：
- 全行业 PE/PB 估值地图
- 主线行业的"价格分位 + 动量 + 趋势"综合评估
- 邱国鹭框架下的"低估改善"机会排名
"""

from __future__ import annotations
import argparse
import sys
from pathlib import Path
from datetime import date

sys.path.insert(0, str(Path(__file__).parent.parent))

from stock_data.industry import (
    get_sw_industry_overview,
    classify_industry_position,
    batch_industry_position,
)


# 重点跟踪的同花顺行业（可扩展，对应当前主线和潜在主线）
TRACKED_INDUSTRIES = [
    "半导体", "电子化学品", "光伏设备", "电池", "白酒", "医药",
    "证券", "银行", "保险", "房地产开发", "煤炭", "石油加工",
    "有色金属", "钢铁", "建筑材料", "汽车整车", "新能源整车",
    "通信服务", "软件开发", "互联网服务", "游戏", "影视院线",
    "家电", "纺织服装", "食品", "白酒", "啤酒",
    "军工电子", "航空装备", "船舶制造",
]


def parse_args():
    p = argparse.ArgumentParser()
    p.add_argument("--industry", default=None, help="单个行业深度分析")
    p.add_argument("--top", type=int, default=15, help="批量模式输出 Top N")
    return p.parse_args()


def main():
    args = parse_args()
    as_of = date.today().strftime("%Y-%m-%d")
    print(f"# 行业基本面快照 (as of {as_of})\n")

    sw = get_sw_industry_overview()

    if args.industry:
        # 单行业深度
        print(f"## 单行业深度：{args.industry}\n")
        sw_row = None
        if not sw.empty:
            match = sw[sw["industry_name"].str.contains(args.industry, na=False)]
            sw_row = match.iloc[0] if not match.empty else None
        result = classify_industry_position(args.industry, sw_row)
        if "error" in result:
            print(f"❌ 数据获取失败：{result['error']}")
            return

        m = result["metrics"]
        print(f"**位置标签**: {result['position_label']}")
        print(f"**综合评分**: {result['opportunity_score']}/100\n")
        print(f"### 估值位置")
        if result.get("pe_ttm"):
            print(f"- PE-TTM: {result['pe_ttm']:.2f}")
        if result.get("pb"):
            print(f"- PB: {result['pb']:.2f}")
        if result.get("dividend_yield"):
            print(f"- 股息率: {result['dividend_yield']:.2f}%")
        print(f"- 价格分位（近3年）: **{m['price_percentile_3y']}%**")
        print()

        print("### 动量")
        for period, val in m["momentum"].items():
            if val is not None:
                print(f"- 近 {period}: {val:+.2f}%")
        print()

        print("### 趋势位置")
        print(f"- 收盘: {m['close']:.2f}")
        print(f"- 52周高点: {m['high_52w']:.2f}（距离 {m['drawdown_from_52w_high']:+.2f}%）")
        print(f"- 52周低点: {m['low_52w']:.2f}（距离 {m['rise_from_52w_low']:+.2f}%）")
        if m.get("ma60"):
            print(f"- MA60: {m['ma60']:.2f}")
        if m.get("ma250"):
            print(f"- MA250: {m['ma250']:.2f}")
        print(f"- **趋势**: {m['trend']}")
        print()

        print("### 邱国鹭框架结论")
        print(f"- {result['reasoning']}")
        _print_position_implication(result["position_label"])
        return

    # 全行业模式
    print("## 1. 申万一级行业估值地图（按 PE-TTM 排序）\n")
    if not sw.empty:
        sw_sorted = sw.sort_values("pe_ttm").reset_index(drop=True)
        print("| 排名 | 行业 | 成份股 | PE-TTM | PB | 股息率(%) | 估值标签 |")
        print("|---:|---|---:|---:|---:|---:|---|")
        for idx, row in sw_sorted.iterrows():
            pe = row["pe_ttm"]
            label = _valuation_label(pe, row["pb"], row["dividend_yield"])
            print(f"| {idx+1} | {row['industry_name']} | {int(row['n_stocks'])} | "
                  f"{pe:.1f} | {row['pb']:.2f} | {row['dividend_yield']:.2f} | {label} |")
        print()

    print(f"## 2. 主线/重点行业位置评估（Top {args.top}）\n")
    df = batch_industry_position(TRACKED_INDUSTRIES)
    if df.empty:
        print("❌ 数据获取失败\n")
        return

    df = df.head(args.top)
    print("| 排名 | 行业 | 评分 | 位置标签 | 价格分位(3y) | 3月动量 | 6月动量 | 距高点 | PE-TTM | 趋势 |")
    print("|---:|---|---:|---|---:|---:|---:|---:|---:|---|")
    for idx, row in df.iterrows():
        pe = f"{row['pe_ttm']:.1f}" if row.get('pe_ttm') else "N/A"
        m3 = f"{row['mom_3m']:+.1f}%" if row.get('mom_3m') is not None else "N/A"
        m6 = f"{row['mom_6m']:+.1f}%" if row.get('mom_6m') is not None else "N/A"
        dd = f"{row['drawdown_52w']:+.1f}%" if row.get('drawdown_52w') is not None else "N/A"
        print(f"| {idx+1} | {row['industry']} | {row['score']:.1f} | {row['position_label']} | "
              f"{row['price_pct_3y']:.1f}% | {m3} | {m6} | {dd} | {pe} | {row['trend']} |")
    print()

    # 邱国鹭最优区：低估改善
    best = df[df["position_label"].str.contains("低估改善", na=False)]
    if not best.empty:
        print('## 3. 邱国鹭"低估改善"最优区 ⭐\n')
        for _, row in best.iterrows():
            print(f"- **{row['industry']}** (评分 {row['score']})")
            print(f"  - {row['reasoning']}")
        print()

    # 高位过热警示
    overheated = df[df["position_label"].str.contains("过热|追高", na=False)]
    if not overheated.empty:
        print("## 4. 高位过热警示 ⚠️\n")
        for _, row in overheated.iterrows():
            print(f"- **{row['industry']}**: {row['position_label']} (评分 {row['score']})")
            print(f"  - {row['reasoning']}")
        print()

    # 价值陷阱警示
    trap = df[df["position_label"].str.contains("价值陷阱|低估恶化", na=False)]
    if not trap.empty:
        print("## 5. 价值陷阱风险 ❌\n")
        for _, row in trap.iterrows():
            print(f"- **{row['industry']}**: {row['position_label']}")
            print(f"  - {row['reasoning']}")
        print()

    print("> [事实] 申万一级 PE/PB 来自申万官方；行业指数 K 线来自同花顺。")
    print("> [推断] 价格分位用同花顺行业指数近 3 年算，是 PE 分位的代理。")
    print('> [推断] 评分基于邱国鹭"好行业低预期"框架：低估值 + 改善方向 = 最高分。')
    print("> 本报告仅供研究参考，不构成投资建议。")


def _valuation_label(pe_ttm, pb, div_yield) -> str:
    if pe_ttm is None or pe_ttm <= 0:
        return "无 PE（亏损或异常）"
    tags = []
    if pe_ttm < 10:
        tags.append("极低估")
    elif pe_ttm < 20:
        tags.append("低估")
    elif pe_ttm < 35:
        tags.append("中位")
    elif pe_ttm < 60:
        tags.append("偏贵")
    else:
        tags.append("高估")
    if div_yield and div_yield > 3:
        tags.append("高股息")
    if pb and pb < 1:
        tags.append("破净")
    return " | ".join(tags)


def _print_position_implication(label: str):
    """根据位置标签给出策略含义"""
    print()
    print("### 策略含义 [推断]")
    if "低估改善" in label:
        print("- 邱国鹭框架最优区。基本面+市场预期同时改善，胜率最高。")
        print("- 适合中线建仓，关注龙头股启动信号。")
    elif "价值陷阱" in label or "低估恶化" in label:
        print("- ⚠️ 估值看似便宜，但基本面持续恶化，可能继续下跌。")
        print("- 需要明确的反转催化剂才能考虑介入，否则避开。")
    elif "高位过热" in label or "追高风险" in label:
        print("- ⚠️ 估值已高 + 动量仍强 = 击鼓传花阶段。")
        print("- 现在追入风险大于收益，建议等待回调或观察。")
    elif "高位回调" in label:
        print("- ⚠️ 趋势已转弱，可能进入下行周期。")
        print("- 不建议新仓；已持仓的考虑减仓或设紧止损。")
    else:
        print(f"- 当前状态：{label}，需要更多信号确认。")


if __name__ == "__main__":
    main()
