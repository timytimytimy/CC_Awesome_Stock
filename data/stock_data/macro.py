"""
宏观数据流水线。
对接高善文（信用周期框架）+ Howard Marks（市场温度计）的核心数据需求。

数据源：akshare（主要走国家统计局/央行/同花顺等非东方财富源，相对稳定）。
"""

from __future__ import annotations
import sys
import re
import warnings
from pathlib import Path
from typing import Optional
import pandas as pd

warnings.filterwarnings("ignore")

CACHE_DIR = Path(__file__).resolve().parents[1] / ".cache" / "macro"


def _cache_get(name: str, ttl_hours: int = 24) -> Optional[pd.DataFrame]:
    """读缓存，TTL 内直接返回。"""
    import time
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    fp = CACHE_DIR / f"{name}.pkl"
    if not fp.exists():
        return None
    age_h = (time.time() - fp.stat().st_mtime) / 3600
    if age_h > ttl_hours:
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


def _parse_chinese_month(s: str) -> Optional[pd.Timestamp]:
    """'2026年04月份' → Timestamp('2026-04-01')"""
    m = re.match(r"(\d{4})年(\d{1,2})月", str(s))
    if not m:
        return None
    return pd.Timestamp(year=int(m.group(1)), month=int(m.group(2)), day=1)


def get_pmi(periods: int = 12) -> pd.DataFrame:
    """
    PMI（采购经理人指数），荣枯线 50。
    返回：date, manufacturing, manufacturing_yoy, non_manufacturing, non_manufacturing_yoy
    最近 N 期，按时间正序。
    """
    cached = _cache_get("pmi", ttl_hours=24 * 7)
    if cached is not None:
        return cached.tail(periods).reset_index(drop=True)
    import akshare as ak
    try:
        df = ak.macro_china_pmi()
        df["date"] = df["月份"].map(_parse_chinese_month)
        df = df.dropna(subset=["date"]).sort_values("date")
        df = df.rename(columns={
            "制造业-指数": "manufacturing",
            "制造业-同比增长": "manufacturing_yoy",
            "非制造业-指数": "non_manufacturing",
            "非制造业-同比增长": "non_manufacturing_yoy",
        })
        out = df[["date", "manufacturing", "manufacturing_yoy",
                  "non_manufacturing", "non_manufacturing_yoy"]].reset_index(drop=True)
        _cache_put("pmi", out)
        return out.tail(periods).reset_index(drop=True)
    except Exception as e:
        print(f"[WARN] pmi: {e}", file=sys.stderr)
        return pd.DataFrame()


def get_ppi(periods: int = 12) -> pd.DataFrame:
    """
    PPI 同比增长（生产者价格指数）。
    返回：date, ppi_yoy（同比%）
    """
    cached = _cache_get("ppi", ttl_hours=24 * 7)
    if cached is not None:
        return cached.tail(periods).reset_index(drop=True)
    import akshare as ak
    try:
        df = ak.macro_china_ppi()
        df["date"] = df["月份"].map(_parse_chinese_month)
        df = df.dropna(subset=["date"]).sort_values("date")
        df = df.rename(columns={"当月同比增长": "ppi_yoy"})
        out = df[["date", "ppi_yoy"]].reset_index(drop=True)
        _cache_put("ppi", out)
        return out.tail(periods).reset_index(drop=True)
    except Exception as e:
        print(f"[WARN] ppi: {e}", file=sys.stderr)
        return pd.DataFrame()


def get_cpi(periods: int = 12) -> pd.DataFrame:
    """CPI 同比增长。返回 date, cpi_yoy"""
    cached = _cache_get("cpi", ttl_hours=24 * 7)
    if cached is not None:
        return cached.tail(periods).reset_index(drop=True)
    import akshare as ak
    try:
        df = ak.macro_china_cpi_monthly()
        df["date"] = pd.to_datetime(df["日期"])
        df["cpi_yoy"] = pd.to_numeric(df["今值"], errors="coerce")
        df = df.dropna(subset=["date", "cpi_yoy"]).sort_values("date")
        out = df[["date", "cpi_yoy"]].reset_index(drop=True)
        _cache_put("cpi", out)
        return out.tail(periods).reset_index(drop=True)
    except Exception as e:
        print(f"[WARN] cpi: {e}", file=sys.stderr)
        return pd.DataFrame()


