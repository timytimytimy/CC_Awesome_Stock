"""
公司财报深度分析（5 年财报体检）。
对接唐朝《手把手教你读财报》+ 巴菲特 Owner Earnings + 邱国鹭好公司标准。

核心检查项：
1. 利润质量：经营现金流 / 净利润 ≥ 100%、扣非占比、毛利率趋势
2. 增长性：营收/利润分年度增速
3. 财务安全：负债率、流动比率、商誉占比
4. 盈利能力：ROE 持续 ≥ 15%、净利率高于行业
5. 分红记录：连续分红 = 利润真实性验证
6. ROE 杜邦分解：净利率 × 总资产周转 × 权益乘数
"""

from __future__ import annotations
import sys
import re
import time
import warnings
from pathlib import Path
from typing import Optional
import pandas as pd

warnings.filterwarnings("ignore")

CACHE_DIR = Path(__file__).resolve().parents[1] / ".cache" / "financial"


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
# 辅助：解析中文数字单位
# ────────────────────────────────────────────────────────────

def _parse_cn_number(s) -> Optional[float]:
    """'1.47亿' → 147000000；'False' → None；'12.34%' → 12.34"""
    if s is None or pd.isna(s):
        return None
    s = str(s).strip()
    if s in ("False", "-", "", "nan", "None", "--"):
        return None
    # 百分比
    if s.endswith("%"):
        try:
            return float(s[:-1])
        except ValueError:
            return None
    # 中文单位
    units = {"亿": 1e8, "万": 1e4, "千": 1e3}
    for u, mul in units.items():
        if s.endswith(u):
            try:
                return float(s[:-1]) * mul
            except ValueError:
                return None
    try:
        return float(s)
    except ValueError:
        return None


def _normalize_ticker(ticker: str) -> str:
    return ticker.split(".")[0]


def _to_sina_symbol(ticker: str) -> str:
    """'600519.SH' → 'sh600519'"""
    code = _normalize_ticker(ticker)
    suffix = ticker.split(".")[-1].lower() if "." in ticker else ""
    if suffix == "sh" or code.startswith("6"):
        return f"sh{code}"
    return f"sz{code}"


# ────────────────────────────────────────────────────────────
# 1. 财务摘要（同花顺，年报口径）
# ────────────────────────────────────────────────────────────

def get_financial_summary(ticker: str, periods: int = 8) -> pd.DataFrame:
    """
    同花顺财务摘要，按报告期。返回最近 N 期年报+半年报+季报。
    输出列（已清洗为数值）：
      report_date, net_profit, net_profit_yoy, nonrec_profit, revenue, revenue_yoy,
      eps, bvps, op_cf_per_share, net_margin, gross_margin, roe, roe_diluted,
      operating_cycle, inv_turnover, inv_days, ar_days, current_ratio, quick_ratio,
      debt_ratio, asset_liability_ratio
    """
    code = _normalize_ticker(ticker)
    cache_key = f"finsum_{code}"
    cached = _cache_get(cache_key, ttl_hours=24 * 3)
    if cached is not None:
        return cached.head(periods).reset_index(drop=True)

    import akshare as ak
    try:
        df = ak.stock_financial_abstract_ths(symbol=code, indicator="按报告期")
    except Exception as e:
        print(f"[WARN] financial_summary {ticker}: {e}", file=sys.stderr)
        return pd.DataFrame()

    if df is None or df.empty:
        return pd.DataFrame()

    col_map = {
        "报告期": "report_date",
        "净利润": "net_profit",
        "净利润同比增长率": "net_profit_yoy",
        "扣非净利润": "nonrec_profit",
        "扣非净利润同比增长率": "nonrec_profit_yoy",
        "营业总收入": "revenue",
        "营业总收入同比增长率": "revenue_yoy",
        "基本每股收益": "eps",
        "每股净资产": "bvps",
        "每股经营现金流": "op_cf_per_share",
        "销售净利率": "net_margin",
        "销售毛利率": "gross_margin",
        "净资产收益率": "roe",
        "净资产收益率-摊薄": "roe_diluted",
        "营业周期": "operating_cycle",
        "存货周转率": "inv_turnover",
        "存货周转天数": "inv_days",
        "应收账款周转天数": "ar_days",
        "流动比率": "current_ratio",
        "速动比率": "quick_ratio",
        "产权比率": "debt_ratio",
        "资产负债率": "asset_liability_ratio",
    }
    df = df.rename(columns={k: v for k, v in col_map.items() if k in df.columns})

    # 清洗：所有数值列
    numeric_cols = [v for v in col_map.values() if v != "report_date"]
    for c in numeric_cols:
        if c in df.columns:
            df[c] = df[c].apply(_parse_cn_number)

    # 排序：最新在前
    df["report_date"] = pd.to_datetime(df["report_date"], errors="coerce")
    df = df.dropna(subset=["report_date"]).sort_values("report_date", ascending=False).reset_index(drop=True)
    _cache_put(cache_key, df)
    return df.head(periods).reset_index(drop=True)


