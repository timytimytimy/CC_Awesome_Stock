#!/usr/bin/env python3
"""
全市场第一层筛选 — 供 weekly_pick 使用。

设计（2026-05 漏斗重构后）：
1. 拉取 A 股全市场实时快照；
2. 初筛 = 纯流动性闸门（成交额阈值 + 排除 ST/停牌/北交所）。
   ★ 不再用"当日涨幅"做有损初筛 —— 那会系统性漏掉"未启动的好票"。
3. 对闸门内的全部标的做技术/估值/财务/宏观增强评分（可 --enrich 限量）；
   增强结果按日缓存，崩溃可自动续跑。
4. 多镜头评分：composite / value / growth / reversal，--lens 选择排序口径；
5. 宏观联动：阶段 1 的信用周期 + PPI 方向 → 个股所属行业加减分；
6. 输出 Top 候选池，供后续深度分析，不直接构成买卖建议。
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
from stock_data.macro import classify_credit_cycle
from stock_data.macro_industry import (
    compute_industry_adjustments,
    get_stock_sw_industry,
    save_industry_cache,
)


CACHE_DIR = Path(__file__).resolve().parents[1] / ".cache"

LENSES = ("composite", "value", "growth", "reversal")


def parse_args():
    p = argparse.ArgumentParser()
    p.add_argument("--top", type=int, default=40, help="输出候选数量")
    p.add_argument("--enrich", type=int, default=0,
                   help="增强评分数量上限；0=闸门内全部（推荐，周频跑）")
    p.add_argument("--lens", choices=LENSES, default="composite",
                   help="排序镜头：composite/value/growth/reversal")
    p.add_argument("--min-amount", type=float, default=3.0, help="最低成交额，单位亿元")
    p.add_argument("--include-bj", action="store_true", help="是否包含北交所")
    p.add_argument("--no-cache", action="store_true", help="不使用行情快照缓存")
    p.add_argument("--fresh", action="store_true", help="忽略当日增强评分缓存，重新跑")
    return p.parse_args()


def main():
    args = parse_args()
    as_of = date.today().strftime("%Y-%m-%d")

    # ── 1. 行情快照 + 流动性闸门 ──────────────────────────────
    raw, source = load_market_snapshot(use_cache=not args.no_cache)
    universe_count = len(raw)
    prepared = prepare_universe(raw, include_bj=args.include_bj)
    filtered = prepared[
        (prepared["amount_billion"] >= args.min_amount)
        & (~prepared["name"].str.contains("ST", case=False, na=False))
        & (prepared["price"] > 0)
    ].copy()
    filtered = filtered.sort_values("amount_billion", ascending=False).reset_index(drop=True)
    gate_count = len(filtered)

    targets = filtered if args.enrich <= 0 else filtered.head(args.enrich)

    # ── 2. 宏观状态 → 行业加减分（整轮算一次）──────────────────
    cc = classify_credit_cycle()
    macro_adj = compute_industry_adjustments(
        cc.get("phase", ""), cc.get("ppi_trend")
    )

    # ── 3. 增强评分（带当日缓存 + 自动续跑）────────────────────
    enrich_cache_file = CACHE_DIR / f"screen_enrich_{date.today():%Y%m%d}.csv"
    done: dict[str, dict] = {}
    if not args.fresh and enrich_cache_file.exists():
        try:
            cached_df = pd.read_csv(enrich_cache_file)
            done = {r["ticker"]: r.to_dict() for _, r in cached_df.iterrows()}
        except Exception:
            done = {}

    factors: list[dict] = list(done.values())
    todo = [r for _, r in targets.iterrows() if r["ticker"] not in done]
    total, failed = len(todo), 0
    print(f"[进度] 闸门内 {gate_count} 只 | 待增强 {total} 只 | 已缓存 {len(done)} 只",
          file=sys.stderr)

    for i, row in enumerate(todo, 1):
        try:
            factors.append(enrich_factors(row, macro_adj))
        except Exception as e:
            failed += 1
            print(f"[WARN] enrich {row['ticker']}: {e}", file=sys.stderr)
        if i % 50 == 0 or i == total:
            print(f"[进度] 增强评分 {i}/{total}（失败 {failed}）", file=sys.stderr)
            _flush_enrich_cache(factors, enrich_cache_file)

    _flush_enrich_cache(factors, enrich_cache_file)
    save_industry_cache()

    if not factors:
        print("本轮无候选通过过滤")
        return

    # ── 4. 多镜头评分 + 排序 ─────────────────────────────────
    scored = []
    for f in factors:
        rec = dict(f)
        for lens in LENSES:
            s, reasons = score_lens(f, lens)
            rec[f"score_{lens}"] = round(s, 1)
            if lens == args.lens:
                rec["reason"] = "、".join(reasons[:4]) if reasons else "因子中性"
        scored.append(rec)

    result = pd.DataFrame(scored).sort_values(
        f"score_{args.lens}", ascending=False
    ).head(args.top).reset_index(drop=True)

    # ── 5. 输出 ──────────────────────────────────────────────
    _print_report(result, args, as_of, source, universe_count, gate_count,
                   len(factors), failed, cc, macro_adj)


# ════════════════════════════════════════════════════════════════
# 数据加载
# ════════════════════════════════════════════════════════════════
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
    raw = str(code).strip().lower()
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
    if raw.startswith(("8", "9", "4")):
        return f"{raw}.BJ"
    return None


def numeric_col(df: pd.DataFrame, col: str) -> pd.Series:
    if col not in df.columns:
        return pd.Series([math.nan] * len(df), index=df.index)
    return pd.to_numeric(df[col], errors="coerce")


def _flush_enrich_cache(factors: list[dict], path: Path) -> None:
    if not factors:
        return
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        pd.DataFrame(factors).drop_duplicates(subset=["ticker"], keep="last").to_csv(
            path, index=False
        )
    except Exception as e:
        print(f"[WARN] 增强缓存落盘失败: {e}", file=sys.stderr)


# ════════════════════════════════════════════════════════════════
# 增强：采集个股原始因子（不打分）
# ════════════════════════════════════════════════════════════════
def enrich_factors(row: pd.Series, macro_adj: dict[str, float]) -> dict:
    ticker = row["ticker"]
    tech = get_technical_position(ticker)
    val = get_valuation(ticker)
    fin = get_financials_summary(ticker)
    rps = compute_rps(ticker, periods=(63,))

    sw_industry = get_stock_sw_industry(ticker)
    macro_fit = float(macro_adj.get(sw_industry, 0.0)) if sw_industry else 0.0

    return {
        "ticker": ticker,
        "name": row["name"],
        "change_pct": round(float(row["change_pct"]), 2),
        "amount_billion": round(float(row["amount_billion"]), 2),
        "trend": tech.get("trend", "N/A"),
        "discount_52w": tech.get("discount_from_52w_high_pct"),
        "rps63": rps.get("rps_scores", {}).get("63d"),
        "pe_percentile": val.get("pe_percentile"),
        "roe": fin.get("roe"),
        "net_margin": fin.get("net_margin"),
        "debt": fin.get("asset_liability_ratio"),
        "sw_industry": sw_industry or "",
        "macro_fit": round(macro_fit, 1),
    }


def liquidity_score(amount_billion) -> float:
    """成交额对数评分，上限 25。"""
    a = float(amount_billion) if amount_billion is not None and not pd.isna(amount_billion) else 0.0
    return min(math.log10(max(a, 0.01) + 1) * 22, 25)


def _num(v, default=None):
    if v is None or (isinstance(v, float) and pd.isna(v)):
        return default
    try:
        return float(v)
    except (TypeError, ValueError):
        return default


# ════════════════════════════════════════════════════════════════
# 多镜头评分
# ════════════════════════════════════════════════════════════════
def score_lens(f: dict, lens: str) -> tuple[float, list[str]]:
    if lens == "value":
        return _score_value(f)
    if lens == "growth":
        return _score_growth(f)
    if lens == "reversal":
        return _score_reversal(f)
    return _score_composite(f)


def _score_composite(f: dict) -> tuple[float, list[str]]:
    """均衡镜头：流动性 + 趋势 + 动量 + 估值 + 财务 + 宏观，无单因子主导。"""
    score = liquidity_score(f.get("amount_billion"))
    reasons: list[str] = []
    trend = f.get("trend")
    if trend == "uptrend":
        score += 12; reasons.append("上升趋势")
    elif trend == "sideways":
        score += 7; reasons.append("横盘待确认")
    else:
        score -= 8; reasons.append("趋势偏弱")

    rps = _num(f.get("rps63"))
    if rps is not None:
        score += max(min(rps / 3, 15), -12)
        if rps > 10:
            reasons.append("RPS强")

    disc = _num(f.get("discount_52w"))
    if disc is not None:
        if disc >= -3:
            score -= 18; reasons.append("贴近52周高点(追高风险)")
        elif disc >= -10:
            score -= 7; reasons.append("接近52周高点")
        elif disc <= -45:
            score += 6; reasons.append("深度回调(潜在低吸)")

    pe = _num(f.get("pe_percentile"))
    if pe is not None:
        if pe < 40:
            score += 8; reasons.append("估值分位低")
        elif pe < 65:
            score += 3
        elif pe > 95:
            score -= 18; reasons.append("估值极端高位")
        elif pe > 80:
            score -= 12; reasons.append("估值偏热")

    roe = _num(f.get("roe"))
    if roe is not None:
        if roe >= 10:
            score += 8; reasons.append("ROE较好")
        elif roe < 0:
            score -= 10; reasons.append("ROE为负")

    nm = _num(f.get("net_margin"))
    if nm is not None:
        if nm >= 10:
            score += 5
        elif nm < 0:
            score -= 8

    debt = _num(f.get("debt"))
    if debt is not None and debt > 75:
        score -= 5; reasons.append("负债率偏高")

    score, reasons = _apply_macro(score, reasons, f)
    return score, reasons


def _score_value(f: dict) -> tuple[float, list[str]]:
    """深度价值镜头（姜诚/唐朝）：估值分位为王，要安全边际，不追动量。"""
    score = liquidity_score(f.get("amount_billion")) * 0.6
    reasons: list[str] = []

    pe = _num(f.get("pe_percentile"))
    if pe is not None:
        if pe < 20:
            score += 25; reasons.append("估值历史极低位")
        elif pe < 40:
            score += 15; reasons.append("估值分位低")
        elif pe < 60:
            score += 5
        elif pe > 95:
            score -= 25; reasons.append("估值极端高位")
        elif pe > 80:
            score -= 15; reasons.append("估值偏热")

    roe = _num(f.get("roe"))
    if roe is not None:
        if roe >= 15:
            score += 15; reasons.append("ROE优秀")
        elif roe >= 10:
            score += 8; reasons.append("ROE较好")
        elif roe >= 5:
            score += 3
        elif roe < 0:
            score -= 20; reasons.append("亏损(非价值标的)")

    debt = _num(f.get("debt"))
    if debt is not None:
        if debt < 40:
            score += 6
        elif debt > 85:
            score -= 18; reasons.append("高杠杆")
        elif debt > 70:
            score -= 10; reasons.append("负债率偏高")

    disc = _num(f.get("discount_52w"))
    if disc is not None:
        if disc <= -30:
            score += 8; reasons.append("深度回调(安全边际)")
        elif disc <= -15:
            score += 4
        elif disc >= -3:
            score -= 6; reasons.append("贴高点(无安全边际)")

    nm = _num(f.get("net_margin"))
    if nm is not None:
        if nm >= 15:
            score += 6
        elif nm >= 8:
            score += 3
        elif nm < 0:
            score -= 10

    trend = f.get("trend")  # 价值镜头不奖励动量，只轻微表态
    if trend == "downtrend":
        score -= 3
    elif trend == "uptrend":
        score += 2

    score, reasons = _apply_macro(score, reasons, f)
    return score, reasons


def _score_growth(f: dict) -> tuple[float, list[str]]:
    """成长镜头（欧奈尔/朱少醒）：趋势 + 相对强度 + 盈利能力，容忍较高估值。"""
    score = liquidity_score(f.get("amount_billion"))
    reasons: list[str] = []

    trend = f.get("trend")
    if trend == "uptrend":
        score += 18; reasons.append("上升趋势")
    elif trend == "sideways":
        score += 5; reasons.append("横盘待确认")
    else:
        score -= 15; reasons.append("趋势走坏")

    rps = _num(f.get("rps63"))
    if rps is not None:
        score += max(min(rps / 2.5, 20), -10)
        if rps > 10:
            reasons.append("RPS强")

    nm = _num(f.get("net_margin"))
    if nm is not None:
        if nm >= 15:
            score += 12; reasons.append("高净利率")
        elif nm >= 10:
            score += 7
        elif nm >= 5:
            score += 3
        elif nm < 0:
            score -= 12; reasons.append("净利率为负")

    roe = _num(f.get("roe"))
    if roe is not None:
        if roe >= 15:
            score += 10; reasons.append("ROE优秀")
        elif roe >= 10:
            score += 6
        elif roe < 0:
            score -= 12

    pe = _num(f.get("pe_percentile"))
    if pe is not None:
        if pe < 40:
            score += 5; reasons.append("估值分位低")
        elif pe > 95:
            score -= 12; reasons.append("估值极端高位")

    disc = _num(f.get("discount_52w"))
    if disc is not None:
        if disc >= -3:
            score -= 8; reasons.append("贴近52周高点(追高风险)")
        elif disc <= -45:
            score -= 5; reasons.append("破位深跌(成长逻辑存疑)")

    score, reasons = _apply_macro(score, reasons, f)
    return score, reasons


def _score_reversal(f: dict) -> tuple[float, list[str]]:
    """困境反转镜头（冯柳/董宝珍）：深度回调为王，但要求'未破产'——亏损重罚。"""
    score = liquidity_score(f.get("amount_billion")) * 0.7
    reasons: list[str] = []

    disc = _num(f.get("discount_52w"))
    if disc is not None:
        if disc <= -50:
            score += 20; reasons.append("极深回调(强反转候选)")
        elif disc <= -35:
            score += 14; reasons.append("深度回调")
        elif disc <= -20:
            score += 7; reasons.append("明显回调")
        elif disc >= -10:
            score -= 10; reasons.append("贴近高点(无反转空间)")

    roe = _num(f.get("roe"))  # "未破产"闸门
    if roe is not None:
        if roe >= 5:
            score += 8; reasons.append("仍盈利(反转基础)")
        elif roe >= 0:
            score += 2
        else:
            score -= 15; reasons.append("亏损(可能接飞刀)")

    pe = _num(f.get("pe_percentile"))
    if pe is not None:
        if pe < 40:
            score += 10; reasons.append("估值分位低")
        elif pe < 60:
            score += 4
        elif pe > 90:
            score -= 10; reasons.append("估值偏高")

    trend = f.get("trend")
    if trend == "sideways":
        score += 8; reasons.append("横盘筑底")
    elif trend == "uptrend":
        score += 5; reasons.append("反转确认中")
    else:
        score -= 2

    nm = _num(f.get("net_margin"))
    if nm is not None:
        if nm < 0:
            score -= 10
        elif nm >= 8:
            score += 4

    debt = _num(f.get("debt"))
    if debt is not None and debt > 80:
        score -= 12; reasons.append("高杠杆(财务困境风险)")

    score, reasons = _apply_macro(score, reasons, f)
    return score, reasons


def _apply_macro(score: float, reasons: list[str], f: dict) -> tuple[float, list[str]]:
    macro_fit = _num(f.get("macro_fit"), 0.0)
    if macro_fit and abs(macro_fit) >= 2:
        score += macro_fit
        ind = f.get("sw_industry") or "行业"
        reasons.append(f"宏观{'顺风' if macro_fit > 0 else '逆风'}({ind}{macro_fit:+.0f})")
    return score, reasons


# ════════════════════════════════════════════════════════════════
# 输出
# ════════════════════════════════════════════════════════════════
def _print_report(result, args, as_of, source, universe_count, gate_count,
                   enriched_count, failed, cc, macro_adj):
    print(f"# 全市场候选筛选 Top {args.top} · {args.lens} 镜头（as of {as_of}）\n")
    print(f"- 原始快照: {universe_count} 只")
    print(f"- 数据源: {source}")
    print(f"- 流动性闸门后: {gate_count} 只"
          f"（成交额 >= {args.min_amount} 亿，排除 ST/停牌{'' if args.include_bj else '/北交所'}）")
    print(f"- 增强评分: {enriched_count} 只"
          f"（{'闸门内全部' if args.enrich <= 0 else f'--enrich 限 {args.enrich}'}"
          f"{f'，失败 {failed}' if failed else ''}）")
    print(f"- 排序镜头: **{args.lens}**（可选 {'/'.join(LENSES)}）")
    print(f"- 宏观状态: {cc.get('phase', 'N/A')}"
          f" | PPI {cc.get('ppi_yoy', 'N/A')}% {cc.get('ppi_trend', '')}")
    print("- 初筛已去动量化：闸门=纯流动性，当日涨幅不再参与初筛（避免漏掉未启动标的）")
    print()

    print("| 排名 | 股票 | 名称 | 行业 | {lens}分 | 综合分 | 涨跌幅 | 成交额(亿) | "
          "距52周高 | 趋势 | RPS63 | PE分位 | ROE | 净利率 | 宏观 | 主要理由 |"
          .format(lens=args.lens))
    print("|---:|---|---|---|---:|---:|---:|---:|---:|---|---:|---:|---:|---:|---:|---|")
    for idx, row in result.iterrows():
        disc = row.get("discount_52w")
        disc_str = f"{disc:.1f}%" if disc is not None and not pd.isna(disc) else "N/A"
        mf = _num(row.get("macro_fit"), 0.0)
        print(
            "| {rank} | {ticker} | {name} | {ind} | {lscore:.1f} | {cscore:.1f} | "
            "{change:.2f}% | {amount:.1f} | {disc} | {trend} | {rps63} | {pe_pct} | "
            "{roe} | {margin} | {mf:+.0f} | {reason} |".format(
                rank=idx + 1,
                ticker=row["ticker"],
                name=row["name"],
                ind=row.get("sw_industry") or "—",
                lscore=row[f"score_{args.lens}"],
                cscore=row["score_composite"],
                change=row["change_pct"],
                amount=row["amount_billion"],
                disc=disc_str,
                trend=row.get("trend", "N/A"),
                rps63=format_optional(row.get("rps63")),
                pe_pct=format_optional(row.get("pe_percentile")),
                roe=format_optional(row.get("roe")),
                margin=format_optional(row.get("net_margin")),
                mf=mf,
                reason=row.get("reason", ""),
            )
        )

    print("\n> [事实] 快照来自 akshare，增强指标来自本地 stock_data 工具。")
    print("> [推断] 初筛=纯流动性闸门，无当日动量偏向；增强阶段做估值/趋势/财务/宏观多因子评分。")
    print(f"> [推断] 当前以 **{args.lens}** 镜头排序；同一批因子可切换 value/growth/reversal 重排。")
    print("> [推断] 宏观联动：信用周期+PPI → 所属行业加减分（见 kb/taxonomy/macro-industry-mapping.yaml）。")
    print("> [提示] 得分用于候选排序，不等同于买入建议；仍需公告、新闻、风险检查二次确认。")


def format_optional(value):
    if value is None or pd.isna(value):
        return "N/A"
    return f"{float(value):.1f}"


if __name__ == "__main__":
    main()
