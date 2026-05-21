#!/usr/bin/env python3
"""
交易日志汇总 + 行为偏见报告。
扫描 journal/trades/*.md，统计交易表现并检测散户常见行为偏见。

用法：
    python scripts/journal_summary.py

这是决策权重最高的一层——你自己的交易记录。
"""

from __future__ import annotations
import sys
import re
from pathlib import Path
from datetime import datetime

PROJECT_ROOT = Path(__file__).resolve().parents[2]
TRADES_DIR = PROJECT_ROOT / "journal" / "trades"


def parse_frontmatter(text: str) -> dict:
    """解析 markdown 文件头部的 YAML frontmatter。"""
    import yaml
    m = re.match(r"^---\s*\n(.*?)\n---\s*\n", text, re.DOTALL)
    if not m:
        return {}
    try:
        return yaml.safe_load(m.group(1)) or {}
    except Exception:
        return {}


def load_trades() -> list[dict]:
    """加载全部交易记录（排除模板）。"""
    if not TRADES_DIR.exists():
        return []
    trades = []
    for fp in sorted(TRADES_DIR.glob("*.md")):
        if fp.name.startswith("_"):
            continue
        fm = parse_frontmatter(fp.read_text(encoding="utf-8"))
        if fm:
            fm["_file"] = fp.name
            trades.append(fm)
    return trades


def main():
    print("# 交易日志汇总\n")
    trades = load_trades()

    if not trades:
        print("📭 `journal/trades/` 暂无交易记录。\n")
        print("用法：每笔交易后，复制 `journal/trades/_template.md`，")
        print("命名为 `YYYY-MM-DD-TICKER.md` 并填写。\n")
        print("> 这是决策权重最高的一层。没有交易记录，系统无法学习你的真实行为模式。")
        return

    closed = [t for t in trades if t.get("status") == "closed"]
    open_pos = [t for t in trades if t.get("status") == "open"]

    # ── 总览 ──
    print("## 总览\n")
    print(f"- 总交易记录: {len(trades)} 笔")
    print(f"- 持仓中: {len(open_pos)} 笔 | 已平仓: {len(closed)} 笔")
    print()

    # ── 平仓交易表现 ──
    if closed:
        pnls = [float(t["pnl_pct"]) for t in closed
                if t.get("pnl_pct") not in (None, "~", "")]
        if pnls:
            wins = [p for p in pnls if p > 0]
            losses = [p for p in pnls if p <= 0]
            win_rate = len(wins) / len(pnls) * 100
            avg_win = sum(wins) / len(wins) if wins else 0
            avg_loss = sum(losses) / len(losses) if losses else 0
            payoff = abs(avg_win / avg_loss) if avg_loss else None

            print("## 平仓交易表现\n")
            print(f"- 胜率: **{win_rate:.0f}%**（{len(wins)} 胜 / {len(losses)} 负）")
            print(f"- 平均盈利: {avg_win:+.1f}% | 平均亏损: {avg_loss:+.1f}%")
            if payoff:
                print(f"- 盈亏比: **{payoff:.2f}**（>1.5 较健康）")
            print(f"- 累计盈亏（简单相加）: {sum(pnls):+.1f}%")
            print()

    # ── 行为偏见检测 ──
    print("## 行为偏见检测\n")
    flags = []

    # 偏见 1：实际仓位系统性高于计划（仓位失控/冲动）
    pos_diffs = []
    for t in trades:
        planned = t.get("planned_position_pct")
        actual = t.get("actual_position_pct")
        if isinstance(planned, (int, float)) and isinstance(actual, (int, float)):
            pos_diffs.append(actual - planned)
    if pos_diffs:
        avg_diff = sum(pos_diffs) / len(pos_diffs)
        if avg_diff > 1.5:
            flags.append(f"⚠️ 实际仓位平均比计划高 {avg_diff:+.1f}% → 可能存在冲动加仓/仓位失控")
        elif avg_diff < -1.5:
            flags.append(f"⚠️ 实际仓位平均比计划低 {avg_diff:+.1f}% → 可能下手犹豫/信心不足")
        else:
            flags.append(f"✅ 实际仓位与计划基本一致（平均差 {avg_diff:+.1f}%）")

    # 偏见 2：亏损加仓（同一 ticker 有 add 且之前是亏损）
    by_ticker: dict[str, list] = {}
    for t in trades:
        by_ticker.setdefault(t.get("ticker", ""), []).append(t)
    avg_down_count = 0
    for ticker, ts in by_ticker.items():
        if any(t.get("action") == "add" for t in ts):
            avg_down_count += 1
    if avg_down_count > 0:
        flags.append(f"⚠️ {avg_down_count} 只标的有加仓记录 → 请人工核查是否为'亏损向下加仓'")

    # 偏见 3：持有期过短（中线却频繁交易）
    holding_periods = []
    for t in closed:
        bd, ed = t.get("date"), t.get("exit_date")
        if bd and ed and ed not in ("~", ""):
            try:
                days = (datetime.fromisoformat(str(ed)) - datetime.fromisoformat(str(bd))).days
                holding_periods.append((days, t.get("horizon", "mid")))
            except Exception:
                pass
    if holding_periods:
        mid_short = [d for d, h in holding_periods if h == "mid" and d < 20]
        if mid_short:
            flags.append(f"⚠️ {len(mid_short)} 笔标注'中线'但持有<20 天 → 可能被短期波动洗出")

    if flags:
        for f in flags:
            print(f"- {f}")
    else:
        print("- 交易样本不足，暂无法检测行为偏见（建议积累 ≥ 5 笔记录）")
    print()

    # ── 持仓中标的 ──
    if open_pos:
        print("## 当前持仓\n")
        print("| 标的 | 行业 | 买入价 | 计划仓位 | 止损价 |")
        print("|---|---|---|---|---|")
        for t in open_pos:
            print(f"| {t.get('name','')} {t.get('ticker','')} | {t.get('industry','')} | "
                  f"{t.get('price','')} | {t.get('actual_position_pct','')}% | {t.get('stop_loss','')} |")
        print()

    print("> [事实] 数据来自 journal/trades/ 你自己填写的交易记录。")
    print("> 行为偏见检测仅供自我复盘参考。")


if __name__ == "__main__":
    main()