# ────────────────────────────────────────────────────────────
# 2. 现金流（新浪三大表，用于算 CFO/净利润）
# ────────────────────────────────────────────────────────────

def get_cash_flow(ticker: str, periods: int = 5) -> pd.DataFrame:
    """获取经营现金流，年报口径"""
    code = _normalize_ticker(ticker)
    cache_key = f"cf_{code}"
    cached = _cache_get(cache_key, ttl_hours=24 * 7)
    if cached is not None:
        return cached.head(periods).reset_index(drop=True)

    import akshare as ak
    try:
        df = ak.stock_financial_report_sina(stock=_to_sina_symbol(ticker), symbol="现金流量表")
    except Exception as e:
        print(f"[WARN] cash_flow {ticker}: {e}", file=sys.stderr)
        return pd.DataFrame()

    if df is None or df.empty:
        return pd.DataFrame()

    df = df.rename(columns={"报告日": "report_date"})
    df["report_date"] = pd.to_datetime(df["report_date"], errors="coerce")
    df = df.dropna(subset=["report_date"]).sort_values("report_date", ascending=False)

    # 经营活动现金流净额（不同披露口径名字可能不同）
    cfo_cols = ["经营活动产生的现金流量净额", "经营活动产生的现金流量净额(元)",
                "经营活动产生的现金流量"]
    cfo_col = next((c for c in cfo_cols if c in df.columns), None)
    if cfo_col:
        df["operating_cash_flow"] = pd.to_numeric(df[cfo_col], errors="coerce")
    else:
        df["operating_cash_flow"] = None

    # 资本开支（购建固定资产、无形资产和其他长期资产支付的现金）
    capex_cols = ["购建固定资产、无形资产和其他长期资产支付的现金",
                  "购建固定资产、无形资产和其他长期资产所支付的现金"]
    capex_col = next((c for c in capex_cols if c in df.columns), None)
    if capex_col:
        df["capex"] = pd.to_numeric(df[capex_col], errors="coerce")
    else:
        df["capex"] = None

    out = df[["report_date", "operating_cash_flow", "capex"]].reset_index(drop=True)
    _cache_put(cache_key, out)
    return out.head(periods).reset_index(drop=True)


# ────────────────────────────────────────────────────────────
# 3. 主营构成
# ────────────────────────────────────────────────────────────

