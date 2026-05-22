"""
业绩预告 / 业绩快报 —— 系统的领先信号层。

为什么重要：业绩预告是 A 股**强制披露、字面意义前瞻**的信号——公司在正式财报
之前就告诉你"利润将大增/大减"。系统原本只量"当前状态"（趋势/RPS/估值分位都是
同步或滞后指标），业绩预告让选股第一次能"猎捕正在变好的公司"。

- 业绩预告（stock_yjyg_em）：预增/略增/扭亏/续盈/略减/预减/首亏/续亏 + 变动幅度
- 业绩快报（stock_yjkb_em）：正式财报前的快报，含同比/环比增速

全链路 fail-safe：取不到数据 → 该股 forecast_signal = 0，不报错。
"""

from __future__ import annotations

import sys
import time
from datetime import date
from pathlib import Path
from typing import Optional

import pandas as pd

_CACHE_DIR = Path(__file__).resolve().parents[1] / ".cache" / "earnings"

# 预告类型 → 方向
FORECAST_POSITIVE = ("预增", "略增", "扭亏", "续盈", "减亏")
FORECAST_NEGATIVE = ("预减", "略减", "首亏", "续亏", "增亏")


# ────────────────────────────────────────────────────────────
def _cache_get(name: str, ttl_hours: int = 24) -> Optional[pd.DataFrame]:
    fp = _CACHE_DIR / f"{name}.pkl"
    if not fp.exists():
        return None
    if (time.time() - fp.stat().st_mtime) / 3600 > ttl_hours:
        return None
    try:
        return pd.read_pickle(fp)
    except Exception:
        return None


def _cache_put(name: str, df: pd.DataFrame) -> None:
    try:
        _CACHE_DIR.mkdir(parents=True, exist_ok=True)
        df.to_pickle(_CACHE_DIR / f"{name}.pkl")
    except Exception as e:
        print(f"[WARN] earnings cache_put {name}: {e}", file=sys.stderr)


def _code_to_ticker(code: str) -> Optional[str]:
    c = str(code).strip().zfill(6)
    if c.startswith("6"):
        return f"{c}.SH"
    if c.startswith(("0", "3")):
        return f"{c}.SZ"
    if c.startswith(("4", "8", "9")):
        return f"{c}.BJ"
    return None


def latest_report_period(today: Optional[date] = None) -> str:
    """今天之前最近的季度末，返回 YYYYMMDD（业绩预告按报告期组织）。"""
    today = today or date.today()
    y, m = today.year, today.month
    # 季度末月：3/6/9/12；取已过去的最近一个
    for end_m, end_d in ((12, 31), (9, 30), (6, 30), (3, 31)):
        if m > end_m or (m == end_m and today.day >= end_d):
            return f"{y}{end_m:02d}{end_d:02d}"
    return f"{y - 1}1231"


# ────────────────────────────────────────────────────────────
# 业绩预告
# ────────────────────────────────────────────────────────────
def get_earnings_forecast(period: Optional[str] = None) -> pd.DataFrame:
    """
    取某报告期的业绩预告，聚焦"归属于上市公司股东的净利润"行。
    返回列：ticker, name, forecast_type, change_pct, reason, notice_date, period
    period 不传则自动用最近季度末；该期为空则回退上一季。
    """
    periods = [period] if period else [
        latest_report_period(),
        latest_report_period(date(date.today().year, max(date.today().month - 3, 1), 1)),
    ]
    for p in periods:
        df = _fetch_forecast(p)
        if not df.empty:
            return df
    return pd.DataFrame(columns=["ticker", "name", "forecast_type", "change_pct",
                                 "reason", "notice_date", "period"])


def _fetch_forecast(period: str) -> pd.DataFrame:
    cache_key = f"yjyg_{period}"
    cached = _cache_get(cache_key, ttl_hours=24)
    if cached is not None:
        return cached

    try:
        import akshare as ak
        raw = ak.stock_yjyg_em(date=period)
    except Exception as e:
        print(f"[WARN] stock_yjyg_em {period}: {e}", file=sys.stderr)
        return pd.DataFrame()

    if raw is None or raw.empty:
        return pd.DataFrame()

    # 只保留净利润口径（一只股票可能有净利润+营收两行）
    profit = raw[raw["预测指标"].astype(str).str.contains("净利润", na=False)].copy()
    if profit.empty:
        profit = raw.copy()

    rows = []
    for _, r in profit.iterrows():
        ticker = _code_to_ticker(r.get("股票代码"))
        if not ticker:
            continue
        rows.append({
            "ticker": ticker,
            "name": str(r.get("股票简称", "")),
            "forecast_type": str(r.get("预告类型", "")).strip(),
            "change_pct": pd.to_numeric(r.get("业绩变动幅度"), errors="coerce"),
            "reason": str(r.get("业绩变动原因") or "")[:60],
            "notice_date": str(r.get("公告日期", "")),
            "period": period,
        })
    df = pd.DataFrame(rows).drop_duplicates(subset=["ticker"], keep="first")
    _cache_put(cache_key, df)
    return df


# ────────────────────────────────────────────────────────────
# 分类 / 打分
# ────────────────────────────────────────────────────────────
def classify_forecast(forecast_type: str, change_pct: Optional[float]) -> dict:
    """
    预告类型 + 变动幅度 → 方向 + 领先信号分（约 -18 ~ +20）。
    信号分供 screen_all_market 作为"领先信号因子"加进个股得分。
    """
    ft = (forecast_type or "").strip()
    cp = change_pct if change_pct is not None and not pd.isna(change_pct) else None

    direction, signal = "neutral", 0.0
    if ft in FORECAST_POSITIVE:
        direction = "positive"
        if ft == "扭亏":
            signal = 12.0                       # 扭亏为盈：质变
        elif ft == "续盈":
            signal = 2.0                        # 续盈：维持，不算大变化
        elif ft == "预增":
            if cp is None:
                signal = 12.0
            elif cp >= 100:
                signal = 20.0
            elif cp >= 50:
                signal = 14.0
            else:
                signal = 9.0
        elif ft == "略增":
            signal = 5.0
        elif ft == "减亏":
            signal = 6.0                        # 亏损收窄：方向改善，但仍亏损
    elif ft in FORECAST_NEGATIVE:
        direction = "negative"
        if ft == "首亏":
            signal = -18.0
        elif ft == "续亏":
            signal = -15.0
        elif ft == "增亏":
            signal = -12.0                      # 亏损扩大
        elif ft == "预减":
            signal = -12.0 if (cp is None or cp <= -50) else -8.0
        elif ft == "略减":
            signal = -5.0
    elif ft in ("不确定",):
        direction, signal = "uncertain", -3.0

    return {"direction": direction, "signal": round(signal, 1),
            "forecast_type": ft, "change_pct": cp}


def get_forecast_map(period: Optional[str] = None) -> dict[str, dict]:
    """
    {ticker: {forecast_type, change_pct, direction, signal, notice_date, period}}
    供 screen_all_market 整轮调一次、个股查表。
    """
    df = get_earnings_forecast(period)
    result = {}
    for _, r in df.iterrows():
        cls = classify_forecast(r["forecast_type"], r["change_pct"])
        result[r["ticker"]] = {
            "forecast_type": cls["forecast_type"],
            "change_pct": cls["change_pct"],
            "direction": cls["direction"],
            "signal": cls["signal"],
            "notice_date": r["notice_date"],
            "period": r["period"],
        }
    return result