def get_m2(periods: int = 12) -> pd.DataFrame:
    """M2 同比增速。返回 date, m2_yoy"""
    cached = _cache_get("m2", ttl_hours=24 * 7)
    if cached is not None:
        return cached.tail(periods).reset_index(drop=True)
    import akshare as ak
    try:
        df = ak.macro_china_m2_yearly()
        df["date"] = pd.to_datetime(df["日期"])
        df["m2_yoy"] = pd.to_numeric(df["今值"], errors="coerce")
        df = df.dropna(subset=["date", "m2_yoy"]).sort_values("date")
        out = df[["date", "m2_yoy"]].reset_index(drop=True)
        _cache_put("m2", out)
        return out.tail(periods).reset_index(drop=True)
    except Exception as e:
        print(f"[WARN] m2: {e}", file=sys.stderr)
        return pd.DataFrame()


def get_social_financing(periods: int = 24) -> pd.DataFrame:
    """
    社会融资规模（亿元）。
    返回：date, social_financing（社融增量）, rmb_loan（人民币贷款增量）
    """
    cached = _cache_get("shrzgm", ttl_hours=24 * 7)
    if cached is not None:
        return cached.tail(periods).reset_index(drop=True)
    import akshare as ak
    try:
        df = ak.macro_china_shrzgm()
        # 月份格式：202510 表示 2025-10
        df["date"] = pd.to_datetime(df["月份"].astype(str), format="%Y%m")
        df = df.rename(columns={
            "社会融资规模增量": "social_financing",
            "其中-人民币贷款": "rmb_loan",
        })
        df["social_financing"] = pd.to_numeric(df["social_financing"], errors="coerce")
        df["rmb_loan"] = pd.to_numeric(df["rmb_loan"], errors="coerce")
        df = df.dropna(subset=["date"]).sort_values("date")
        out = df[["date", "social_financing", "rmb_loan"]].reset_index(drop=True)
        _cache_put("shrzgm", out)
        return out.tail(periods).reset_index(drop=True)
    except Exception as e:
        print(f"[WARN] shrzgm: {e}", file=sys.stderr)
        return pd.DataFrame()


def get_treasury_yields(periods: int = 60) -> pd.DataFrame:
    """
    中美各期限国债收益率 + 关键利差。
    返回：date, cn_10y, cn_10y_2y_spread, us_10y, cn_us_10y_spread
    """
    cached = _cache_get("treasury", ttl_hours=12)
    if cached is not None:
        return cached.tail(periods).reset_index(drop=True)
    import akshare as ak
    try:
        df = ak.bond_zh_us_rate()
        df = df.rename(columns={
            "日期": "date",
            "中国国债收益率10年": "cn_10y",
            "中国国债收益率2年": "cn_2y",
            "中国国债收益率10年-2年": "cn_10y_2y_spread",
            "美国国债收益率10年": "us_10y",
        })
        df["date"] = pd.to_datetime(df["date"])
        df = df.dropna(subset=["cn_10y"]).sort_values("date")
        df["cn_us_10y_spread"] = df["cn_10y"] - df["us_10y"]
        out = df[["date", "cn_10y", "cn_10y_2y_spread", "us_10y",
                  "cn_us_10y_spread"]].reset_index(drop=True)
        _cache_put("treasury", out)
        return out.tail(periods).reset_index(drop=True)
    except Exception as e:
        print(f"[WARN] treasury: {e}", file=sys.stderr)
        return pd.DataFrame()


def get_fed_rate(periods: int = 12) -> pd.DataFrame:
    """美联储基准利率历次决议。返回 date, fed_rate"""
    cached = _cache_get("fed", ttl_hours=24 * 30)
    if cached is not None:
        return cached.tail(periods).reset_index(drop=True)
    import akshare as ak
    try:
        df = ak.macro_bank_usa_interest_rate()
        df["date"] = pd.to_datetime(df["日期"])
        df["fed_rate"] = pd.to_numeric(df["今值"], errors="coerce")
        df = df.dropna(subset=["date", "fed_rate"]).sort_values("date")
        out = df[["date", "fed_rate"]].reset_index(drop=True)
        _cache_put("fed", out)
        return out.tail(periods).reset_index(drop=True)
    except Exception as e:
        print(f"[WARN] fed: {e}", file=sys.stderr)
        return pd.DataFrame()


