"""
行业基本面流水线。
对接邱国鹭"好行业好公司低预期"+ 唐朝/唐朝"行业可见性"+ 巴菲特"护城河"框架。

核心数据：
- 申万一级行业 PE/PB/股息（一次性快照）
- 同花顺行业指数 3 年 K 线（算价格分位）
- 巨潮证监会行业 PE 历史（按需回溯）
"""

from __future__ import annotations
import sys
import time
import warnings
from pathlib import Path
from typing import Optional
import pandas as pd

warnings.filterwarnings("ignore")

CACHE_DIR = Path(__file__).resolve().parents[1] / ".cache" / "industry"


def _cache_get(name: str, ttl_hours: int = 24) -> Optional[pd.DataFrame]:
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    fp = CACHE_DIR / f"{name}.pkl"
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
        CACHE_DIR.mkdir(parents=True, exist_ok=True)
        df.to_pickle(CACHE_DIR / f"{name}.pkl")
    except Exception as e:
        print(f"[WARN] cache_put {name}: {e}", file=sys.stderr)


# ────────────────────────────────────────────────────────────
# 1. 申万一级行业当前快照（PE/PB/股息）
# ────────────────────────────────────────────────────────────

def get_sw_industry_overview() -> pd.DataFrame:
    """
    申万一级行业当前估值快照（31 个一级行业）。
    返回：industry_code, industry_name, n_stocks, pe_static, pe_ttm, pb, dividend_yield
    """
    cached = _cache_get("sw_overview", ttl_hours=24)
    if cached is not None:
        return cached
    import akshare as ak
    try:
        df = ak.sw_index_first_info()
        df = df.rename(columns={
            "行业代码": "industry_code",
            "行业名称": "industry_name",
            "成份个数": "n_stocks",
            "静态市盈率": "pe_static",
            "TTM(滚动)市盈率": "pe_ttm",
            "市净率": "pb",
            "静态股息率": "dividend_yield",
        })
        for c in ["pe_static", "pe_ttm", "pb", "dividend_yield"]:
            df[c] = pd.to_numeric(df[c], errors="coerce")
        _cache_put("sw_overview", df)
        return df
    except Exception as e:
        print(f"[WARN] sw_overview: {e}", file=sys.stderr)
        return pd.DataFrame()


# ────────────────────────────────────────────────────────────
# 2. 同花顺行业指数历史 K 线
# ────────────────────────────────────────────────────────────

def get_industry_index_history(industry_name: str, days: int = 750) -> pd.DataFrame:
    """
    同花顺行业指数 K 线（默认 3 年）。
    用于：
    - 行业指数价格历史分位（PE 分位的代理指标）
    - 行业相对强度（vs 沪深300）
    - 行业近 N 月动量
    """
    cache_key = f"ths_idx_{industry_name}"
    cached = _cache_get(cache_key, ttl_hours=12)
    if cached is not None:
        return cached.tail(days).reset_index(drop=True)

    import akshare as ak
    from datetime import date, timedelta
    end = date.today().strftime("%Y%m%d")
    start = (date.today() - timedelta(days=days + 30)).strftime("%Y%m%d")
    try:
        df = ak.stock_board_industry_index_ths(symbol=industry_name, start_date=start, end_date=end)
        if df is None or df.empty:
            return pd.DataFrame()
        df = df.rename(columns={
            "日期": "date",
            "开盘价": "open",
            "最高价": "high",
            "最低价": "low",
            "收盘价": "close",
            "成交量": "volume",
            "成交额": "amount",
        })
        df["date"] = pd.to_datetime(df["date"])
        for c in ["open", "high", "low", "close", "volume", "amount"]:
            if c in df.columns:
                df[c] = pd.to_numeric(df[c], errors="coerce")
        df = df.sort_values("date").reset_index(drop=True)
        _cache_put(cache_key, df)
        return df.tail(days).reset_index(drop=True)
    except Exception as e:
        print(f"[WARN] industry_index_history {industry_name}: {e}", file=sys.stderr)
        return pd.DataFrame()


# ────────────────────────────────────────────────────────────
# 3. 价格分位 + 动量
# ────────────────────────────────────────────────────────────

