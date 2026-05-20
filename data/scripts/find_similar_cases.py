#!/usr/bin/env python3
"""
相似案例检索 — 在 kb/cases/ 和 journal/ 中找相关历史案例。
用法：
  python find_similar_cases.py 600519.SH
  python find_similar_cases.py --theme consumer-recovery
  python find_similar_cases.py --school long-value --outcome success
"""

import argparse
import sys
import yaml
from pathlib import Path

KB_ROOT = Path(__file__).parent.parent.parent / "kb"
JOURNAL_ROOT = Path(__file__).parent.parent.parent / "journal"
CASES_DIR = KB_ROOT / "cases"
LESSONS_DIR = JOURNAL_ROOT / "lessons"


def parse_frontmatter(content: str) -> dict:
    """简单解析 YAML frontmatter（--- 包裹）"""
    lines = content.split("\n")
    if not lines[0].strip() == "---":
        return {}
    try:
        end = next(i for i, l in enumerate(lines[1:], 1) if l.strip() == "---")
        return yaml.safe_load("\n".join(lines[1:end])) or {}
    except Exception:
        return {}


def search_cases(ticker: str = None, theme: str = None, school: str = None,
                 outcome: str = None) -> list[dict]:
    results = []
    if not CASES_DIR.exists():
        return results
    for f in CASES_DIR.glob("*.md"):
        if f.name.startswith("_"):
            continue
        content = f.read_text()
        fm = parse_frontmatter(content)
        if not fm:
            continue
        # 匹配条件
        if ticker and fm.get("ticker") != ticker:
            continue
        if theme and theme not in (fm.get("themes_involved") or []):
            continue
        if school and school not in (fm.get("schools_involved") or []):
            continue
        if outcome and fm.get("outcome") != outcome:
            continue
        results.append({
            "file": str(f.relative_to(KB_ROOT.parent)),
            "ticker": fm.get("ticker"),
            "display_name": fm.get("display_name"),
            "outcome": fm.get("outcome"),
            "event_date": fm.get("event_date"),
            "horizon": fm.get("horizon"),
        })
    return results


def search_lessons() -> list[dict]:
    results = []
    if not LESSONS_DIR.exists():
        return results
    for f in LESSONS_DIR.glob("*.md"):
        content = f.read_text()
        results.append({
            "file": str(f.relative_to(JOURNAL_ROOT.parent)),
            "slug": f.stem,
            "snippet": content[:200],
        })
    return results


def parse_args():
    p = argparse.ArgumentParser()
    p.add_argument("ticker", nargs="?", help="股票代码，如 600519.SH")
    p.add_argument("--theme", help="题材 slug")
    p.add_argument("--school", help="流派 slug")
    p.add_argument("--outcome", help="success / failure / mixed")
    return p.parse_args()


def main():
    args = parse_args()
    print("# 相似案例检索\n")

    cases = search_cases(
        ticker=args.ticker,
        theme=args.theme,
        school=args.school,
        outcome=args.outcome,
    )

    print("## kb/cases 历史案例\n")
    if not cases:
        print("- 暂无匹配案例（知识库尚在建设中）\n")
    else:
        for c in cases:
            icon = "✅" if c["outcome"] == "success" else ("❌" if c["outcome"] == "failure" else "⚠️")
            print(f"- {icon} [{c['display_name']} {c['ticker']}]({c['file']}) "
                  f"— {c['event_date']} | {c['horizon']} | {c['outcome']}")
        print()

    print("## journal/lessons 你的教训\n")
    lessons = search_lessons()
    if not lessons:
        print("- 暂无教训记录（开始交易后逐步填充）\n")
    else:
        for l in lessons:
            print(f"- [{l['slug']}]({l['file']})")
            print(f"  > {l['snippet'][:100]}...")
        print()

    print("> 提示：案例和教训需要人工积累。当前 MVP 阶段知识库为空，随时间填充。")


if __name__ == "__main__":
    main()