def get_credit_pulse(window_months: int = 12) -> pd.DataFrame:
    """
    信贷脉冲（高善文核心领先指标）。
    定义：社融增量的滚动 N 月之和的同比变化率。
    正值 = 信用扩张加速，负值 = 信用收缩加速。
    领先权益市场约 6-9 个月。
    """
    sf = get_social_financing(periods=60)
    if sf.empty or len(sf) < window_months * 2:
        return pd.DataFrame()
    sf = sf.copy()
    sf["roll"] = sf["social_financing"].rolling(window_months).sum()
    sf["credit_pulse"] = sf["roll"].pct_change(window_months) * 100
    return sf[["date", "credit_pulse"]].dropna().reset_index(drop=True)


# ────────────────────────────────────────────────────────────────
# 高阶聚合：信用周期 / 市场温度计
# ────────────────────────────────────────────────────────────────

def classify_credit_cycle() -> dict:
    """
    信用周期定位（高善文框架简化版）。
    输出：phase（复苏/过热/滞胀/衰退），依据，置信度，策略含义。
    """
    pmi = get_pmi(periods=6)
    ppi = get_ppi(periods=6)
    pulse = get_credit_pulse()

    if pmi.empty or ppi.empty:
        return {"phase": "unknown", "reason": "数据缺失", "confidence": "low"}

    pmi_now = float(pmi.iloc[-1]["manufacturing"])
    pmi_trend = "↗" if pmi.iloc[-1]["manufacturing"] > pmi.iloc[-3]["manufacturing"] else "↘"
    ppi_now = float(ppi.iloc[-1]["ppi_yoy"])
    ppi_trend = "↗" if ppi.iloc[-1]["ppi_yoy"] > ppi.iloc[-3]["ppi_yoy"] else "↘"
    pulse_now = float(pulse.iloc[-1]["credit_pulse"]) if not pulse.empty else None
    pulse_trend = None
    if pulse_now is not None and len(pulse) >= 4:
        pulse_trend = "↗" if pulse.iloc[-1]["credit_pulse"] > pulse.iloc[-3]["credit_pulse"] else "↘"

    # 经典四象限简化判断
    expansion = pmi_now >= 50
    inflation = ppi_now > 0 and ppi_trend == "↗"

    if expansion and not inflation:
        phase = "复苏（经济扩张 + 通胀温和）"
        strategy = "利好成长股与制造业；股权资产积极配置；周期股可逐步介入"
    elif expansion and inflation:
        phase = "过热（经济扩张 + 通胀上行）"
        strategy = "周期、有色、能源占优；警惕货币收紧；股权资产中性"
    elif not expansion and inflation:
        phase = "滞胀（经济收缩 + 通胀仍高）"
        strategy = "防御为主：高股息、必需消费、黄金；股权资产偏空"
    else:
        phase = "衰退（经济收缩 + 通缩压力）"
        strategy = "现金/利率债优先；权益等待政策底；逆向布局优质资产"

    # 信贷脉冲前瞻：领先权益市场约 6-9 个月，是全系统最前瞻的单一指标。
    # 它的"方向"本身就是领先信号——不只是定位四象限。
    if pulse_trend == "↗":
        pulse_outlook = ("信贷脉冲回升 → [推断] 未来 6-9 个月市场风险偏好趋升，"
                         "权益资产中期偏多，利好成长股；选股优先 growth 镜头")
        pulse_lens_hint = "growth"
    elif pulse_trend == "↘":
        pulse_outlook = ("信贷脉冲回落 → [推断] 未来 6-9 个月市场风险偏好趋降，"
                         "中期转向防御；选股优先 value / reversal 镜头，控制成长股仓位")
        pulse_lens_hint = "value"
    else:
        pulse_outlook = "信贷脉冲方向不明（数据不足），暂不作前瞻判断"
        pulse_lens_hint = None

    return {
        "phase": phase,
        "pmi": pmi_now,
        "pmi_trend": pmi_trend,
        "ppi_yoy": ppi_now,
        "ppi_trend": ppi_trend,
        "credit_pulse": round(pulse_now, 2) if pulse_now is not None else None,
        "credit_pulse_trend": pulse_trend,
        "credit_pulse_outlook": pulse_outlook,
        "credit_pulse_lens_hint": pulse_lens_hint,
        "strategy_implication": strategy,
        "confidence": "mid",
        "as_of": str(pmi.iloc[-1]["date"].date()),
    }


