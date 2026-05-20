"""大盘、行业、资金流数据"""

from __future__ import annotations
import sys
from datetime import date, timedelta
from typing import Optional
import pandas as pd


def _today() -> str:
    return date.today().strftime("%Y%m%d")


def get_index_snapshot(as_of: Optional[str] = None) -> dict:
    """
    返回主要指数的价格和均线状态。
    as_of: YYYY-MM-DD 格式，默认今日。
    """
    import akshare as ak

    indices = {
        "sh": "000001",   # 上证指数
        "sz300": "399300",  # 沪深300
        "cyb": "399006",   # 创业板
        "kcb": "000688",   # 科创50
    }
    result = {}
    for name, code in indices.items():
        try:
            df = ak.stock_zh_index_daily(symbol=f"sh{code}" if code.startswith("0") else f"sz{code}")
            if df is None or df.empty:
                result[name] = {"error": "no data"}
                continue
            df["date"] = pd.to_datetime(df["date"])
            if as_of:
                cutoff = pd.to_datetime(as_of)
                df = df[df["date"] <= cutoff]
            df = df.sort_values("date")
            df["ma20"] = df["close"].rolling(20).mean()
            df["ma60"] = df["close"].rolling(60).mean()
            latest = df.iloc[-1]
            prev = df.iloc[-2] if len(df) > 1 else latest
            result[name] = {
                "date": str(latest["date"].date()),
                "close": float(latest["close"]),
                "change_pct": round((latest["close"] - prev["close"]) / prev["close"] * 100, 2),
                "ma20": round(float(latest["ma20"]), 2) if pd.notna(latest["ma20"]) else None,
                "ma60": round(float(latest["ma60"]), 2) if pd.notna(latest["ma60"]) else None,
                "above_ma20": bool(latest["close"] > latest["ma20"]) if pd.notna(latest["ma20"]) else None,
                "above_ma60": bool(latest["close"] > latest["ma60"]) if pd.notna(latest["ma60"]) else None,
                "volume": float(latest.get("volume", 0)),
            }
        except Exception as e:
            result[name] = {"error": str(e)}
            print(f"[WARN] index {name}: {e}", file=sys.stderr)
    return result


def get_limit_up_stats(as_of: Optional[str] = None) -> dict:
    """涨停数量、连板高度、封板率"""
    import akshare as ak
    trade_date = (as_of or date.today().strftime("%Y-%m-%d")).replace("-", "")
    try:
        df = ak.stock_zt_pool_em(date=trade_date)
        if df is None or df.empty:
            return {"limit_up_count": 0, "max_consecutive": 0, "seal_rate": None, "error": "empty"}
        count = len(df)
        max_consec = int(df["连续涨停天数"].max()) if "连续涨停天数" in df.columns else 0
        return {
            "limit_up_count": count,
            "max_consecutive": max_consec,
            "date": trade_date,
        }
    except Exception as e:
        print(f"[WARN] limit_up_stats: {e}", file=sys.stderr)
        return {"limit_up_count": None, "max_consecutive": None, "error": str(e)}


def get_sector_performance(top_n: int = 10, period_days: int = 5) -> pd.DataFrame:
    """
    同花顺行业板块今日涨跌幅排名（含净流入、领涨股）。
    数据源：同花顺（非东方财富，稳定可用）。
    返回 DataFrame，列：industry, change_pct, net_inflow, volume, leader_stock, leader_pct
    period_days 参数保留接口兼容，实际返回今日数据。
    """
    import akshare as ak
    try:
        df = ak.stock_board_industry_summary_ths()
        if df is None or df.empty:
            return pd.DataFrame()
        df = df.rename(columns={
            "板块":     "industry",
            "涨跌幅":   "change_pct",
            "总成交额": "volume",
            "净流入":   "net_inflow",
            "领涨股":   "leader_stock",
            "领涨股-涨跌幅": "leader_pct",
            "上涨家数": "up_count",
            "下跌家数": "down_count",
        })
        for c in ["change_pct", "volume", "net_inflow", "leader_pct"]:
            if c in df.columns:
                df[c] = pd.to_numeric(df[c], errors="coerce")
        df = df.sort_values("change_pct", ascending=False)
        cols = [c for c in ["industry", "change_pct", "net_inflow", "volume",
                             "leader_stock", "leader_pct", "up_count", "down_count"]
                if c in df.columns]
        return df.head(top_n)[cols].reset_index(drop=True)
    except Exception as e:
        print(f"[WARN] sector_performance (ths): {e}", file=sys.stderr)
        return pd.DataFrame()


def get_northbound_flow(days: int = 5) -> dict:
    """北上资金近 N 日净流入（亿元）"""
    import akshare as ak
    try:
        df = ak.stock_hsgt_hist_em(symbol="北向资金")
        if df is None or df.empty:
            return {"total_5d": None, "error": "empty"}
        df = df.sort_values(df.columns[0], ascending=False).head(days)
        flow_col = [c for c in df.columns if "净" in c or "flow" in c.lower()]
        if not flow_col:
            return {"total_5d": None, "error": "column not found"}
        total = float(df[flow_col[0]].sum())
        return {"total_5d": round(total, 2), "days": days}
    except Exception as e:
        print(f"[WARN] northbound_flow: {e}", file=sys.stderr)
        return {"total_5d": None, "error": str(e)}