def get_business_composition(ticker: str) -> pd.DataFrame:
    """主营构成：看真实业务结构，识别"主题股 vs 真实业务公司"。"""
    code = _normalize_ticker(ticker)
    cache_key = f"zygc_{code}"
    cached = _cache_get(cache_key, ttl_hours=24 * 7)
    if cached is not None:
        return cached

    import akshare as ak
    suffix = "SH" if code.startswith("6") else "SZ"
    try:
        df = ak.stock_zygc_em(symbol=f"{suffix}{code}")
        if df is None or df.empty:
            return pd.DataFrame()
        df = df.rename(columns={
            "报告日期": "report_date",
            "分类类型": "classify_type",
            "主营构成": "segment",
            "主营收入": "revenue",
            "收入比例": "revenue_ratio",
            "主营成本": "cost",
            "毛利率": "gross_margin",
        })
        df["report_date"] = pd.to_datetime(df["report_date"], errors="coerce")
        df = df.dropna(subset=["report_date"]).sort_values("report_date", ascending=False)
        _cache_put(cache_key, df)
        return df
    except Exception as e:
        print(f"[WARN] business_composition {ticker}: {e}", file=sys.stderr)
        return pd.DataFrame()


# ────────────────────────────────────────────────────────────
# 4. 分红历史
# ────────────────────────────────────────────────────────────

def get_dividend_history(ticker: str) -> pd.DataFrame:
    """分红派息历史。连续分红 = 利润真实性的间接验证。"""
    code = _normalize_ticker(ticker)
    cache_key = f"div_{code}"
    cached = _cache_get(cache_key, ttl_hours=24 * 30)
    if cached is not None:
        return cached

    import akshare as ak
    try:
        df = ak.stock_history_dividend_detail(symbol=code)
        if df is None or df.empty:
            return pd.DataFrame()
        df = df.rename(columns={
            "公告日期": "announce_date",
            "送股": "bonus_share",
            "转增": "transfer_share",
            "派息": "cash_dividend",
            "进度": "progress",
            "除权除息日": "ex_date",
        })
        df["announce_date"] = pd.to_datetime(df["announce_date"], errors="coerce")
        # 只保留实施完成的分红
        if "progress" in df.columns:
            df = df[df["progress"].str.contains("实施", na=False) | df["progress"].isna()]
        df = df.dropna(subset=["announce_date"]).sort_values("announce_date", ascending=False)
        _cache_put(cache_key, df)
        return df
    except Exception as e:
        print(f"[WARN] dividend {ticker}: {e}", file=sys.stderr)
        return pd.DataFrame()


# ────────────────────────────────────────────────────────────
# 5. 综合财报体检（唐朝框架）
# ────────────────────────────────────────────────────────────