def compute_industry_metrics(industry_name: str) -> dict:
    """
    用同花顺行业指数算关键指标：
    - 价格历史分位（近 3 年）—— PE 分位的代理
    - 近 1/3/6/12 月动量
    - 距离 52 周高点回撤
    - 当前 MA60/MA250 关系
    """
    df = get_industry_index_history(industry_name, days=750)
    if df.empty or len(df) < 60:
        return {"industry": industry_name, "error": "数据不足"}

    latest = df.iloc[-1]
    close = float(latest["close"])

    # 价格历史分位（近 3 年）
    price_pct = round((df["close"] < close).mean() * 100, 1)

    # 动量
    def _ret(periods: int) -> Optional[float]:
        if len(df) < periods + 1:
            return None
        return round((close / df.iloc[-periods - 1]["close"] - 1) * 100, 2)

    momentum = {
        "1m": _ret(20),
        "3m": _ret(60),
        "6m": _ret(120),
        "12m": _ret(250),
    }

    # 52 周高低
    last_year = df.tail(250) if len(df) >= 250 else df
    high_52w = float(last_year["close"].max())
    low_52w = float(last_year["close"].min())
    drawdown_from_high = round((close / high_52w - 1) * 100, 2)
    rise_from_low = round((close / low_52w - 1) * 100, 2)

    # MA
    df["ma60"] = df["close"].rolling(60).mean()
    df["ma250"] = df["close"].rolling(250).mean()
    ma60 = float(df.iloc[-1]["ma60"]) if pd.notna(df.iloc[-1]["ma60"]) else None
    ma250 = float(df.iloc[-1]["ma250"]) if pd.notna(df.iloc[-1]["ma250"]) else None

    trend = _classify_trend(close, ma60, ma250)

    return {
        "industry": industry_name,
        "close": close,
        "as_of": str(latest["date"].date()),
        "price_percentile_3y": price_pct,
        "momentum": momentum,
        "high_52w": high_52w,
        "low_52w": low_52w,
        "drawdown_from_52w_high": drawdown_from_high,
        "rise_from_52w_low": rise_from_low,
        "ma60": ma60,
        "ma250": ma250,
        "trend": trend,
    }


def _classify_trend(close: float, ma60: Optional[float], ma250: Optional[float]) -> str:
    """趋势分类（参考 O'Neil 框架）"""
    if ma60 is None or ma250 is None:
        return "数据不足"
    if close > ma60 > ma250:
        return "明确上升趋势（多头排列）"
    if close < ma60 < ma250:
        return "明确下降趋势（空头排列）"
    if close > ma60 and ma60 < ma250:
        return "底部反弹（短期回升，长期仍弱）"
    if close < ma60 and ma60 > ma250:
        return "高位回调（短期回落，长期仍强）"
    return "横盘整理"


# ────────────────────────────────────────────────────────────
# 4. 综合行业位置评估（邱国鹭框架）
# ────────────────────────────────────────────────────────────

