#!/usr/bin/env python3
"""
预测日志 prediction log —— 每个判断都留痕，事后验证，统计命中率。

解决系统最致命的缺口：从不知道自己对不对。
A/B/C 档候选 + "放弃"判断都要 log；3-6 个月后 validate；stats 看哪些
档位/镜头/宏观状态下系统判断更可靠——让知识库第一次可证伪。

用法：
  python scripts/prediction_log.py log --ticker 603259.SH --name 药明康德 \
      --tier B --signal 可小仓试错 --lens value --stock-type deep_value \
      --thesis "..." --trigger "..." --horizon 3-6mo --price 104.23 \
      --macro 过热 --source reports/xxx.md
  python scripts/prediction_log.py list [--pending|--validated]
  python scripts/prediction_log.py validate --id 3 --outcome correct --price 130 --notes "..."
  python scripts/prediction_log.py stats
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).parent.parent))

from stock_data.tracking import (
    load_predictions, append_prediction, validate_prediction, prediction_stats,
)


def cmd_log(args):
    pred_id = append_prediction({
        "ticker": args.ticker, "name": args.name, "tier": args.tier,
        "signal": args.signal, "lens": args.lens or "", "stock_type": args.stock_type or "",
        "thesis": args.thesis or "", "trigger": args.trigger or "",
        "horizon": args.horizon or "3-6mo", "price_at_prediction": args.price,
        "macro_state": args.macro or "", "source_report": args.source or "",
    })
    print(f"已记录预测 #{pred_id}：{args.name} {args.ticker} [{args.tier}档/{args.signal}]")


def cmd_list(args):
    df = load_predictions()
    if df.empty:
        print("# 预测日志为空")
        return
    if args.pending:
        df = df[df["status"] == "pending"]
    elif args.validated:
        df = df[df["status"] == "validated"]
    print(f"# 预测日志（{len(df)} 条）\n")
    print("| # | 日期 | 股票 | 档 | 信号 | 镜头 | 预测价 | 状态 | 结果 | 收益% |")
    print("|---:|---|---|---|---|---|---:|---|---|---:|")
    for _, r in df.iterrows():
        print(f"| {r['id']} | {r['date']} | {r['name']} {r['ticker']} | {r['tier']} "
              f"| {r['signal']} | {_txt(r.get('lens'))} | {_fmt(r['price_at_prediction'])} "
              f"| {r['status']} | {_txt(r.get('outcome'))} | {_fmt(r.get('return_pct'))} |")
    print()


def cmd_validate(args):
    ok = validate_prediction(args.id, args.outcome, args.price, args.notes or "")
    if ok:
        print(f"已标定预测 #{args.id}：{args.outcome}"
              + (f"，验证价 {args.price}" if args.price else ""))
    else:
        print(f"未找到预测 #{args.id}")


def cmd_stats(args):
    s = prediction_stats()
    print("# 预测命中率统计\n")
    print(f"- 累计预测 {s['total']} 条 | 已验证 {s['validated']} | 待验证 {s['pending']}\n")
    if s["validated"] == 0:
        print("> 暂无已验证记录。预测需 3-6 个月后用 `validate` 标定，再回看本表。")
        return

    _print_group("总体", {"全部": s["overall"]})
    _print_group("按档位", s["by_tier"])
    _print_group("按镜头", s["by_lens"])
    _print_group("按宏观状态", s["by_macro"])
    print("> 命中率含部分对 = correct + 0.5×partial。样本少时仅供参考，需持续积累。")


def _print_group(title: str, group: dict):
    if not group:
        return
    print(f"## {title}\n")
    print("| 分组 | 样本 | 命中 | 部分 | 错 | 命中率 | 含部分命中率 | 平均收益% |")
    print("|---|---:|---:|---:|---:|---:|---:|---:|")
    for k, v in group.items():
        print(f"| {k} | {v['n']} | {v['correct']} | {v['partial']} | {v['wrong']} "
              f"| {_pct(v['hit_rate'])} | {_pct(v['hit_rate_incl_partial'])} "
              f"| {_fmt(v['avg_return_pct'])} |")
    print()


def _fmt(v):
    if v is None or v == "" or (isinstance(v, float) and pd.isna(v)):
        return "—"
    try:
        return f"{float(v):.2f}"
    except (TypeError, ValueError):
        return str(v)


def _txt(v):
    """文本字段安全显示：None/NaN/空串 → —"""
    if v is None or v == "" or (isinstance(v, float) and pd.isna(v)):
        return "—"
    return str(v)


def _pct(v):
    return "—" if v is None else f"{v*100:.0f}%"


def main():
    p = argparse.ArgumentParser(description="预测日志 prediction log")
    sub = p.add_subparsers(dest="cmd", required=True)

    pl = sub.add_parser("log", help="记录一条预测")
    pl.add_argument("--ticker", required=True)
    pl.add_argument("--name", required=True)
    pl.add_argument("--tier", required=True, help="A/B/C/放弃")
    pl.add_argument("--signal", required=True, help="强观察/可小仓试错/等待验证/放弃/跟踪事件")
    pl.add_argument("--lens")
    pl.add_argument("--stock-type", dest="stock_type")
    pl.add_argument("--thesis")
    pl.add_argument("--trigger")
    pl.add_argument("--horizon", help="预测兑现周期，默认 3-6mo")
    pl.add_argument("--price", type=float, help="预测时股价")
    pl.add_argument("--macro")
    pl.add_argument("--source")

    pls = sub.add_parser("list", help="列出预测")
    pls.add_argument("--pending", action="store_true", help="只看待验证")
    pls.add_argument("--validated", action="store_true", help="只看已验证")

    pv = sub.add_parser("validate", help="标定预测结果")
    pv.add_argument("--id", type=int, required=True)
    pv.add_argument("--outcome", required=True, choices=["correct", "wrong", "partial"])
    pv.add_argument("--price", type=float, help="验证时股价，自动算收益")
    pv.add_argument("--notes")

    sub.add_parser("stats", help="命中率统计")

    args = p.parse_args()
    {"log": cmd_log, "list": cmd_list, "validate": cmd_validate,
     "stats": cmd_stats}[args.cmd](args)


if __name__ == "__main__":
    main()
