#!/usr/bin/env python3
"""
巨潮资讯 cninfo 查询 —— 官方法定披露源（里海取数纪律的落地工具）。

财报/公告/招股书以官方原始源为准。本脚本直查巨潮，供 skill 阶段 4：
财报数字存疑时回原文核对、年轻公司读招股书、扫描交易所监管函。

用法：
  python scripts/cninfo_query.py profile 600519.SH              # 公司概况
  python scripts/cninfo_query.py disclosures 600519.SH --days 90 [--keyword 回购]
  python scripts/cninfo_query.py prospectus 688256.SH           # 招股说明书定位
  python scripts/cninfo_query.py risk 300769.SZ --days 180      # 监管类风险公告
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from stock_data import cninfo  # noqa: E402

_PROFILE_FIELDS = ["公司名称", "A股简称", "上市日期", "成立日期", "所属行业",
                   "法人代表", "注册资金", "官方网站", "主营业务"]


def cmd_profile(args):
    p = cninfo.get_company_profile(args.ticker)
    print(f"# 公司概况 · {args.ticker}（来源：巨潮资讯 cninfo）\n")
    if not p:
        print("- ❌ 未取到公司概况")
        return
    for f in _PROFILE_FIELDS:
        v = p.get(f)
        if v is not None and str(v).strip() and str(v) != "nan":
            print(f"- **{f}**：{str(v).strip()[:200]}")
    ly = cninfo.listing_years(args.ticker)
    if ly is not None:
        flag = "（上市未满 10 年 → 里海纪律：必读招股说明书）" if ly < 10 else ""
        print(f"- **距今上市年数**：{ly} 年 {flag}")


def cmd_disclosures(args):
    df = cninfo.recent_disclosures(args.ticker, days=args.days, keyword=args.keyword)
    kw = f"（含「{args.keyword}」）" if args.keyword else ""
    print(f"# 公告披露 · {args.ticker} · 近 {args.days} 天{kw}（来源：巨潮 cninfo）\n")
    if df.empty:
        print("- 无匹配公告")
        return
    print(f"- 共 {len(df)} 条\n")
    print("| 日期 | 公告标题 | 原文链接 |")
    print("|---|---|---|")
    for _, r in df.head(40).iterrows():
        print(f"| {r['date']} | {r['title']} | {r['url']} |")
    print("\n> 财报关键数字存疑时，用 WebFetch 打开原文链接核对。")


def cmd_prospectus(args):
    print(f"# 招股说明书定位 · {args.ticker}（来源：巨潮 cninfo）\n")
    ly = cninfo.listing_years(args.ticker)
    if ly is not None and ly >= 10:
        print(f"- 该股上市已 {ly} 年（≥10 年）——里海纪律不要求必读招股书。")
        return
    pr = cninfo.find_prospectus(args.ticker)
    if not pr:
        print("- ❌ 未定位到招股说明书（可能上市过早或检索窗口未覆盖）")
        return
    print(f"- **{pr['title']}**")
    print(f"- 公告日期：{pr['date']}")
    print(f"- 原文链接：{pr['url']}")
    print("\n> 用 WebFetch 打开链接：招股书是理解年轻公司「创立逻辑 + 原始竞争位置」的最全单一文件。")


def cmd_risk(args):
    df = cninfo.find_inquiry_letters(args.ticker, days=args.days)
    print(f"# 监管类风险公告 · {args.ticker} · 近 {args.days} 天（来源：巨潮 cninfo）\n")
    print(f"- 扫描关键词：{' / '.join(cninfo.INQUIRY_KEYWORDS)}\n")
    if df.empty:
        print("- ✅ 未发现问询函/关注函/警示/处罚/立案类公告")
        return
    print(f"- ⚠️ 发现 {len(df)} 条监管类公告，必须列入财务排雷和反对理由：\n")
    print("| 日期 | 公告标题 | 原文链接 |")
    print("|---|---|---|")
    for _, r in df.iterrows():
        print(f"| {r['date']} | {r['title']} | {r['url']} |")


def main():
    p = argparse.ArgumentParser(description="巨潮资讯 cninfo 查询")
    sub = p.add_subparsers(dest="cmd", required=True)

    pp = sub.add_parser("profile", help="公司概况")
    pp.add_argument("ticker")

    pd_ = sub.add_parser("disclosures", help="公告披露列表")
    pd_.add_argument("ticker")
    pd_.add_argument("--days", type=int, default=90)
    pd_.add_argument("--keyword", help="按标题关键词过滤")

    pr = sub.add_parser("prospectus", help="招股说明书定位")
    pr.add_argument("ticker")

    prk = sub.add_parser("risk", help="监管类风险公告扫描")
    prk.add_argument("ticker")
    prk.add_argument("--days", type=int, default=180)

    args = p.parse_args()
    {"profile": cmd_profile, "disclosures": cmd_disclosures,
     "prospectus": cmd_prospectus, "risk": cmd_risk}[args.cmd](args)


if __name__ == "__main__":
    main()
