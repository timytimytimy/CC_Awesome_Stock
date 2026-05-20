"""技术分析指标：趋势、动量、相对强度"""

from __future__ import annotations
from typing import Optional
import pandas as pd


def compute_rps(ticker: str, benchmark: str = "000300.SH",
                periods: tuple[int, ...] = (63, 126, 189, 252)) -> dict:
    """
    计算相对强度（RPS）：个股涨幅 vs 基准涨幅，按多个时间周期。
    periods 默认对应约 3/6/9/12 个月交易日。
    """
    from stock_data.company import get_kline

    df = get_kline(ticker, period=max(periods) + 10)
    if df.empty:
        return {"ticker": ticker, "rps": None, "error": "no kline"}

    benchmark_df = _get_benchmark_kline(benchmark, period=max(periods) + 10)
    benchmark_error = benchmark_df.empty

    result = {
        "ticker": ticker,
        "benchmark": benchmark,
        "rps_scores": {},
        "stock_returns": {},
        "benchmark_returns": {},
    }
    if benchmark_error:
        result["benchmark_error"] = "no benchmark kline"

    for p in periods:
        if len(df) < p:
            continue
        start_price = float(df.iloc[-p]["收盘"])
        end_price = float(df.iloc[-1]["收盘"])
        stock_return = (end_price - start_price) / start_price

        benchmark_return = None
        if not benchmark_error and len(benchmark_df) >= p:
            benchmark_start = float(benchmark_df.iloc[-p]["收盘"])
            benchmark_end = float(benchmark_df.iloc[-1]["收盘"])
            benchmark_return = (benchmark_end - benchmark_start) / benchmark_start

        key = f"{p}d"
        result["stock_returns"][key] = round(stock_return * 100, 2)
        if benchmark_return is None:
            result["rps_scores"][key] = round(stock_return * 100, 2)
        else:
            result["benchmark_returns"][key] = round(benchmark_return * 100, 2)
            result["rps_scores"][key] = round((stock_return - benchmark_return) * 100, 2)

    return result


def _get_benchmark_kline(benchmark: str, period: int) -> pd.DataFrame:
    import akshare as ak
    import sys

    symbol = _to_index_symbol(benchmark)
    try:
        df = ak.stock_zh_index_daily(symbol=symbol)
        if df is None or df.empty:
            return pd.DataFrame()
        df["date"] = pd.to_datetime(df["date"])
        df = df.sort_values("date").tail(period)
        df = df.rename(columns={"date": "日期", "close": "收盘"})
        return df.reset_index(drop=True)
    except Exception as e:
        print(f"[WARN] benchmark {benchmark}: {e}", file=sys.stderr)
        return pd.DataFrame()


def _to_index_symbol(benchmark: str) -> str:
    code = benchmark.split(".")[0]
    suffix = benchmark.split(".")[-1].lower() if "." in benchmark else ""
    if suffix == "sh" or code.startswith("0"):
        return f"sh{code}"
    return f"sz{code}"


def get_technical_position(ticker: str) -> dict:
    """
    判断当前股价相对于关键均线的位置和趋势。
    """
    from stock_data.company import get_kline

    df = get_kline(ticker, period=250)
    if df.empty:
        return {"ticker": ticker, "error": "no kline"}

    latest = df.iloc[-1]
    close = float(latest["收盘"])
    ma20 = float(latest["ma20"]) if pd.notna(latest.get("ma20")) else None
    ma60 = float(latest["ma60"]) if pd.notna(latest.get("ma60")) else None

    # 52周高低点
    week52 = df.tail(252)
    high52 = float(week52["收盘"].max())
    low52 = float(week52["收盘"].min())

    # 距离52周高点的折扣
    discount_from_high = round((close - high52) / high52 * 100, 1) if high52 else None

    # 趋势判断
    trend = "undefined"
    if ma20 and ma60:
        if close > ma20 > ma60:
            trend = "uptrend"
        elif close < ma20 < ma60:
            trend = "downtrend"
        else:
            trend = "sideways"

    return {
        "ticker": ticker,
        "close": close,
        "ma20": ma20,
        "ma60": ma60,
        "above_ma20": close > ma20 if ma20 else None,
        "above_ma60": close > ma60 if ma60 else None,
        "trend": trend,
        "high_52w": high52,
        "low_52w": low52,
        "discount_from_52w_high_pct": discount_from_high,
    }