def classify_industry_position(industry_name: str, sw_row: Optional[pd.Series] = None) -> dict:
    """
    综合行业位置评估（邱国鹭"好行业低预期"框架）。

    输出：
    - position_label：低估改善 / 低估稳定 / 中位上行 / 中位下行 / 高位过热 / 高位回调
    - opportunity_score：0-100 综合机会评分
    - reasoning：评分依据
    """
    metrics = compute_industry_metrics(industry_name)
    if "error" in metrics:
        return {"industry": industry_name, "error": metrics["error"]}

    pe_ttm = None
    pb = None
    div_yield = None
    if sw_row is not None:
        pe_ttm = float(sw_row.get("pe_ttm", 0)) if pd.notna(sw_row.get("pe_ttm")) else None
        pb = float(sw_row.get("pb", 0)) if pd.notna(sw_row.get("pb")) else None
        div_yield = float(sw_row.get("dividend_yield", 0)) if pd.notna(sw_row.get("dividend_yield")) else None

    price_pct = metrics["price_percentile_3y"]
    mom_3m = metrics["momentum"].get("3m") or 0
    mom_6m = metrics["momentum"].get("6m") or 0
    trend = metrics["trend"]

    # 邱国鹭核心思想：低估值 + 改善方向 = 最优；高估值 + 恶化 = 最差
    valuation_level = (
        "低" if price_pct < 30 else
        "中" if price_pct < 70 else
        "高"
    )
    direction = (
        "改善" if mom_3m > 0 and mom_6m > -10 else
        "恶化" if mom_3m < -5 and mom_6m < -10 else
        "稳定"
    )

    position_label = f"{valuation_level}估值-{direction}"
    if valuation_level == "高" and "下降" in trend:
        position_label = "高位回调（警惕）"
    elif valuation_level == "高" and direction == "改善":
        position_label = "高位过热（追高风险）"
    elif valuation_level == "低" and direction == "改善":
        position_label = "低估改善（邱国鹭最优）⭐"
    elif valuation_level == "低" and direction == "恶化":
        position_label = "低估恶化（价值陷阱风险）"

    # 综合机会评分
    score = 50
    if valuation_level == "低":
        score += 20
    elif valuation_level == "高":
        score -= 15

    if direction == "改善":
        score += 15
    elif direction == "恶化":
        score -= 20

    if trend == "明确上升趋势（多头排列）":
        score += 10
    elif trend == "明确下降趋势（空头排列）":
        score -= 15
    elif trend == "底部反弹（短期回升，长期仍弱）":
        score += 8

    if pe_ttm is not None and pe_ttm < 15:
        score += 5
    elif pe_ttm is not None and pe_ttm > 60:
        score -= 5

    score = max(0, min(100, score))

    reasoning = (
        f"价格分位 {price_pct}%（近3年，{valuation_level}）"
        f" | 3月动量 {mom_3m:+.1f}%（方向：{direction}）"
        f" | 趋势：{trend}"
    )
    if pe_ttm:
        reasoning += f" | PE-TTM {pe_ttm:.1f}"
    if pb:
        reasoning += f" | PB {pb:.2f}"
    if div_yield:
        reasoning += f" | 股息率 {div_yield:.2f}%"

    return {
        "industry": industry_name,
        "position_label": position_label,
        "opportunity_score": round(score, 1),
        "valuation_level": valuation_level,
        "direction": direction,
        "reasoning": reasoning,
        "metrics": metrics,
        "pe_ttm": pe_ttm,
        "pb": pb,
        "dividend_yield": div_yield,
    }


# ────────────────────────────────────────────────────────────
# 5. 批量行业体检（主线筛选核心）
# ────────────────────────────────────────────────────────────

def batch_industry_position(industry_names: list[str]) -> pd.DataFrame:
    """
    对一组行业批量做位置评估。
    返回按 opportunity_score 排序的 DataFrame。
    """
    sw_df = get_sw_industry_overview()
    sw_map = {}
    if not sw_df.empty:
        sw_map = {row["industry_name"]: row for _, row in sw_df.iterrows()}

    results = []
    for name in industry_names:
        sw_row = sw_map.get(name)
        if sw_row is None:
            # 同花顺名字可能和申万不同，模糊匹配
            for k, v in sw_map.items():
                if name in k or k in name:
                    sw_row = v
                    break
        result = classify_industry_position(name, sw_row)
        if "error" not in result:
            results.append({
                "industry": result["industry"],
                "position_label": result["position_label"],
                "score": result["opportunity_score"],
                "price_pct_3y": result["metrics"]["price_percentile_3y"],
                "trend": result["metrics"]["trend"],
                "mom_3m": result["metrics"]["momentum"].get("3m"),
                "mom_6m": result["metrics"]["momentum"].get("6m"),
                "drawdown_52w": result["metrics"]["drawdown_from_52w_high"],
                "pe_ttm": result.get("pe_ttm"),
                "pb": result.get("pb"),
                "dividend_yield": result.get("dividend_yield"),
                "reasoning": result["reasoning"],
            })

    if not results:
        return pd.DataFrame()
    return pd.DataFrame(results).sort_values("score", ascending=False).reset_index(drop=True)