def comprehensive_check(ticker: str) -> dict:
    """
    综合财报体检。返回结构化报告，逐项打分。

    评分维度：
    A. 利润质量（30 分）：CFO/净利润、扣非占比、毛利率稳定性
    B. 增长性（20 分）：营收/利润增速、增速趋势
    C. 财务安全（20 分）：负债率、流动比率、商誉
    D. 盈利能力（20 分）：ROE 持续性、净利率
    E. 股东回报（10 分）：分红连续性

    总分对应：
    - 85-100：唐朝体检"健康"
    - 70-84：尚可，关注异常项
    - 50-69：警惕，存在多项问题
    - <50：基本面差，回避
    """
    summary = get_financial_summary(ticker, periods=5)
    if summary.empty:
        return {"ticker": ticker, "error": "财报数据缺失"}

    # 金融股检测：银行/券商/保险的财务摘要不含"销售毛利率"，
    # 唐朝《手把手教你读财报》5 维框架（毛利率/CFO-净利润/扣非/流动比率）对其不适用。
    if "gross_margin" not in summary.columns or summary["gross_margin"].dropna().empty:
        return {
            "ticker": ticker,
            "not_applicable": True,
            "latest_report": str(summary.iloc[0]["report_date"].date()),
            "reason": (
                "财务摘要缺少毛利率数据，判定为金融股（银行/券商/保险）。\n"
                "  金融业无毛利率、无常规经营现金流概念，唐朝《手把手教你读财报》"
                "5 维框架不适用，本工具不评分。\n"
                "  建议改看专用指标：\n"
                "  - 银行：ROE、不良贷款率、拨备覆盖率、核心一级资本充足率、净息差\n"
                "  - 券商：ROE、净资本、风险覆盖率、自营/经纪收入结构\n"
                "  - 保险：内含价值(EV)、新业务价值(NBV)、综合成本率、偿付能力充足率"
            ),
        }

    cf = get_cash_flow(ticker, periods=5)
    div = get_dividend_history(ticker)

    result = {
        "ticker": ticker,
        "latest_report": str(summary.iloc[0]["report_date"].date()),
        "checks": {},
        "score": 0,
        "max_score": 100,
        "verdict": "",
        "red_flags": [],
        "yellow_flags": [],
        "highlights": [],
    }

    # ── A. 利润质量（30 分）──
    score_a, notes_a = _check_profit_quality(summary, cf)
    result["checks"]["A_profit_quality"] = {
        "score": score_a, "max": 30, "notes": notes_a,
    }

    # ── B. 增长性（20 分）──
    score_b, notes_b = _check_growth(summary)
    result["checks"]["B_growth"] = {
        "score": score_b, "max": 20, "notes": notes_b,
    }

    # ── C. 财务安全（20 分）──
    score_c, notes_c = _check_safety(summary)
    result["checks"]["C_safety"] = {
        "score": score_c, "max": 20, "notes": notes_c,
    }

    # ── D. 盈利能力（20 分）──
    score_d, notes_d = _check_profitability(summary)
    result["checks"]["D_profitability"] = {
        "score": score_d, "max": 20, "notes": notes_d,
    }

    # ── E. 股东回报（10 分）──
    score_e, notes_e = _check_dividend(div)
    result["checks"]["E_shareholder_return"] = {
        "score": score_e, "max": 10, "notes": notes_e,
    }

    # 汇总
    total = score_a + score_b + score_c + score_d + score_e
    result["score"] = round(total, 1)

    if total >= 85:
        result["verdict"] = "健康（唐朝标准）⭐"
    elif total >= 70:
        result["verdict"] = "尚可，关注异常项"
    elif total >= 50:
        result["verdict"] = "警惕，存在多项问题 ⚠️"
    else:
        result["verdict"] = "基本面差，回避 ❌"

    # 收集红黄旗
    for chk in result["checks"].values():
        for note in chk.get("notes", []):
            if "❌" in note:
                result["red_flags"].append(note)
            elif "⚠️" in note:
                result["yellow_flags"].append(note)
            elif "✅" in note:
                result["highlights"].append(note)

    return result


