"""单股 K线、财报、估值数据"""

from __future__ import annotations
import sys
from datetime import date, timedelta
from typing import Optional
import pandas as pd


def get_kline(ticker: str, period: int = 120, as_of: Optional[str] = None,
              adjust: str = "hfq") -> pd.DataFrame:
    """
    获取 K 线数据（日线）。
    ticker: 600519.SH 或 000858.SZ 格式
    period: 获取近 N 个交易日
    adjust: "hfq" 后复权（默认，用于技术指标）/ "" 不复权（实际市价，用于仓位换算）
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
        df = ak.stock_zh_a_daily(symbol=symbol, adjust=adjust)
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
        pe_df = ak.stock_zh_valuation_baidu(
            symbol=symbol, indicator="市盈率(TTM)", period="近一年"
        )
        pb_df = ak.stock_zh_valuation_baidu(
            symbol=symbol, indicator="市净率", period="近一年"
        )

        pe, pe_pct, pe_date = _latest_value_and_percentile(pe_df)
        pb, pb_pct, pb_date = _latest_value_and_percentile(pb_df)

        if pe is None and pb is None:
            return {"ticker": ticker, "error": "no valuation data"}

        return {
            "ticker": ticker,
            "pe_ttm": pe,
            "pb": pb,
            "pe_percentile": pe_pct,
            "pb_percentile": pb_pct,
            "valuation_date": pe_date or pb_date,
            "source": "akshare.stock_zh_valuation_baidu",
        }
    except Exception as e:
        print(f"[WARN] valuation {ticker}: {e}", file=sys.stderr)
        return {"ticker": ticker, "error": str(e)}


def get_announcements(ticker: str, limit: int = 5) -> list[dict]:
    """最近 N 条公告摘要"""
    import akshare as ak
    symbol = _normalize_ticker(ticker)
    try:
        end_date = date.today()
        begin_date = end_date - timedelta(days=90)
        result = ak.stock_individual_notice_report(
            security=symbol,
            symbol="全部",
            begin_date=begin_date.strftime("%Y%m%d"),
            end_date=end_date.strftime("%Y%m%d"),
        )
        if result is None or result.empty:
            return []
        if "公告日期" in result.columns:
            result = result.sort_values("公告日期", ascending=False)
        return result.head(limit).to_dict("records")
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


def _latest_value_and_percentile(df: pd.DataFrame) -> tuple[Optional[float], Optional[float], Optional[str]]:
    if df is None or df.empty or "value" not in df.columns:
        return None, None, None

    data = df.copy()
    if "date" in data.columns:
        data["date"] = pd.to_datetime(data["date"], errors="coerce")
        data = data.sort_values("date")
    series = pd.to_numeric(data["value"], errors="coerce").dropna()
    if series.empty:
        return None, None, None

    latest = round(float(series.iloc[-1]), 2)
    percentile = float(round((series < latest).mean() * 100, 1)) if len(series) > 10 else None
    latest_date = None
    if "date" in data.columns and pd.notna(data.iloc[-1]["date"]):
        latest_date = str(data.iloc[-1]["date"].date())
    return latest, percentile, latest_date
