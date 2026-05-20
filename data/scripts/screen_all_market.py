#!/usr/bin/env python3
"""
全市场第一层筛选 — 供 weekly_pick 使用。

流程：
1. 拉取 A 股全市场实时快照；
2. 过滤 ST、停牌、低成交额标的；
3. 按成交额、当日强度做第一层排序；
4. 对前 N 只做技术、估值、财务增强评分；
5. 输出 Top 候选池，供后续深度分析，不直接构成买卖建议。
"""

from __future__ import annotations

import argparse
import math
import sys
import time
from datetime import date
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).parent.parent))

from stock_data.company import get_financials_summary, get_valuation
from stock_data.technical import compute_rps, get_technical_position


CACHE_DIR = Path(__file__).resolve().parents[1] / ".cache"


def parse_args():
    p = argparse.ArgumentParser()
    p.add_argument("--top", type=int, default=30, help="输出候选数量")
    p.add_argument("--enrich", type=int, default=80, help="做深度评分的初筛数量")
    p.add_argument("--min-amount", type=float, default=3.0, help="最低成交额，单位亿元")
    p.add_argument("--include-bj", action="store_true", help="是否包含北交所")
    p.add_argument("--no-cache", action="store_true", help="不使用缓存")
    return p.parse_args()


def main():
    args = parse_args()
    as_of = date.today().strftime("%Y-%m-%d")
    raw, source = load_market_snapshot(use_cache=not args.no_cache)
    universe_count = len(raw)
    prepared = prepare_universe(raw, include_bj=args.include_bj)
    filtered = prepared[
        (prepared["amount_billion"] >= args.min_amount)
        & (~prepared["name"].str.contains("ST", case=False, na=False))
        & (prepared["price"] > 0)
    ].copy()

    filtered["base_score"] = filtered.apply(score_base_row, axis=1)
    first_pass = filtered.sort_values("base_score", ascending=False).head(args.enrich)
    enriched = [enrich_row(row) for _, row in first_pass.iterrows()]
    result = pd.DataFrame(enriched)
    if result.empty:
        print("本轮无候选通过过滤")
        return

    result = result.sort_values("score", ascending=False).head(args.top).reset_index(drop=True)

    print(f"# 全市场候选筛选 Top {args.top}（as of {as_of}）\n")
    print(f"- 原始快照: {universe_count} 只")
    print(f"- 数据源: {source}")
    print(f"- 过滤后: {len(filtered)} 只（成交额 >= {args.min_amount} 亿，排除 ST/停牌）")
    print(f"- 增强评分: {len(first_pass)} 只")
    if not args.include_bj:
        print("- 北交所: 已排除（当前后续 K 线/估值工具主要支持沪深）")
    print()
    print("| 排名 | 股票 | 名称 | 得分 | 涨跌幅 | 成交额(亿) | 趋势 | RPS63 | PE分位 | ROE | 净利率 | 主要理由 |")
    print("|---:|---|---|---:|---:|---:|---|---:|---:|---:|---:|---|")
    for idx, row in result.iterrows():
        print(
            "| {rank} | {ticker} | {name} | {score:.1f} | {change:.2f}% | {amount:.1f} | "
            "{trend} | {rps63} | {pe_pct} | {roe} | {margin} | {reason} |".format(
                rank=idx + 1,
                ticker=row["ticker"],
                name=row["name"],
                score=row["score"],
                change=row["change_pct"],
                amount=row["amount_billion"],
                trend=row.get("trend", "N/A"),
                rps63=format_optional(row.get("rps63")),
                pe_pct=format_optional(row.get("pe_percentile")),
                roe=format_optional(row.get("roe")),
                margin=format_optional(row.get("net_margin")),
                reason=row.get("reason", ""),
            )
        )

    print("\n> [事实] 快照来自 akshare，增强指标来自本地 stock_data 工具。")
    print("> [推断] 得分用于候选排序，不等同于买入建议；仍需公告、新闻、风险检查和执行信号表二次确认。")


def load_market_snapshot(use_cache: bool = True) -> tuple[pd.DataFrame, str]:
    import akshare as ak

    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    cache_file = CACHE_DIR / f"stock_zh_a_spot_{date.today():%Y%m%d}.csv"
    if use_cache and cache_file.exists():
        return pd.read_csv(cache_file), f"cache:{cache_file.name}"

    errors = []
    for attempt in range(2):
        try:
            df = ak.stock_zh_a_spot_em()
            if df is not None and not df.empty:
                df.to_csv(cache_file, index=False)
                return df, "akshare.stock_zh_a_spot_em"
        except Exception as e:
            errors.append(f"stock_zh_a_spot_em attempt {attempt + 1}: {e}")
            time.sleep(1)

    try:
        df = ak.stock_zh_a_spot()
        if df is not None and not df.empty:
            df.to_csv(cache_file, index=False)
            return df, "akshare.stock_zh_a_spot"
    except Exception as e:
        errors.append(f"stock_zh_a_spot: {e}")

    raise RuntimeError("; ".join(errors))


