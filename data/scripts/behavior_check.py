#!/usr/bin/env python3
"""
反人性护栏检查 —— 散户亏钱主要亏在行为，本脚本在决策前把行为陷阱摆到台面。

用法：
  python scripts/behavior_check.py                          # 当前行为状态（交易日志）
  python scripts/behavior_check.py --candidates 603259.SH,600176.SH  # 候选股陷阱扫描
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).parent.parent))   # data/
sys.path.insert(0, str(Path(__file__).parent))          # scripts/

from journal_summary import load_trades                  # noqa: E402
from stock_data.tracking import load_predictions, load_watchlist  # noqa: E402
from stock_data import behavior_guard as bg              # noqa: E402

PROFILE_FILE = Path(__file__).resolve().parents[2] / "config" / "personal-profile.yaml"
_ICON = {"high": "❌", "mid": "⚠️", "low": "💡"}


def load_profile() -> dict:
    if PROFILE_FILE.exists():
        try:
            return yaml.safe_load(PROFILE_FILE.read_text(encoding="utf-8")) or {}
        except Exception:
            return {}
    return {}


def _print_warn(w: dict):
    print(f"- {_ICON.get(w['level'], '•')} **{w['type']}**：{w['message']}")


def parse_args():
    p = argparse.ArgumentParser(description="反人性护栏检查")
    p.add_argument("--candidates", help="候选股代码，逗号分隔（做陷阱扫描）")
    return p.parse_args()


def main():
    args = parse_args()
    profile = load_profile()
    trades = load_trades()

    print("# 反人性护栏检查\n")

    # ── 当前行为状态（交易日志）──────────────────────────────
    print("## 当前行为状态\n")
    if not trades:
        print("- 📭 `journal/trades/` 暂无交易记录，行为状态检查待有交易后生效。\n")
    else:
        state_warns = [w for w in (
            bg.check_overtrading(trades, profile),
            bg.check_cooling_off(trades, profile),
            bg.check_short_holding(trades, profile),
        ) if w]
        if state_warns:
            for w in state_warns:
                _print_warn(w)
            print()
            if any(w["level"] == "high" for w in state_warns):
                print("> ⚠️ 存在高危行为信号——本轮强烈建议只看不动，先复盘。\n")
        else:
            print("- ✅ 行为状态正常：无过度交易、无连续亏损、无持有期过短。\n")

    # ── 候选股陷阱扫描 ──────────────────────────────────────
    if args.candidates:
        print("## 候选股行为陷阱扫描\n")
        preds = load_predictions()
        wl = load_watchlist()
        holdings = [t for t in trades if t.get("status") == "open"]
        any_hit = False
        for tk in [t.strip() for t in args.candidates.split(",") if t.strip()]:
            hits = [w for w in (
                bg.check_flip_flop(tk, tk, preds, profile),
                bg.check_repeat_recommend(tk, tk, wl),
                bg.check_averaging_down(tk, tk, "add", holdings),
            ) if w]
            if hits:
                any_hit = True
                print(f"### {tk}\n")
                for w in hits:
                    _print_warn(w)
                print()
        if not any_hit:
            print("- ✅ 候选股未命中反复改主意 / 重复推荐 / 亏损加仓 等陷阱。\n")
        print("> 注：追高/FOMO 检测需个股市场数据，由 skill 阶段 4 用 discount_52w 直接判定。")

    print("\n> [提示] 本检查只提示行为风险，不改变选股结论；最终由你自行判断。")


if __name__ == "__main__":
    main()
