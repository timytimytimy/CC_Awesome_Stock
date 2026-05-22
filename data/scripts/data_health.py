#!/usr/bin/env python3
"""
数据健康体检 —— 分析前的"飞行前检查"。

2026-05 实测教训：weekly_pick 用了滞后 9 个月的 CPI、失效的北上资金（=0），
却毫无察觉。本脚本一次性核对所有关键数据源的新鲜度，让 skill 在阶段 1
之前就知道哪些数据不能信。

用法：python scripts/data_health.py
"""

from __future__ import annotations

import glob
import sys
from datetime import date, datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from stock_data.macro import (
    get_pmi, get_ppi, get_cpi, get_m2, get_social_financing,
    get_credit_pulse, get_treasury_yields, get_fed_rate,
)
from stock_data.market import get_northbound_flow
from stock_data.data_freshness import assess_freshness, worst_status, looks_broken_zero

CACHE_DIR = Path(__file__).resolve().parents[1] / ".cache"


def _latest_date(df, col_candidates=("date",)):
    """取 DataFrame 最新一行的日期。"""
    if df is None or len(df) == 0:
        return None
    for c in col_candidates:
        if c in df.columns:
            try:
                return df.iloc[-1][c]
            except Exception:
                return None
    return None


def _spot_snapshot_date():
    """最近一份全市场行情快照缓存的日期（取文件名里的 YYYYMMDD）。"""
    files = sorted(glob.glob(str(CACHE_DIR / "stock_zh_a_spot_*.csv")))
    if not files:
        return None
    stem = Path(files[-1]).stem            # stock_zh_a_spot_20260522
    digits = stem.split("_")[-1]
    try:
        return datetime.strptime(digits, "%Y%m%d").date()
    except ValueError:
        return None


def main():
    today = date.today()
    print(f"# 数据健康体检（as of {today}）\n")

    checks = []   # (名称, data_type, as_of)
    try:
        checks.append(("PMI 制造业", "macro_monthly", _latest_date(get_pmi(periods=3))))
        checks.append(("PPI 同比", "macro_monthly", _latest_date(get_ppi(periods=3))))
        checks.append(("CPI 同比", "macro_monthly", _latest_date(get_cpi(periods=3))))
        checks.append(("M2 同比", "macro_monthly", _latest_date(get_m2(periods=3))))
        checks.append(("社融", "macro_monthly", _latest_date(get_social_financing(periods=3))))
        checks.append(("信贷脉冲", "macro_monthly", _latest_date(get_credit_pulse())))
        checks.append(("中国国债收益率", "market_daily", _latest_date(get_treasury_yields(periods=10))))
        checks.append(("美联储利率", "fed_rate", _latest_date(get_fed_rate(periods=3))))
    except Exception as e:
        print(f"> [WARN] 部分宏观数据拉取异常: {e}\n", file=sys.stderr)

    checks.append(("全市场行情快照", "market_daily", _spot_snapshot_date()))

    # 评估
    results = []
    for name, dtype, as_of in checks:
        a = assess_freshness(dtype, as_of, today)
        results.append((name, a))

    print("| 数据源 | 最新时间 | 滞后(天) | 状态 | 说明 |")
    print("|---|---|---:|---|---|")
    icon = {"fresh": "✅", "stale": "⚠️", "critical": "❌", "unknown": "❓"}
    for name, a in results:
        lag = a["lag_days"] if a["lag_days"] is not None else "—"
        print(f"| {name} | {a['as_of']} | {lag} | {icon[a['status']]} {a['status']} | {a['note']} |")

    # 北上资金值级失效检测
    print()
    nb_note = None
    try:
        nb = get_northbound_flow(5)
        if nb.get("error"):
            nb_note = "❌ 北上资金：数据获取失败"
        else:
            total = nb.get("total_5d")
            broken = looks_broken_zero(total, "北上资金近5日净额") if total is not None else "无数据"
            nb_note = f"❌ 北上资金：{broken}" if broken else f"✅ 北上资金：近5日净额 {total:+.1f} 亿，看起来正常"
    except Exception as e:
        nb_note = f"❌ 北上资金：检查异常 {e}"
    print(f"- {nb_note}")

    # 总体结论
    statuses = [a["status"] for _, a in results]
    overall = worst_status(statuses)
    print()
    critical = [name for name, a in results if a["status"] == "critical"]
    stale = [name for name, a in results if a["status"] == "stale"]

    if overall == "critical":
        print(f"## ❌ 体检结论：有严重过期数据\n")
        print(f"严重过期：{', '.join(critical)}")
        print("> 这些数据**不可作为当期依据**。报告必须显式声明并降级相关结论。")
    elif overall == "stale":
        print(f"## ⚠️ 体检结论：有滞后数据\n")
        print(f"滞后：{', '.join(stale)}")
        print("> 这些数据可用但需谨慎，报告中标注其实际新鲜度。")
    elif overall == "unknown":
        print("## ❓ 体检结论：部分数据时间无法确认\n")
        print("> 无法确认新鲜度的数据，不应当成当期数据使用。")
    else:
        print("## ✅ 体检结论：关键数据均新鲜\n")

    print("\n> [事实] 新鲜度阈值见 stock_data/data_freshness.py。")
    print("> [提示] skill 阶段 1 之前应先看本体检；严重过期的数据源相关结论必须降级。")


if __name__ == "__main__":
    main()
