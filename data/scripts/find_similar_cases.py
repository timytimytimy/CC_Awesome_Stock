#!/usr/bin/env python3
"""
相似案例检索 — 在 kb/cases/ 和 journal/ 中找相关历史案例。

匹配分两层：
  - 精确命中：ticker / theme / school 完全匹配
  - 相关命中：行业关键词出现在案例的 themes_involved 或 display_name 中
    （板块级案例如 PHARMA-SECTOR 没有真实 ticker，靠行业/主题才能被检索到）

用法：
  python find_similar_cases.py 600519.SH
  python find_similar_cases.py 603259.SH --industry 医药生物
  python find_similar_cases.py --theme 白酒 --outcome success
  python find_similar_cases.py --school contrarian-odds
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


def _related_reason(industry: str, theme: str, themes: list, display: str) -> str | None:
    """判断案例是否与给定行业/主题相关，返回命中理由；不相关返回 None。"""
    blobs = [str(t) for t in themes] + [str(display)]
    # 行业关键词匹配：用行业名及其 2/3 字前缀去 themes / display_name 里找
    if industry:
        probes = {industry, industry[:2], industry[:3]}
        for p in probes:
            if p and any(p in b for b in blobs):
                return f"行业相关（{p}）"
    # 主题部分匹配（双向子串）
    if theme:
        for t in themes:
            if theme in str(t) or str(t) in theme:
                return f"主题相关（{t}）"
    return None


def search_cases(ticker: str = None, theme: str = None, school: str = None,
                 outcome: str = None, industry: str = None) -> tuple[list, list]:
    """返回 (精确命中, 相关命中) 两个列表。"""
    exact, related = [], []
    if not CASES_DIR.exists():
        return exact, related
    for f in sorted(CASES_DIR.glob("*.md")):
        if f.name.startswith("_"):
            continue
        content = f.read_text()
        fm = parse_frontmatter(content)
        if not fm:
            continue
        if outcome and fm.get("outcome") != outcome:
            continue
        themes = fm.get("themes_involved") or []
        schools = fm.get("schools_involved") or []
        rec = {
            "file": str(f.relative_to(KB_ROOT.parent)),
            "ticker": fm.get("ticker"),
            "display_name": fm.get("display_name"),
            "outcome": fm.get("outcome"),
            "event_date": fm.get("event_date"),
            "horizon": fm.get("horizon"),
        }
        # ── 精确命中 ──
        is_exact = (
            (ticker and fm.get("ticker") == ticker)
            or (theme and theme in themes)
            or (school and school in schools)
        )
        if is_exact:
            exact.append(rec)
            continue
        # ── 相关命中（行业/主题模糊匹配）──
        reason = _related_reason(industry, theme, themes, fm.get("display_name") or "")
        if reason:
            rec["match_reason"] = reason
            related.append(rec)
    return exact, related


def search_lessons() -> list[dict]:
    results = []
    if not LESSONS_DIR.exists():
        return results
    for f in sorted(LESSONS_DIR.glob("*.md")):
        if f.name.startswith("_"):      # 跳过 _template.md 等模板文件
            continue
        content = f.read_text()
        results.append({
            "file": str(f.relative_to(JOURNAL_ROOT.parent)),
            "slug": f.stem,
            "snippet": content[:200],
        })
    return results


def _fmt_case(c: dict, with_reason: bool = False) -> str:
    icon = "✅" if c["outcome"] == "success" else ("❌" if c["outcome"] == "failure" else "⚠️")
    line = (f"- {icon} [{c['display_name']} {c['ticker']}]({c['file']}) "
            f"— {c['event_date']} | {c['horizon']} | {c['outcome']}")
    if with_reason and c.get("match_reason"):
        line += f"  ⟵ {c['match_reason']}"
    return line


def parse_args():
    p = argparse.ArgumentParser()
    p.add_argument("ticker", nargs="?", help="股票代码，如 600519.SH")
    p.add_argument("--industry", help="行业名，用于相关案例匹配，如 医药生物")
    p.add_argument("--theme", help="题材 slug")
    p.add_argument("--school", help="流派 slug")
    p.add_argument("--outcome", help="success / failure / mixed")
    return p.parse_args()


def main():
    args = parse_args()
    print("# 相似案例检索\n")

    exact, related = search_cases(
        ticker=args.ticker,
        theme=args.theme,
        school=args.school,
        outcome=args.outcome,
        industry=args.industry,
    )

    cases_exist = CASES_DIR.exists() and any(
        not f.name.startswith("_") for f in CASES_DIR.glob("*.md")
    )

    print("## kb/cases 精确命中\n")
    if not exact:
        if not cases_exist:
            print("- 案例库为空（kb/cases/ 尚无案例）\n")
        else:
            print("- 无精确命中（ticker/theme/school 未完全匹配）\n")
    else:
        for c in exact:
            print(_fmt_case(c))
        print()

    print("## kb/cases 相关案例（行业/主题相关）\n")
    if not related:
        if not args.industry and not args.theme:
            print("- 未提供 --industry / --theme，无法做相关性匹配\n")
        else:
            print("- 无行业/主题相关案例\n")
    else:
        for c in related:
            print(_fmt_case(c, with_reason=True))
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

    print("> 提示：精确命中按 ticker/theme/school；相关案例按行业关键词模糊匹配。"
          "板块级案例（如医药集采）需用 --industry 或 --theme 才能检索到。")


if __name__ == "__main__":
    main()
