#!/usr/bin/env python3
"""
个股 5 年财报体检 — 对接唐朝《手把手教你读财报》+ 巴菲特/林园 ROE 框架。

用法：
    python scripts/financial_check.py 600519.SH
    python scripts/financial_check.py 002467.SZ
"""

from __future__ import annotations
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from stock_data.financial import (
    get_financial_summary,
    get_cash_flow,
    get_business_composition,
    get_dividend_history,
    comprehensive_check,
)


def parse_args():
    p = argparse.ArgumentParser()
    p.add_argument("ticker", help="股票代码，如 600519.SH")
    p.add_argument("--periods", type=int, default=5, help="财报期数")
    return p.parse_args()


def main():
    args = parse_args()
    ticker = args.ticker

    print(f"# 个股财报体检：{ticker}\n")

    # 综合体检（先输出结论）
    check = comprehensive_check(ticker)
    if "error" in check:
        print(f"❌ {check['error']}")
        return
    if check.get("not_applicable"):
        print("## 综合结论\n")
        print(f"- **最新报告期**: {check['latest_report']}")
        print(f"- **结论**: ⚠️ 本框架不适用（金融股）\n")
        print(check["reason"])
        return

    print(f"## 综合结论\n")
    print(f"- **最新报告期**: {check['latest_report']}")
    print(f"- **总分**: **{check['score']}/100**")
    print(f"- **结论**: {check['verdict']}")
    print()

    # 分项明细
    print("## 各维度评分\n")
    print("| 维度 | 得分 | 满分 |")
    print("|---|---:|---:|")
    label_map = {
        "A_profit_quality": "A. 利润质量",
        "B_growth": "B. 增长性",
        "C_safety": "C. 财务安全",
        "D_profitability": "D. 盈利能力",
        "E_shareholder_return": "E. 股东回报",
    }
    for key, chk in check["checks"].items():
        print(f"| {label_map.get(key, key)} | {chk['score']} | {chk['max']} |")
    print()

    # 红/黄/绿旗
    if check["red_flags"]:
        print("### ❌ 红旗（重大风险）\n")
        for r in check["red_flags"]:
            print(f"- {r}")
        print()
    if check["yellow_flags"]:
        print("### ⚠️ 黄旗（需关注）\n")
        for y in check["yellow_flags"]:
            print(f"- {y}")
        print()
    if check["highlights"]:
        print("### ✅ 亮点\n")
        for h in check["highlights"]:
            print(f"- {h}")
        print()

    # 5 年财务摘要
    print(f"## 近 {args.periods} 期财务摘要\n")
    summary = get_financial_summary(ticker, periods=args.periods)
    if not summary.empty:
        print("| 报告期 | 营收(亿) | 营收增速 | 净利润(亿) | 净利润增速 | 毛利率 | 净利率 | ROE | 负债率 |")
        print("|---|---:|---:|---:|---:|---:|---:|---:|---:|")
        for _, row in summary.iterrows():
            rev = f"{row['revenue']/1e8:.1f}" if row.get('revenue') else "N/A"
            rev_yoy = f"{row['revenue_yoy']:+.1f}%" if row.get('revenue_yoy') is not None else "N/A"
            np_val = f"{row['net_profit']/1e8:.1f}" if row.get('net_profit') else "N/A"
            np_yoy = f"{row['net_profit_yoy']:+.1f}%" if row.get('net_profit_yoy') is not None else "N/A"
            gm = f"{row['gross_margin']:.1f}%" if row.get('gross_margin') is not None else "N/A"
            nm = f"{row['net_margin']:.1f}%" if row.get('net_margin') is not None else "N/A"
            roe = f"{row['roe']:.1f}%" if row.get('roe') is not None else "N/A"
            debt = f"{row['asset_liability_ratio']:.1f}%" if row.get('asset_liability_ratio') is not None else "N/A"
            print(f"| {row['report_date'].strftime('%Y-%m-%d')} | {rev} | {rev_yoy} | "
                  f"{np_val} | {np_yoy} | {gm} | {nm} | {roe} | {debt} |")
        print()

    # 现金流对比
    print("## 经营现金流 vs 净利润\n")
    cf = get_cash_flow(ticker, periods=args.periods)
    if not cf.empty and not summary.empty:
        # 取年报数据对齐
        cf_annual = cf[cf["report_date"].dt.month == 12].head(args.periods)
        sum_annual = summary[summary["report_date"].dt.month == 12].head(args.periods)
        if not cf_annual.empty:
            print("| 年份 | 净利润(亿) | 经营现金流(亿) | CFO/净利润 | 资本开支(亿) |")
            print("|---|---:|---:|---:|---:|")
            for _, c_row in cf_annual.iterrows():
                date = c_row["report_date"]
                match = sum_annual[sum_annual["report_date"] == date]
                np_val = match.iloc[0]["net_profit"] if not match.empty else None
                cfo = c_row["operating_cash_flow"]
                capex = c_row["capex"]
                np_disp = f"{np_val/1e8:.1f}" if np_val else "N/A"
                cfo_disp = f"{cfo/1e8:.1f}" if cfo else "N/A"
                capex_disp = f"{capex/1e8:.1f}" if capex else "N/A"
                ratio = f"{cfo/np_val:.2f}" if cfo and np_val else "N/A"
                print(f"| {date.strftime('%Y')} | {np_disp} | {cfo_disp} | {ratio} | {capex_disp} |")
            print()

    # 主营构成
    print("## 主营构成（最新报告期）\n")
    biz = get_business_composition(ticker)
    if not biz.empty:
        latest_date = biz["report_date"].max()
        latest_biz = biz[biz["report_date"] == latest_date]
        # 取行业分类
        by_industry = latest_biz[latest_biz["classify_type"].str.contains("行业|产品", na=False)]
        if by_industry.empty:
            by_industry = latest_biz
        print(f"报告期：{latest_date.strftime('%Y-%m-%d')}\n")
        print("| 分类 | 业务 | 收入比例 | 毛利率 |")
        print("|---|---|---:|---:|")
        for _, row in by_industry.head(8).iterrows():
            ratio = row.get("revenue_ratio", "")
            gm = row.get("gross_margin", "")
            print(f"| {row.get('classify_type','')} | {row.get('segment','')} | {ratio} | {gm} |")
        print()

    # 分红记录
    print("## 分红记录\n")
    div = get_dividend_history(ticker)
    if not div.empty:
        years = div["announce_date"].dt.year.nunique()
        print(f"- 累计分红年数: **{years}** 年")
        print(f"- 最近一次: {div.iloc[0]['announce_date'].strftime('%Y-%m-%d')}"
              f"（派息 {div.iloc[0].get('cash_dividend', 'N/A')}）")
        print()
        print("近 5 次分红（实施完成）：")
        for _, row in div.head(5).iterrows():
            print(f"  - {row['announce_date'].strftime('%Y-%m-%d')}: "
                  f"派息 {row.get('cash_dividend','-')}, "
                  f"送股 {row.get('bonus_share','-')}, "
                  f"转增 {row.get('transfer_share','-')}")
        print()

    print("---\n")
    print("> [事实] 财务数据来自同花顺 + 新浪财务接口。")
    print("> [推断] 体检评分基于唐朝《手把手教你读财报》+ 巴菲特/林园 ROE 框架。")
    print("> [假设] 评分仅供研究参考，不构成投资建议；具体阈值可能因行业不同需要调整。")


if __name__ == "__main__":
    main()