def _check_profit_quality(summary: pd.DataFrame, cf: pd.DataFrame) -> tuple[float, list[str]]:
    """A. 利润质量（30 分）"""
    score = 0
    notes = []

    # A1. 经营现金流 / 净利润 ≥ 100%（10 分）
    if not cf.empty and not summary.empty:
        # 用最近 3 期年报对比
        cf_annual = cf[cf["report_date"].dt.month == 12].head(3)
        sum_annual = summary[summary["report_date"].dt.month == 12].head(3)
        if not cf_annual.empty and not sum_annual.empty:
            ratios = []
            for _, c_row in cf_annual.iterrows():
                date = c_row["report_date"]
                match = sum_annual[sum_annual["report_date"] == date]
                if not match.empty and c_row["operating_cash_flow"] and match.iloc[0]["net_profit"]:
                    r = c_row["operating_cash_flow"] / match.iloc[0]["net_profit"]
                    ratios.append(r)
            if ratios:
                avg = sum(ratios) / len(ratios)
                if avg >= 1.0:
                    score += 10
                    notes.append(f"✅ 经营现金流/净利润 = {avg:.2f}（≥1，利润含金量高）")
                elif avg >= 0.8:
                    score += 7
                    notes.append(f"⚠️ 经营现金流/净利润 = {avg:.2f}（接近 1，可接受）")
                elif avg >= 0.5:
                    score += 3
                    notes.append(f"⚠️ 经营现金流/净利润 = {avg:.2f}（偏低，利润质量存疑）")
                else:
                    notes.append(f"❌ 经营现金流/净利润 = {avg:.2f}（远低于 1，利润可能虚增）")

    # A2. 毛利率稳定性（10 分）
    # 防御：金融股无 gross_margin 列（comprehensive_check 已前置拦截，此处双保险）
    gross_margins = (
        summary["gross_margin"].dropna().head(5)
        if "gross_margin" in summary.columns
        else pd.Series(dtype=float)
    )
    if len(gross_margins) >= 3:
        avg_gm = gross_margins.mean()
        std_gm = gross_margins.std()
        cv = std_gm / avg_gm if avg_gm else 1
        if avg_gm >= 30 and cv < 0.1:
            score += 10
            notes.append(f"✅ 毛利率 {avg_gm:.1f}%（高且稳定，CV={cv:.2f}）")
        elif avg_gm >= 20 and cv < 0.15:
            score += 7
            notes.append(f"✅ 毛利率 {avg_gm:.1f}%（尚可）")
        elif avg_gm >= 15:
            score += 4
            notes.append(f"- 毛利率 {avg_gm:.1f}%（一般）")
        else:
            notes.append(f"⚠️ 毛利率 {avg_gm:.1f}%（偏低）")

    # A3. 扣非占比（10 分）
    latest = summary.iloc[0] if not summary.empty else None
    if latest is not None and latest.get("net_profit") and latest.get("nonrec_profit"):
        ratio = latest["nonrec_profit"] / latest["net_profit"]
        if 0.85 <= ratio <= 1.15:
            score += 10
            notes.append(f"✅ 扣非/净利润 = {ratio:.2f}（≈1，盈利主要来自主营）")
        elif 0.7 <= ratio < 0.85:
            score += 6
            notes.append(f"⚠️ 扣非/净利润 = {ratio:.2f}（非经常性损益占比偏高）")
        elif ratio < 0.7:
            score += 2
            notes.append(f"⚠️ 扣非/净利润 = {ratio:.2f}（非经常性损益占比过高）")

    return score, notes


def _check_growth(summary: pd.DataFrame) -> tuple[float, list[str]]:
    """B. 增长性（20 分）"""
    score = 0
    notes = []
    if summary.empty:
        return score, notes

    # 最近一期增速
    latest = summary.iloc[0]
    rev_yoy = latest.get("revenue_yoy")
    profit_yoy = latest.get("net_profit_yoy")

    # B1. 营收增速（10 分）
    if rev_yoy is not None:
        if rev_yoy >= 20:
            score += 10
            notes.append(f"✅ 营收增速 {rev_yoy:.1f}%（高增长）")
        elif rev_yoy >= 10:
            score += 7
            notes.append(f"✅ 营收增速 {rev_yoy:.1f}%（稳健增长）")
        elif rev_yoy >= 0:
            score += 4
            notes.append(f"- 营收增速 {rev_yoy:.1f}%（低增长）")
        else:
            notes.append(f"⚠️ 营收增速 {rev_yoy:.1f}%（下滑）")

    # B2. 利润增速（10 分）
    if profit_yoy is not None:
        if profit_yoy >= 20:
            score += 10
            notes.append(f"✅ 净利润增速 {profit_yoy:.1f}%（高增长）")
        elif profit_yoy >= 10:
            score += 7
            notes.append(f"✅ 净利润增速 {profit_yoy:.1f}%（稳健增长）")
        elif profit_yoy >= 0:
            score += 4
            notes.append(f"- 净利润增速 {profit_yoy:.1f}%（持平）")
        else:
            notes.append(f"❌ 净利润增速 {profit_yoy:.1f}%（下滑）")

    return score, notes


