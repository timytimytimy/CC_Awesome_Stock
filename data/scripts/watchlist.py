#!/usr/bin/env python3
"""
观察池 watchlist —— 把一次性研究变成持续盯盘的活标的。

用法：
  python scripts/watchlist.py list                       # 列出全部条目
  python scripts/watchlist.py check                      # 低成本复查（价格/止损/复核日）
  python scripts/watchlist.py add --ticker 603259.SH --name 药明康德 --tier B \
      --stock-type deep_value --thesis "..." --trigger "..." --invalidation "..." \
      --stop-loss 91.72 --price 104.23 --macro 过热 --source reports/xxx.md \
      --next-review 2026-05-29
  python scripts/watchlist.py update --ticker 603259.SH --state triggered --note "站上MA60"
  python scripts/watchlist.py remove --ticker 603259.SH --note "论文证伪"

check 只报"有变化/要关注"的条目：止损击穿、复核日到、距触发可能不远。
具体触发条件是自由文本，由人/skill 判断；本脚本只把当前价摆到你面前。
"""

from __future__ import annotations

import argparse
import glob
import sys
from datetime import date
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).parent.parent))

from stock_data.tracking import (
    load_watchlist, add_to_watchlist, update_watchlist_entry,
    active_entries, WATCHLIST_STATES,
)

CACHE_DIR = Path(__file__).resolve().parents[1] / ".cache"


def _to_spot_code(ticker: str) -> str:
    """603259.SH → sh603259"""
    code, ex = ticker.split(".")
    return f"{ex.lower()}{code}"


def _load_prices() -> dict[str, float]:
    """从最近一份全市场快照缓存读 {ticker: 最新价}。"""
    files = sorted(glob.glob(str(CACHE_DIR / "stock_zh_a_spot_*.csv")))
    if not files:
        return {}
    try:
        df = pd.read_csv(files[-1])
        df["代码"] = df["代码"].astype(str)
        prices = {}
        for _, r in df.iterrows():
            prices[r["代码"]] = pd.to_numeric(r.get("最新价"), errors="coerce")
        return prices
    except Exception as e:
        print(f"[WARN] 读取快照价格失败: {e}", file=sys.stderr)
        return {}


def _price_of(ticker: str, prices: dict) -> float | None:
    p = prices.get(_to_spot_code(ticker))
    if p is None or pd.isna(p):
        return None
    return float(p)


# ────────────────────────────────────────────────────────────
def cmd_list(args):
    entries = load_watchlist()
    if not entries:
        print("# 观察池为空\n\n用 `watchlist.py add` 或 a-stock-analyst skill 阶段5 写入。")
        return
    print(f"# 观察池（{len(entries)} 只）\n")
    by_state: dict[str, list] = {}
    for e in entries:
        by_state.setdefault(e.get("state", "watching"), []).append(e)
    for state in WATCHLIST_STATES:
        items = by_state.get(state, [])
        if not items:
            continue
        print(f"## {state}（{len(items)}）\n")
        for e in items:
            print(f"- **{e.get('name')} {e.get('ticker')}** [{e.get('tier')}档·{e.get('stock_type','')}]")
            print(f"  - 逻辑：{e.get('thesis','')}")
            print(f"  - 触发：{e.get('trigger','')}")
            print(f"  - 止损：{e.get('stop_loss','N/A')} | 入池价：{e.get('price_at_add','N/A')}"
                  f" | 复核日：{e.get('next_review','N/A')}")
        print()


