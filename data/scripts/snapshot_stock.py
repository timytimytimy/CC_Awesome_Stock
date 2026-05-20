#!/usr/bin/env python3
"""
单股快照 — 供 skill 阶段 4 使用。
用法：python snapshot_stock.py <TICKER> [--as-of YYYY-MM-DD]
示例：python snapshot_stock.py 600519.SH
"""

import argparse
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from stock_data.company import get_kline, get_financials_summary, get_valuation, get_announcements
from stock_data.technical import get_technical_position, compute_rps
from stock_data.news import get_stock_news


def parse_args():
    p = argparse.ArgumentParser()
    p.add_argument("ticker", help="股票代码，如 600519.SH")
    p.add_argument("--as-of", default=None)
    p.add_argument("--no-cache", action="store_true")
    return p.parse_args()


def main():
    args = parse_args()
    ticker = args.ticker
    as_of = args.as_of or date.today().strftime("%Y-%m-%d")

    print(f"# 个股快照：{ticker} (as of {as_of})\n")

    # 技术位置
    print("## 技术位置\n")
    tech = get_technical_position(ticker)
    if tech.get("error"):
        print(f"- [数据获取失败] ⚠️ {tech['error']}\n")
    else:
        trend_label = {"uptrend": "上升趋势 ✅", "downtrend": "下降趋势 ❌", "sideways": "横盘 ⚠️"}.get(tech.get("trend", ""), "未知")
        print(f"- 当前价格: **{tech.get('close')}**")
        print(f"- MA20: {tech.get('ma20')} | MA60: {tech.get('ma60')}")
        print(f"- 趋势: {trend_label}")
        print(f"- 距52周高点: {tech.get('discount_from_52w_high_pct')}%")
        print(f"- 52周区间: [{tech.get('low_52w')} – {tech.get('high_52w')}]")
        print()

    # 相对强度
    print("## 相对强度（RPS）\n")
    rps = compute_rps(ticker)
    if rps.get("error"):
        print(f"- [数据获取失败] ⚠️\n")
    else:
        for period, val in rps.get("rps_scores", {}).items():
            print(f"- {period}: {val:+.1f}%")
        print()

    # 估值
    print("## 估值\n")
    val = get_valuation(ticker)
    if val.get("error"):
        print(f"- [数据获取失败] ⚠️\n")
    else:
        pe_pct = val.get('pe_percentile')
        pb_pct = val.get('pb_percentile')
        pe_flag = "⚠️ 过热" if pe_pct and pe_pct > 80 else ("✅ 合理" if pe_pct and pe_pct < 50 else "")
        print(f"- PE(TTM): **{val.get('pe_ttm')}** | 历史分位: {pe_pct}% {pe_flag}")
        print(f"- PB: **{val.get('pb')}** | 历史分位: {pb_pct}%")
        print()

    # 财务摘要
    print("## 财务摘要\n")
    fin = get_financials_summary(ticker)
    if fin.get("financials_error"):
        print(f"- [数据获取失败] ⚠️\n")
    else:
        print(f"- ROE: {fin.get('roe', 'N/A')}%")
        print(f"- 净利率: {fin.get('net_margin', 'N/A')}%")
        print(f"- 资产负债率: {fin.get('asset_liability_ratio', 'N/A')}%")
        print()

    # 最新公告
    print("## 最新公告（最近5条）\n")
    announcements = get_announcements(ticker, limit=5)
    if not announcements:
        print("- 暂无公告数据\n")
    else:
        for a in announcements:
            title = a.get("公告标题") or a.get("标题") or str(a)
            date_val = a.get("公告日期") or a.get("公告时间") or ""
            print(f"- [{date_val}] {title}")
        print()

    # 最新新闻
    print("## 最新新闻（最近5条）\n")
    news = get_stock_news(ticker, limit=5)
    if not news:
        print("- 暂无新闻数据\n")
    else:
        for n in news[:5]:
            title = n.get("新闻标题") or n.get("标题") or str(n)
            published_at = n.get("发布时间") or n.get("时间") or ""
            source = n.get("文章来源") or n.get("来源") or ""
            prefix = f"[{published_at}] " if published_at else ""
            suffix = f"（{source}）" if source else ""
            print(f"- {prefix}{title}{suffix}")
        print()

    print(f"> [事实] 以上数据来自 akshare。数据时间: {as_of}")


if __name__ == "__main__":
    main()
