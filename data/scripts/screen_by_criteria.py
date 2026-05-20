#!/usr/bin/env python3
"""
个股筛选 — 供 skill 阶段 3 使用。
从 industry-mapping.yaml 取候选池，按基础财务指标过滤。
用法：
  python screen_by_criteria.py --industry 801080
  python screen_by_criteria.py --tickers 600519.SH,000858.SZ
  python screen_by_criteria.py --school trend-growth --industry 801080
"""

import argparse
import sys
import yaml
from pathlib import Path
from datetime import date

sys.path.insert(0, str(Path(__file__).parent.parent))

from stock_data.company import get_financials_summary, get_valuation
from stock_data.technical import get_technical_position

KB_ROOT = Path(__file__).parent.parent.parent / "kb"
INDUSTRY_MAPPING = KB_ROOT / "taxonomy" / "industry-mapping.yaml"


def load_candidates_from_industry(industry_code: str) -> list[str]:
    if not INDUSTRY_MAPPING.exists():
        print(f"[WARN] industry-mapping.yaml not found", file=sys.stderr)
        return []
    with open(INDUSTRY_MAPPING) as f:
        data = yaml.safe_load(f)
    for ind in data.get("industries", []):
        if ind.get("sw_code") == industry_code:
            tickers = []
            for sub in ind.get("sub_industries", []):
                tickers.extend(sub.get("leaders", []))
            return list(dict.fromkeys(tickers))  # dedup preserve order
    return []


def apply_school_filter(row: dict, school: str) -> bool:
    """根据流派过滤标准做简单过滤"""
    if school == "trend-growth":
        roe = row.get("roe") or 0
        return roe >= 15
    elif school == "long-value":
        roe = row.get("roe") or 0
        net_margin = row.get("net_margin") or 0
        return roe >= 15 and net_margin >= 10
    elif school == "fundamental":
        roe = row.get("roe") or 0
        return roe >= 12
    return True  # 其他流派不过滤


def parse_args():
    p = argparse.ArgumentParser()
    p.add_argument("--industry", help="申万行业代码，如 801080")
    p.add_argument("--tickers", help="逗号分隔的股票列表")
    p.add_argument("--school", default=None, help="流派 slug，应用对应过滤标准")
    p.add_argument("--min-roe", type=float, default=0)
    p.add_argument("--as-of", default=None)
    return p.parse_args()


def main():
    args = parse_args()
    as_of = args.as_of or date.today().strftime("%Y-%m-%d")

    # 确定候选池
    if args.tickers:
        candidates = [t.strip() for t in args.tickers.split(",")]
    elif args.industry:
        candidates = load_candidates_from_industry(args.industry)
    else:
        print("请指定 --industry 或 --tickers", file=sys.stderr)
        sys.exit(1)

    if not candidates:
        print("候选池为空，请检查 industry-mapping.yaml 或 ticker 列表")
        sys.exit(2)

    print(f"# 个股筛选结果（as of {as_of}）\n")
    if args.industry:
        print(f"- 行业代码: {args.industry}")
    if args.school:
        print(f"- 流派过滤: {args.school}")
    print(f"- 候选池: {len(candidates)} 只\n")

    print("| 股票 | ROE(%) | 净利率(%) | 资负率(%) | PE分位 | 趋势 | 通过 |")
    print("|---|---|---|---|---|---|---|")

    passed = []
    for ticker in candidates:
        fin = get_financials_summary(ticker)
        val = get_valuation(ticker)
        tech = get_technical_position(ticker)

        roe = fin.get("roe")
        net_margin = fin.get("net_margin")
        alr = fin.get("asset_liability_ratio")
        pe_pct = val.get("pe_percentile")
        trend = tech.get("trend", "N/A")

        row = {"roe": roe, "net_margin": net_margin}

        # 基础过滤
        ok = True
        if roe is not None and roe < args.min_roe:
            ok = False
        if args.school:
            ok = ok and apply_school_filter(row, args.school)

        flag = "✅" if ok else "❌"
        if ok:
            passed.append(ticker)

        trend_icon = {"uptrend": "↑", "downtrend": "↓", "sideways": "→"}.get(trend, "-")
        print(f"| {ticker} | {roe or 'N/A'} | {net_margin or 'N/A'} | {alr or 'N/A'} | {pe_pct or 'N/A'} | {trend_icon} | {flag} |")

    print(f"\n**通过筛选: {len(passed)} 只** — {', '.join(passed)}")
    print(f"\n> [事实] 数据来自 akshare，时间: {as_of}")
    print("> [推断] ROE/净利率等基于最新年报，非实时。")


if __name__ == "__main__":
    main()