def cmd_check(args):
    entries = active_entries()
    if not entries:
        print("# 观察池复查\n\n无活跃条目（watching/triggered/active_trial/downgraded）。")
        return
    prices = _load_prices()
    today = date.today().isoformat()
    alerts, normal = [], []

    for e in entries:
        ticker = e.get("ticker")
        cur = _price_of(ticker, prices)
        p_add = e.get("price_at_add")
        stop = e.get("stop_loss")
        chg = None
        if cur is not None and p_add:
            try:
                chg = (cur / float(p_add) - 1) * 100
            except (TypeError, ValueError):
                chg = None

        flags = []
        if cur is not None and stop:
            try:
                if cur <= float(stop):
                    flags.append("⚠️止损击穿")
            except (TypeError, ValueError):
                pass
        nr = e.get("next_review")
        if nr and str(nr) <= today:
            flags.append("📅复核日到")
        if cur is None:
            flags.append("❓无价格数据")

        rec = {"e": e, "cur": cur, "chg": chg, "flags": flags}
        (alerts if flags else normal).append(rec)

    print(f"# 观察池复查（as of {today}）\n")
    print(f"- 活跃条目 {len(entries)} 只 | 需关注 {len(alerts)} 只\n")

    if alerts:
        print("## ⚠️ 需要关注\n")
        print("| 股票 | 档位 | 状态 | 现价 | 较入池 | 止损 | 触发条件 | 标记 |")
        print("|---|---|---|---:|---:|---:|---|---|")
        for r in alerts:
            e = r["e"]
            print(f"| {e.get('name')} {e.get('ticker')} | {e.get('tier')} | {e.get('state')} "
                  f"| {_fmt(r['cur'])} | {_fmt(r['chg'],'%')} | {e.get('stop_loss','N/A')} "
                  f"| {e.get('trigger','')} | {' '.join(r['flags'])} |")
        print()

    if normal:
        print("## 正常跟踪中（无需动作）\n")
        print("| 股票 | 档位 | 状态 | 现价 | 较入池 | 复核日 |")
        print("|---|---|---|---:|---:|---|")
        for r in normal:
            e = r["e"]
            print(f"| {e.get('name')} {e.get('ticker')} | {e.get('tier')} | {e.get('state')} "
                  f"| {_fmt(r['cur'])} | {_fmt(r['chg'],'%')} | {e.get('next_review','N/A')} |")
        print()

    print("> 触发条件为自由文本，需人/skill 判断是否满足；本表只提供现价与硬性标记。")


def _fmt(v, suffix=""):
    if v is None or (isinstance(v, float) and pd.isna(v)):
        return "N/A"
    return f"{v:+.1f}{suffix}" if suffix == "%" else f"{v:.2f}{suffix}"


def cmd_add(args):
    entry = {
        "ticker": args.ticker, "name": args.name, "tier": args.tier,
        "state": "watching", "stock_type": args.stock_type or "",
        "thesis": args.thesis or "", "trigger": args.trigger or "",
        "invalidation": args.invalidation or "", "stop_loss": args.stop_loss,
        "price_at_add": args.price, "macro_at_add": args.macro or "",
        "source_report": args.source or "", "next_review": args.next_review or "",
    }
    result = add_to_watchlist(entry)
    print(f"{'已加入' if result == 'added' else '已刷新'}观察池：{args.name} {args.ticker}")


def cmd_update(args):
    ok = update_watchlist_entry(
        args.ticker, state=args.state, note=args.note or "",
        **({"next_review": args.next_review} if args.next_review else {}),
    )
    print(f"已更新 {args.ticker}" if ok else f"未找到 {args.ticker}")


def cmd_remove(args):
    ok = update_watchlist_entry(args.ticker, state="removed",
                                note=args.note or "移出观察池")
    print(f"已移出 {args.ticker}" if ok else f"未找到 {args.ticker}")


def main():
    p = argparse.ArgumentParser(description="观察池 watchlist 管理")
    sub = p.add_subparsers(dest="cmd", required=True)

    sub.add_parser("list", help="列出全部条目")
    sub.add_parser("check", help="低成本复查")

    pa = sub.add_parser("add", help="加入观察池")
    pa.add_argument("--ticker", required=True)
    pa.add_argument("--name", required=True)
    pa.add_argument("--tier", required=True, choices=["A", "B", "C"])
    pa.add_argument("--stock-type", dest="stock_type")
    pa.add_argument("--thesis")
    pa.add_argument("--trigger")
    pa.add_argument("--invalidation")
    pa.add_argument("--stop-loss", dest="stop_loss", type=float)
    pa.add_argument("--price", type=float, help="入池时股价")
    pa.add_argument("--macro")
    pa.add_argument("--source", help="来源报告路径")
    pa.add_argument("--next-review", dest="next_review")

    pu = sub.add_parser("update", help="更新状态/字段")
    pu.add_argument("--ticker", required=True)
    pu.add_argument("--state", choices=list(WATCHLIST_STATES))
    pu.add_argument("--note")
    pu.add_argument("--next-review", dest="next_review")

    pr = sub.add_parser("remove", help="移出观察池")
    pr.add_argument("--ticker", required=True)
    pr.add_argument("--note")

    args = p.parse_args()
    {"list": cmd_list, "check": cmd_check, "add": cmd_add,
     "update": cmd_update, "remove": cmd_remove}[args.cmd](args)


if __name__ == "__main__":
    main()