def prepare_universe(df: pd.DataFrame, include_bj: bool) -> pd.DataFrame:
    data = df.copy()
    data.columns = [str(c).strip() for c in data.columns]
    if "代码" not in data.columns:
        raise ValueError("market snapshot missing 代码 column")

    data["ticker"] = data["代码"].astype(str).map(to_ticker)
    data["exchange"] = data["ticker"].str.split(".").str[-1]
    if not include_bj:
        data = data[data["exchange"].isin(["SH", "SZ"])]

    data["name"] = data.get("名称", "").astype(str)
    data["price"] = numeric_col(data, "最新价")
    data["change_pct"] = numeric_col(data, "涨跌幅")
    data["amount"] = numeric_col(data, "成交额")
    data["amount_billion"] = data["amount"] / 100_000_000
    return data.dropna(subset=["ticker", "price", "change_pct", "amount_billion"])


def to_ticker(code: str) -> str | None:
    raw = code.strip().lower()
    if raw.startswith("sh"):
        return f"{raw[2:]}.SH"
    if raw.startswith("sz"):
        return f"{raw[2:]}.SZ"
    if raw.startswith("bj"):
        return f"{raw[2:]}.BJ"
    if raw.startswith("6"):
        return f"{raw}.SH"
    if raw.startswith(("0", "3")):
        return f"{raw}.SZ"
    if raw.startswith(("8", "9")):
        return f"{raw}.BJ"
    return None


def numeric_col(df: pd.DataFrame, col: str) -> pd.Series:
    if col not in df.columns:
        return pd.Series([math.nan] * len(df), index=df.index)
    return pd.to_numeric(df[col], errors="coerce")


def score_base_row(row: pd.Series) -> float:
    amount_score = min(math.log10(max(row["amount_billion"], 0.01) + 1) * 22, 25)
    change_score = max(min(row["change_pct"], 10), -10) * 2
    return amount_score + change_score


def enrich_row(row: pd.Series) -> dict:
    ticker = row["ticker"]
    tech = get_technical_position(ticker)
    val = get_valuation(ticker)
    fin = get_financials_summary(ticker)
    rps = compute_rps(ticker, periods=(63,))

    trend = tech.get("trend", "N/A")
    rps63 = rps.get("rps_scores", {}).get("63d")
    pe_pct = val.get("pe_percentile")
    roe = fin.get("roe")
    net_margin = fin.get("net_margin")
    debt = fin.get("asset_liability_ratio")

    score = score_base_row(row)
    reasons = []

    if trend == "uptrend":
        score += 18
        reasons.append("上升趋势")
    elif trend == "sideways":
        score += 7
        reasons.append("横盘待确认")
    else:
        score -= 8
        reasons.append("趋势偏弱")

    if rps63 is not None:
        score += max(min(rps63 / 3, 18), -12)
        if rps63 > 10:
            reasons.append("RPS强")

    if pe_pct is not None:
        if pe_pct < 50:
            score += 8
            reasons.append("估值分位可控")
        elif pe_pct > 80:
            score -= 10
            reasons.append("估值偏热")

    if roe is not None:
        if roe >= 10:
            score += 8
            reasons.append("ROE较好")
        elif roe < 0:
            score -= 10
            reasons.append("ROE为负")

    if net_margin is not None:
        if net_margin >= 10:
            score += 5
        elif net_margin < 0:
            score -= 8

    if debt is not None and debt > 75:
        score -= 5
        reasons.append("负债率偏高")

    return {
        "ticker": ticker,
        "name": row["name"],
        "score": round(score, 1),
        "change_pct": round(float(row["change_pct"]), 2),
        "amount_billion": round(float(row["amount_billion"]), 2),
        "trend": trend,
        "rps63": rps63,
        "pe_percentile": pe_pct,
        "roe": roe,
        "net_margin": net_margin,
        "debt": debt,
        "reason": "、".join(reasons[:4]),
    }


def format_optional(value):
    if value is None or pd.isna(value):
        return "N/A"
    return f"{float(value):.1f}"


if __name__ == "__main__":
    main()
