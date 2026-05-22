"""
反人性护栏 —— 散户亏钱主要亏在行为，不是分析。

FOMO 追高、亏损加仓、过度交易、连续亏损后报复性交易、反复改主意——
这些行为模式比任何选股公式都更决定散户的长期结果。本模块在**决策时**
检测这些陷阱并告警，是 journal_summary.py（事后复盘）的事前对应物。

全部为纯函数，便于测试；不碰网络。
阈值默认值可被 personal-profile.yaml 的 behavior 段覆盖。
"""

from __future__ import annotations

from datetime import date, datetime, timedelta
from typing import Optional

import pandas as pd

# ── 默认行为阈值（可被 profile.behavior 覆盖）──────────────────
DEFAULTS = {
    "max_trades_per_month": 8,      # 30 天内交易笔数上限
    "cooling_off_loss_streak": 3,   # 连续亏损 N 笔 → 冷静期
    "min_holding_days": 10,         # 单股最短持有期（中线）
    "flip_flop_lookback_days": 90,  # 反复改主意回看窗口
}


def _threshold(profile: Optional[dict], key: str):
    if profile:
        b = profile.get("behavior") or {}
        if key in b and b[key] is not None:
            return b[key]
    return DEFAULTS[key]


def _parse_date(v) -> Optional[date]:
    if v is None:
        return None
    if isinstance(v, datetime):
        return v.date()
    if isinstance(v, date):
        return v
    try:
        return datetime.strptime(str(v).strip(), "%Y-%m-%d").date()
    except (ValueError, TypeError):
        return None


def _warn(level: str, kind: str, message: str) -> dict:
    return {"level": level, "type": kind, "message": message}


# ════════════════════════════════════════════════════════════
# 决策时检测（候选股层面，当前数据即可用）
# ════════════════════════════════════════════════════════════
def check_chasing_high(name: str, discount_52w, change_pct=None) -> Optional[dict]:
    """
    追高 / FOMO 检测。
    discount_52w：距 52 周高点（负数，-3 表示距高点 3%）。
    """
    d = None
    if discount_52w is not None and not (isinstance(discount_52w, float) and pd.isna(discount_52w)):
        try:
            d = float(discount_52w)
        except (TypeError, ValueError):
            d = None
    cp = None
    if change_pct is not None and not (isinstance(change_pct, float) and pd.isna(change_pct)):
        try:
            cp = float(change_pct)
        except (TypeError, ValueError):
            cp = None

    if d is not None and d >= -3:
        return _warn("high", "追高/FOMO",
                     f"{name} 距 52 周高点仅 {abs(d):.1f}%，贴着新高买入是典型 FOMO 模式——"
                     f"问自己：是看懂了逻辑，还是怕踏空？")
    if cp is not None and cp >= 7:
        return _warn("mid", "追涨",
                     f"{name} 当日大涨 {cp:.1f}%，在情绪高点介入容易买在短期顶部，建议等回踩。")
    if d is not None and -10 <= d < -3:
        return _warn("low", "接近高点",
                     f"{name} 距 52 周高点 {abs(d):.1f}%，安全边际有限，仓位需保守。")
    return None


def check_flip_flop(ticker: str, name: str, predictions: pd.DataFrame,
                    profile: Optional[dict] = None,
                    today: Optional[date] = None) -> Optional[dict]:
    """
    反复改主意检测——基于预测日志。
    若该股近期被判过"放弃/规避"，现在又要推荐 → 警告。
    """
    if predictions is None or len(predictions) == 0:
        return None
    today = today or date.today()
    lookback = _threshold(profile, "flip_flop_lookback_days")
    cutoff = today - timedelta(days=lookback)

    mine = predictions[predictions["ticker"] == ticker]
    if mine.empty:
        return None

    recent_reject = []
    signals = set()
    for _, r in mine.iterrows():
        d = _parse_date(r.get("date"))
        sig = str(r.get("signal") or "")
        signals.add(sig)
        if d and d >= cutoff and (str(r.get("tier")) == "放弃" or sig in ("放弃", "规避")):
            recent_reject.append(d)

    if recent_reject:
        latest = max(recent_reject)
        return _warn("high", "反复改主意",
                     f"{name} 在 {latest} 曾被判「放弃/规避」，现在又要推荐——"
                     f"是出现了新的实质变化，还是只是被价格波动带着改了主意？必须说清。")
    if len(signals) >= 3:
        return _warn("mid", "立场摇摆",
                     f"{name} 在预测日志里出现过 {len(signals)} 种不同信号，立场不稳定，需复核。")
    return None