def market_temperature() -> dict:
    """
    市场温度计（Howard Marks 框架本地化版）。
    用 A 股可获得的代理指标：估值分位 + 国债利差 + 涨停活跃度（外部传入）。
    输出温度评级：极冷 / 偏冷 / 中性 / 偏热 / 过热
    """
    ty = get_treasury_yields(periods=252)
    fed = get_fed_rate(periods=24)

    if ty.empty:
        return {"temperature": "unknown", "reason": "国债数据缺失"}

    cn_10y = float(ty.iloc[-1]["cn_10y"])
    cn_10y_yr_min = float(ty["cn_10y"].min())
    cn_10y_yr_max = float(ty["cn_10y"].max())
    cn_10y_pct = round((ty["cn_10y"] < cn_10y).mean() * 100, 1)

    spread_10_2 = float(ty.iloc[-1]["cn_10y_2y_spread"])
    # 中美利差：美国数据通常比中国晚 1 天，取最近一个非 nan
    valid_spread = ty["cn_us_10y_spread"].dropna()
    cn_us_spread = float(valid_spread.iloc[-1]) if not valid_spread.empty else None
    fed_rate = float(fed.iloc[-1]["fed_rate"]) if not fed.empty else None

    # 简化温度评分（0=极冷，100=过热）
    # 10年国债处于历史分位高 → 估值压力大 → 偏热？错——国债收益率低=资金便宜=股市估值中枢上移
    # 国债收益率低分位 → 流动性宽松 → 股市估值偏暖
    temp_score = 100 - cn_10y_pct  # 反向

    if temp_score >= 80:
        rating = "偏热（流动性极宽松）"
    elif temp_score >= 60:
        rating = "偏暖（流动性宽松）"
    elif temp_score >= 40:
        rating = "中性"
    elif temp_score >= 20:
        rating = "偏冷（流动性偏紧）"
    else:
        rating = "极冷（流动性紧张）"

    return {
        "rating": rating,
        "temp_score": round(temp_score, 1),
        "cn_10y": cn_10y,
        "cn_10y_1y_percentile": cn_10y_pct,
        "cn_10y_1y_range": f"{cn_10y_yr_min:.2f}-{cn_10y_yr_max:.2f}",
        "cn_10y_2y_spread": round(spread_10_2, 2),
        "cn_us_10y_spread": round(cn_us_spread, 2),
        "fed_rate": fed_rate,
        "interpretation": _interpret_yield_spreads(spread_10_2, cn_us_spread),
        "as_of": str(ty.iloc[-1]["date"].date()),
    }


def _interpret_yield_spreads(spread_10_2: float, cn_us_spread) -> str:
    """利差解读"""
    notes = []
    if spread_10_2 < 0:
        notes.append("中国国债期限利差倒挂 → 经济衰退预期")
    elif spread_10_2 < 0.3:
        notes.append("中国期限利差收窄 → 经济动能减弱")
    elif spread_10_2 > 1.0:
        notes.append("中国期限利差扩张 → 经济复苏预期")

    if cn_us_spread is not None:
        if cn_us_spread < -2:
            notes.append("中美10年利差深度倒挂 → 资本外流压力大、人民币贬值压力")
        elif cn_us_spread < -1:
            notes.append("中美10年利差倒挂 → 北上资金或承压")
        elif cn_us_spread > 0:
            notes.append("中美10年利差正值 → 资本流入支撑")

    return "；".join(notes) if notes else "利差结构相对平稳"


def get_macro_snapshot() -> dict:
    """
    一次性聚合所有宏观指标，用于报告生成。
    """
    snapshot = {
        "pmi": get_pmi(periods=6).to_dict("records"),
        "ppi": get_ppi(periods=6).to_dict("records"),
        "cpi": get_cpi(periods=6).to_dict("records"),
        "m2": get_m2(periods=6).to_dict("records"),
        "social_financing": get_social_financing(periods=6).to_dict("records"),
        "treasury": get_treasury_yields(periods=20).to_dict("records"),
        "credit_pulse": get_credit_pulse().tail(6).to_dict("records"),
        "credit_cycle": classify_credit_cycle(),
        "market_temperature": market_temperature(),
    }
    return snapshot
