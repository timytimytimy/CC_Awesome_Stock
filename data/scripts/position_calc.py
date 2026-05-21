#!/usr/bin/env python3
"""
仓位换算器 — 把"目标仓位 X%"换算成对一个具体散户可执行的下单指令。

用法：
    python scripts/position_calc.py 600519.SH --pct 5
    python scripts/position_calc.py 600519.SH --pct 5 --price 1450
    python scripts/position_calc.py --check-profile     # 只检查个人档案

读取 config/personal-profile.yaml。
"""

from __future__ import annotations
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from stock_data.profile import load_profile, calc_position, get_stop_loss, profile_exists


def parse_args():
    p = argparse.ArgumentParser()
    p.add_argument("ticker", nargs="?", help="股票代码，如 600519.SH")
    p.add_argument("--pct", type=float, default=5.0, help="目标仓位百分比")
    p.add_argument("--price", type=float, default=None, help="指定股价（默认取最新收盘）")
    p.add_argument("--horizon", default="mid", help="持有周期 swing/mid/long")
    p.add_argument("--check-profile", action="store_true", help="只检查个人档案是否就绪")
    return p.parse_args()


def main():
    args = parse_args()

    if not profile_exists():
        print("❌ config/personal-profile.yaml 不存在。")
        print("   请复制 config/personal-profile.example.yaml 并填写你的真实信息。")
        sys.exit(1)

    profile = load_profile()

    if args.check_profile:
        cap = profile.get("capital", {})
        rules = profile.get("position_rules", {})
        print("# 个人档案检查\n")
        print(f"- 总资金: {cap.get('total', 0):,.0f} 元")
        print(f"- 可用现金: {cap.get('available', 0):,.0f} 元")
        print(f"- 单股上限: {rules.get('max_single_stock_pct')}%")
        print(f"- 单行业上限: {rules.get('max_single_industry_pct')}%")
        print(f"- 最低现金比例: {rules.get('min_cash_reserve_pct')}%")
        print(f"- 最多持仓数: {rules.get('max_positions')}")
        print(f"- 中线止损线: {get_stop_loss('mid', profile)}%")
        print(f"- 波段止损线: {get_stop_loss('swing', profile)}%")
        owner = profile.get("meta", {}).get("owner", "")
        if not owner:
            print("\n⚠️  meta.owner 为空，且配置可能仍是默认值——请确认已按真实情况修改。")
        return

    if not args.ticker:
        print("用法：python scripts/position_calc.py <ticker> --pct <仓位%>")
        sys.exit(1)

    # 取股价（用不复权的实际市价，不能用后复权价）
    price = args.price
    if price is None:
        from stock_data.company import get_kline
        kl = get_kline(args.ticker, period=5, adjust="")
        if kl.empty:
            print(f"❌ 无法获取 {args.ticker} 的股价，请用 --price 手动指定")
            sys.exit(1)
        price = float(kl.iloc[-1]["收盘"])

    result = calc_position(price, args.pct, profile)
    if "error" in result:
        print(f"❌ {result['error']}")
        sys.exit(1)

    stop_loss_pct = get_stop_loss(args.horizon, profile)
    stop_loss_price = round(price * (1 + stop_loss_pct / 100), 2)

    print(f"# 仓位换算：{args.ticker}\n")
    print(f"- **股价**: {price} 元")
    print(f"- **目标仓位**: {args.pct}% → 目标金额 {result['target_amount']:,.0f} 元")
    print(f"- **可买股数**: **{result['shares']} 股**（{result['lots']} 手）")
    print(f"- **实际占用**: {result['actual_amount']:,.0f} 元（实际仓位 {result['actual_pct']}%）")
    print(f"- **止损价**（{args.horizon}）: {stop_loss_price} 元（{stop_loss_pct}%）")
    print()
    print("## 交易成本")
    print(f"- 买入成本: {result['buy_cost']} 元")
    print(f"- 卖出成本: {result['sell_cost']} 元（含印花税）")
    print(f"- 往返手续费: {result['round_trip_cost']} 元（占 {result['round_trip_cost_pct']}%）")
    print()
    print("## 可执行性")
    if result["executable"] and not result["warnings"]:
        print("- ✅ 可执行")
    else:
        for w in result["warnings"]:
            print(f"- {w}")
        if result["executable"]:
            print("- ✅ 可执行（但请注意上述提示）")
        else:
            print("- ❌ 不可执行")
    print()
    print("> [事实] 换算基于 config/personal-profile.yaml 的资金和成本参数。")
    print("> 最终下单由你自行判断，本工具仅做换算。")


if __name__ == "__main__":
    main()
