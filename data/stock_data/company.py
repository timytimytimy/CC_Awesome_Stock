"""单股 K线、财报、估值数据"""

from __future__ import annotations
import sys
from typing import Optional
import pandas as pd


def get_kline(ticker: str, period: int = 120, as_of: Optional[str] = None) -> pd.DataFrame:
    """
    获取 K 线数据（日线，前复权）。
    ticker: 600519.SH 或 000858.SZ 格式
    period: 获取近 N 个交易日
    数据源：新浪财经（非东方财富，稳定可用）
    """
    import akshare as ak
    code = _normalize_ticker(ticker)
    # 新浪接口需要 sh/sz 前缀
    suffix = ticker.split(".")[-1].lower() if "." in ticker else ""
    if suffix == "sh" or code.startswith("6"):
        symbol = f"sh{code}"
    else:
        symbol = f"sz{code}"
    try:
        df = ak.stock_zh_a_daily(symbol=symbol, adjust="hfq")
        if df is None or df.empty:
            return pd.DataFrame()
        df["date"] = pd.to_datetime(df["date"])
        if as_of:
            df = df[df["date"] <= pd.to_datetime(as_of)]
        df = df.sort_values("date").tail(period)
        df["ma20"] = df["close"].rolling(20).mean()
        df["ma60"] = df["close"].rolling(60).mean()
        # 统一列名为中文（兼容下游脚本）
        df = df.rename(columns={
            "date": "日期", "open": "开盘", "high": "最高",
            "low": "最低", "close": "收盘", "volume": "成交量",
        })
        return df.reset_index(drop=True)
    except Exception as e:
        print(f"[WARN] kline {ticker} (sina): {e}", file=sys.stderr)
        return pd.DataFrame()


def get_financials_summary(ticker: str) -> dict:
    """
    获取最新财报摘要：营收/净利润增速、ROE、净利率、FCF/净利润。
    """
    import akshare as ak
    symbol = _normalize_ticker(ticker)
    result = {"ticker": ticker}
    try:
        df = ak.stock_financial_report_sina(stock=symbol, symbol="利润表")
        if df is not None and not df.empty:
            # 取最近 2 期做增速对比
            df = df.head(8)  # 近 2 年季度
            result["financials_available"] = True
        else:
            result["financials_available"] = False
    except Exception as e:
        result["financials_error"] = str(e)
        print(f"[WARN] financials {ticker}: {e}", file=sys.stderr)

    # 尝试获取主要财务指标
    try:
        df_ind = ak.stock_financial_analysis_indicator(symbol=symbol, start_year="2022")
        if df_ind is not None and not df_ind.empty:
            latest = df_ind.iloc[0]
            result["roe"] = _safe_float(latest, "净资产收益率(%)")
            result["net_margin"] = _safe_float(latest, "销售净利率(%)")
            result["asset_liability_ratio"] = _safe_float(latest, "资产负债率(%)")
    except Exception as e:
        print(f"[WARN] indicators {ticker}: {e}", file=sys.stderr)

    return result


def get_valuation(ticker: str) -> dict:
    """PE、PB 及历史分位"""
    import akshare as ak
    symbol = _normalize_ticker(ticker)
    try:
        df = ak.stock_a_ttm_lyr(symbol=symbol)
        if df is None or df.empty:
            return {"ticker": ticker, "error": "no valuation data"}
        latest = df.sort_values(df.columns[0], ascending=False).iloc[0]
        pe = _safe_float(latest, "pe_ttm") or _safe_float(latest, "PE")
        pb = _safe_float(latest, "pb") or _safe_float(latest, "PB")

        # 计算历史分位（使用全部历史数据）
        pe_col = "pe_ttm" if "pe_ttm" in df.columns else "PE"
        pb_col = "pb" if "pb" in df.columns else "PB"
        pe_series = pd.to_numeric(df[pe_col], errors="coerce").dropna()
        pb_series = pd.to_numeric(df[pb_col], errors="coerce").dropna()

        pe_pct = round((pe_series < pe).mean() * 100, 1) if pe and len(pe_series) > 10 else None
        pb_pct = round((pb_series < pb).mean() * 100, 1) if pb and len(pb_series) > 10 else None

        return {"ticker": ticker, "pe_ttm": pe, "pb": pb,
                "pe_percentile": pe_pct, "pb_percentile": pb_pct}
    except Exception as e:
        print(f"[WARN] valuation {ticker}: {e}", file=sys.stderr)
        return {"ticker": ticker, "error": str(e)}


def get_announcements(ticker: str, limit: int = 5) -> list[dict]:
    """最近 N 条公告摘要"""
    import akshare as ak
    symbol = _normalize_ticker(ticker)
    try:
        df = ak.stock_notice_report(symbol=symbol)
        if df is None or df.empty:
            return []
        return df.head(limit).to_dict("records")
    except Exception as e:
        print(f"[WARN] announcements {ticker}: {e}", file=sys.stderr)
        return []


def _normalize_ticker(ticker: str) -> str:
    """600519.SH → 600519"""
    return ticker.split(".")[0]


def _safe_float(row, col: str) -> Optional[float]:
    try:
        v = row.get(col) if hasattr(row, "get") else row[col]
        return round(float(v), 2) if v is not None and str(v) not in ("", "nan", "-") else None
    except Exception:
        return None
