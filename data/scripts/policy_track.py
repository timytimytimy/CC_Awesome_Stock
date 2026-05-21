#!/usr/bin/env python3
"""
政策事件追踪 — 抓取 + 归档。

设计原则：本脚本只做"抓取 + 归档"，不做政策影响判断。
影响判断由 skill 分析阶段的 LLM / industry-catalyst subagent 完成。

用法：
    python scripts/policy_track.py            # 抓取并归档
    python scripts/policy_track.py --show     # 只显示最近汇总，不重新抓

产出：
    data/events/policy/YYYY-MM-DD.md   当日抓取归档
    data/events/policy/_recent.md      近 7 天滚动汇总（供 skill 读取）
"""

from __future__ import annotations
import argparse
import sys
from pathlib import Path
from datetime import date, datetime, timedelta

sys.path.insert(0, str(Path(__file__).parent.parent))

from stock_data.policy import get_policy_snapshot

EVENTS_DIR = Path(__file__).resolve().parents[1] / "events" / "policy"


def parse_args():
    p = argparse.ArgumentParser()
    p.add_argument("--show", action="store_true", help="只显示最近汇总")
    p.add_argument("--recent-days", type=int, default=7, help="汇总天数")
    return p.parse_args()


def render_daily(snapshot: dict) -> str:
    """渲染当日归档 Markdown"""
    lines = [f"# 政策事件归档 · {snapshot['as_of']}", ""]
    lines.append(f"> 抓取时间：{datetime.now().strftime('%Y-%m-%d %H:%M')}")
    lines.append("> 本文件仅为原文归档，政策影响判断由分析阶段完成。")
    lines.append("")

    # 政府官网新闻
    lines.append("## 政府官网新闻")
    lines.append("")
    gov = snapshot.get("gov_news", [])
    if gov:
        by_source: dict[str, list] = {}
        for item in gov:
            by_source.setdefault(item["source"], []).append(item)
        for source, items in by_source.items():
            lines.append(f"### {source}")
            lines.append("")
            for it in items:
                lines.append(f"- [{it['title']}]({it['url']})")
            lines.append("")
    else:
        lines.append("- [抓取失败或无数据]")
        lines.append("")

    # 新闻联播
    lines.append("## 新闻联播（近 3 日）")
    lines.append("")
    cctv = snapshot.get("cctv_news", [])
    if cctv:
        cur_date = None
        for it in cctv:
            if it["date"] != cur_date:
                cur_date = it["date"]
                lines.append(f"### {cur_date}")
                lines.append("")
            lines.append(f"- **{it['title']}**")
            if it.get("content"):
                lines.append(f"  - {it['content'][:200]}...")
        lines.append("")
    else:
        lines.append("- [无数据]")
        lines.append("")

    # 财经日历
    lines.append("## 财经日历（未来重要数据公布）")
    lines.append("")
    cal = snapshot.get("economic_calendar", [])
    if cal:
        lines.append("| 日期 | 时间 | 地区 | 事件 | 公布 | 预期 |")
        lines.append("|---|---|---|---|---|---|")
        for it in cal:
            lines.append(
                f"| {it['date']} | {it['time']} | {it['region']} | "
                f"{it['event']} | {it['actual']} | {it['forecast']} |"
            )
        lines.append("")
    else:
        lines.append("- [无数据]")
        lines.append("")

    return "\n".join(lines)


def render_recent(recent_days: int) -> str:
    """合并近 N 天归档为滚动汇总"""
    lines = [f"# 政策事件滚动汇总（近 {recent_days} 天）", ""]
    lines.append(f"> 更新时间：{datetime.now().strftime('%Y-%m-%d %H:%M')}")
    lines.append("> 供 skill 阶段 1/2 的 industry-catalyst subagent 读取。")
    lines.append("> 标注规则：原文标题为 [事实]；政策影响传导为 [推断]；涨跌预测为 [假设]。")
    lines.append("")

    found = 0
    for i in range(recent_days):
        d = (date.today() - timedelta(days=i)).strftime("%Y-%m-%d")
        fp = EVENTS_DIR / f"{d}.md"
        if fp.exists():
            content = fp.read_text(encoding="utf-8")
            # 去掉一级标题，作为子段落并入
            body = "\n".join(content.split("\n")[1:])
            lines.append(f"---\n\n## 📅 {d}\n")
            lines.append(body)
            found += 1

    if found == 0:
        lines.append("（近期无归档数据，请先运行 `python scripts/policy_track.py`）")

    return "\n".join(lines)


def main():
    args = parse_args()
    EVENTS_DIR.mkdir(parents=True, exist_ok=True)

    if not args.show:
        print("[policy_track] 开始抓取政策事件...", file=sys.stderr)
        snapshot = get_policy_snapshot(gov_limit=15, cctv_days=3)

        # 写当日归档
        today = snapshot["as_of"]
        daily_fp = EVENTS_DIR / f"{today}.md"
        daily_fp.write_text(render_daily(snapshot), encoding="utf-8")
        print(f"[policy_track] 当日归档 → {daily_fp}", file=sys.stderr)

        # 统计
        n_gov = len(snapshot.get("gov_news", []))
        n_cctv = len(snapshot.get("cctv_news", []))
        n_cal = len(snapshot.get("economic_calendar", []))
        print(f"[policy_track] 抓取：政府新闻 {n_gov} 条 | 新闻联播 {n_cctv} 条 | 财经日历 {n_cal} 条",
              file=sys.stderr)

    # 更新滚动汇总
    recent_fp = EVENTS_DIR / "_recent.md"
    recent_content = render_recent(args.recent_days)
    recent_fp.write_text(recent_content, encoding="utf-8")
    print(f"[policy_track] 滚动汇总 → {recent_fp}", file=sys.stderr)

    # stdout 输出汇总（供管道使用）
    print(recent_content)


if __name__ == "__main__":
    main()
