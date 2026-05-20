"""新闻、公告、研报摘要"""

from __future__ import annotations
import sys
from typing import Optional


def get_stock_news(ticker: str, limit: int = 10) -> list[dict]:
    """个股相关新闻（来自东财）"""
    import akshare as ak
    symbol = ticker.split(".")[0]
    try:
        df = ak.stock_news_em(symbol=symbol)
        if df is None or df.empty:
            return []
        cols = list(df.columns)
        return df.head(limit)[cols].to_dict("records")
    except Exception as e:
        print(f"[WARN] news {ticker}: {e}", file=sys.stderr)
        return []


def get_industry_news(industry_name: str, limit: int = 5) -> list[dict]:
    """行业相关新闻"""
    import akshare as ak
    try:
        df = ak.stock_board_industry_info_em(symbol=industry_name)
        if df is None or df.empty:
            return []
        return df.head(limit).to_dict("records")
    except Exception as e:
        print(f"[WARN] industry_news {industry_name}: {e}", file=sys.stderr)
        return []