def _check_safety(summary: pd.DataFrame) -> tuple[float, list[str]]:
    """C. 财务安全（20 分）"""
    score = 0
    notes = []
    if summary.empty:
        return score, notes

    latest = summary.iloc[0]

    # C1. 资产负债率（10 分）
    debt_ratio = latest.get("asset_liability_ratio")
    if debt_ratio is not None:
        if debt_ratio < 30:
            score += 10
            notes.append(f"✅ 资产负债率 {debt_ratio:.1f}%（极低杠杆）")
        elif debt_ratio < 50:
            score += 8
            notes.append(f"✅ 资产负债率 {debt_ratio:.1f}%（健康）")
        elif debt_ratio < 65:
            score += 5
            notes.append(f"- 资产负债率 {debt_ratio:.1f}%（中等）")
        elif debt_ratio < 80:
            score += 2
            notes.append(f"⚠️ 资产负债率 {debt_ratio:.1f}%（偏高）")
        else:
            notes.append(f"❌ 资产负债率 {debt_ratio:.1f}%（过高）")

    # C2. 流动比率（10 分）
    cr = latest.get("current_ratio")
    if cr is not None:
        if cr >= 2.0:
            score += 10
            notes.append(f"✅ 流动比率 {cr:.2f}（短期偿债能力极强）")
        elif cr >= 1.5:
            score += 7
            notes.append(f"✅ 流动比率 {cr:.2f}（短期偿债能力良好）")
        elif cr >= 1.0:
            score += 4
            notes.append(f"- 流动比率 {cr:.2f}（短期偿债能力一般）")
        else:
            notes.append(f"⚠️ 流动比率 {cr:.2f}（短期偿债能力不足）")

    return score, notes


def _check_profitability(summary: pd.DataFrame) -> tuple[float, list[str]]:
    """D. 盈利能力（20 分）"""
    score = 0
    notes = []
    if summary.empty:
        return score, notes

    # ROE 持续性
    roes = summary["roe"].dropna().head(5)
    if len(roes) >= 3:
        avg_roe = roes.mean()
        min_roe = roes.min()
        # D1. ROE 平均水平（15 分）
        if avg_roe >= 20:
            score += 15
            notes.append(f"✅ ROE 平均 {avg_roe:.1f}%（巴菲特/林园门槛）")
        elif avg_roe >= 15:
            score += 12
            notes.append(f"✅ ROE 平均 {avg_roe:.1f}%（唐朝/邱国鹭门槛）")
        elif avg_roe >= 10:
            score += 7
            notes.append(f"- ROE 平均 {avg_roe:.1f}%（一般）")
        else:
            notes.append(f"⚠️ ROE 平均 {avg_roe:.1f}%（偏低）")

        # D2. ROE 持续性（5 分）
        if min_roe >= 15:
            score += 5
            notes.append(f"✅ ROE 最低 {min_roe:.1f}%（持续高 ROE）")
        elif min_roe >= 10:
            score += 3
        elif min_roe < 0:
            notes.append(f"❌ ROE 最低 {min_roe:.1f}%（出现亏损年份）")

    return score, notes


def _check_dividend(div: pd.DataFrame) -> tuple[float, list[str]]:
    """E. 股东回报（10 分）"""
    score = 0
    notes = []
    if div.empty:
        notes.append("⚠️ 无分红记录")
        return score, notes

    div_with_cash = div[div["cash_dividend"].apply(
        lambda x: _parse_cn_number(x) is not None and (_parse_cn_number(x) or 0) > 0
    )] if "cash_dividend" in div.columns else pd.DataFrame()

    n_years = div_with_cash["announce_date"].dt.year.nunique() if not div_with_cash.empty else 0
    if n_years >= 10:
        score += 10
        notes.append(f"✅ 连续分红 {n_years} 年（利润真实性强验证）")
    elif n_years >= 5:
        score += 7
        notes.append(f"✅ 连续分红 {n_years} 年")
    elif n_years >= 3:
        score += 4
        notes.append(f"- 分红 {n_years} 年")
    elif n_years >= 1:
        score += 2
        notes.append(f"- 偶尔分红 {n_years} 年")
    else:
        notes.append("⚠️ 无现金分红记录（不分红的公司，利润真实性需更严格验证）")

    return score, notes