def check_repeat_recommend(ticker: str, name: str,
                           watchlist_entries: list) -> Optional[dict]:
    """该股已在观察池 → 不必重复研究，避免把同一标的算成两次机会。"""
    for e in watchlist_entries or []:
        if e.get("ticker") == ticker and e.get("state") not in ("removed", "validated"):
            return _warn("low", "已在观察池",
                         f"{name} 已在观察池（状态 {e.get('state')}）——直接复用既有研究和触发条件，"
                         f"不要当成新机会重复建仓。")
    return None


# ════════════════════════════════════════════════════════════
# 行为状态检测（交易日志层面）
# ════════════════════════════════════════════════════════════
def check_overtrading(trades: list[dict], profile: Optional[dict] = None,
                      today: Optional[date] = None) -> Optional[dict]:
    """过度交易：近 30 天交易笔数超上限。"""
    today = today or date.today()
    cap = _threshold(profile, "max_trades_per_month")
    cutoff = today - timedelta(days=30)
    recent = [t for t in trades if (_parse_date(t.get("date")) or date.min) >= cutoff]
    if len(recent) > cap:
        return _warn("high", "过度交易",
                     f"近 30 天已交易 {len(recent)} 笔（上限 {cap}）——"
                     f"过度交易是散户负 alpha 的主要来源，本轮建议只看不动。")
    return None


def check_cooling_off(trades: list[dict], profile: Optional[dict] = None) -> Optional[dict]:
    """连续亏损冷静期：最近 N 笔平仓全亏 → 进入冷静期。"""
    streak_trigger = _threshold(profile, "cooling_off_loss_streak")
    closed = [t for t in trades if t.get("status") == "closed"
              and _parse_date(t.get("exit_date"))]
    closed.sort(key=lambda t: _parse_date(t.get("exit_date")), reverse=True)
    streak = 0
    for t in closed:
        pnl = t.get("pnl_pct")
        try:
            if pnl is not None and float(pnl) < 0:
                streak += 1
            else:
                break
        except (TypeError, ValueError):
            break
    if streak >= streak_trigger:
        return _warn("high", "连续亏损·冷静期",
                     f"最近 {streak} 笔平仓连续亏损——这是报复性交易的高发区。"
                     f"建议进入冷静期：本轮不新建仓，先做复盘找出共同失误。")
    return None


def check_short_holding(trades: list[dict], profile: Optional[dict] = None) -> Optional[dict]:
    """持有期过短：已平仓交易里有持有天数低于下限的。"""
    min_days = _threshold(profile, "min_holding_days")
    short = []
    for t in trades:
        if t.get("status") != "closed":
            continue
        d0, d1 = _parse_date(t.get("date")), _parse_date(t.get("exit_date"))
        if d0 and d1 and (d1 - d0).days < min_days:
            short.append((t.get("name", t.get("ticker", "?")), (d1 - d0).days))
    if short:
        items = "、".join(f"{n}({d}天)" for n, d in short[:5])
        return _warn("mid", "持有期过短",
                     f"有 {len(short)} 笔持有期低于 {min_days} 天：{items}——"
                     f"中线策略却频繁短炒，说明计划和执行脱节。")
    return None


def check_averaging_down(ticker: str, name: str, action: str,
                         holdings: list[dict]) -> Optional[dict]:
    """亏损加仓：对一只浮亏的在手持仓执行 add。"""
    if action not in ("add", "buy"):
        return None
    for h in holdings or []:
        if h.get("ticker") == ticker and h.get("status") == "open":
            pnl = h.get("pnl_pct")
            try:
                if pnl is not None and float(pnl) < -5:
                    return _warn("high", "亏损加仓",
                                 f"{name} 是已浮亏 {float(pnl):.1f}% 的在手持仓，再加仓 = 亏损加仓。"
                                 f"只有在「原始逻辑未变 + 下跌纯属市场情绪」时才允许，且必须重新算总仓位。")
            except (TypeError, ValueError):
                pass
    return None
