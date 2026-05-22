"""
系统闭环：Watchlist（观察池）+ Prediction Log（预测留痕）。

把一次性研究变成持续跟踪、把每个判断变成可验证的记录——
解决"系统从不知道自己对不对""研究成果每轮被扔掉"两个最致命的缺口。

- Watchlist：A/B/C 档候选的活跟踪，带状态机。
- Prediction Log：每个判断（含"放弃"）append-only 留痕，事后验证、统计命中率。

本模块只管文件 I/O 和统计，不碰网络（便于测试）。价格复查在 scripts/watchlist.py。
"""

from __future__ import annotations

import sys
from datetime import date, datetime
from pathlib import Path
from typing import Optional

import pandas as pd
import yaml

_REPO_ROOT = Path(__file__).resolve().parents[2]
WATCHLIST_FILE = _REPO_ROOT / "watchlist" / "watchlist.yaml"
PREDICTIONS_FILE = _REPO_ROOT / "journal" / "predictions" / "predictions.csv"

# ── 观察池状态机 ────────────────────────────────────────────
WATCHLIST_STATES = (
    "watching",       # 已研究，等待触发条件
    "triggered",      # 触发条件已满足，可考虑行动
    "active_trial",   # 已小仓试错（由用户更新）
    "downgraded",     # 逻辑走弱，降级观察
    "removed",        # 证伪/失效，移出
    "validated",      # 逻辑兑现，成功了结
)
_CLOSED_STATES = ("removed", "validated")

PREDICTION_COLUMNS = [
    "id", "date", "ticker", "name", "tier", "signal", "lens", "stock_type",
    "thesis", "trigger", "horizon", "price_at_prediction", "macro_state",
    "source_report", "status", "validated_date", "price_at_validation",
    "return_pct", "outcome", "notes",
]
# 数值列之外都是文本列（读 CSV 后需强制 object，避免空列变 float64）
_NUMERIC_COLUMNS = ("id", "price_at_prediction", "price_at_validation", "return_pct")
_TEXT_COLUMNS = tuple(c for c in PREDICTION_COLUMNS if c not in _NUMERIC_COLUMNS)


# ════════════════════════════════════════════════════════════
# Watchlist
# ════════════════════════════════════════════════════════════
def load_watchlist() -> list[dict]:
    """读观察池；文件不存在返回空列表。"""
    if not WATCHLIST_FILE.exists():
        return []
    try:
        data = yaml.safe_load(WATCHLIST_FILE.read_text(encoding="utf-8")) or {}
        return data.get("entries") or []
    except Exception as e:
        print(f"[WARN] 读取 watchlist 失败: {e}", file=sys.stderr)
        return []


def save_watchlist(entries: list[dict]) -> None:
    WATCHLIST_FILE.parent.mkdir(parents=True, exist_ok=True)
    header = (
        "# 观察池 watchlist —— 把一次性研究变成持续跟踪的活标的。\n"
        "# 由 a-stock-analyst skill 阶段 5 写入；scripts/watchlist.py check 复查。\n"
        "# 状态机：watching → triggered → active_trial → downgraded/removed/validated\n\n"
    )
    body = yaml.safe_dump(
        {"entries": entries}, allow_unicode=True, sort_keys=False, width=100
    )
    WATCHLIST_FILE.write_text(header + body, encoding="utf-8")


def find_entry(entries: list[dict], ticker: str) -> Optional[dict]:
    for e in entries:
        if e.get("ticker") == ticker:
            return e
    return None


def add_to_watchlist(entry: dict) -> str:
    """
    加入观察池。同 ticker 已存在则刷新（保留 history）。
    返回 'added' / 'updated'。
    """
    entries = load_watchlist()
    today = date.today().isoformat()
    existing = find_entry(entries, entry["ticker"])

    if existing:
        history = existing.get("history") or []
        history.append({"date": today, "state": entry.get("state", existing.get("state")),
                         "note": "重新研究，刷新条目"})
        existing.update({k: v for k, v in entry.items() if k != "history"})
        existing["history"] = history
        existing["last_checked"] = today
        save_watchlist(entries)
        return "updated"

    entry.setdefault("added", today)
    entry.setdefault("state", "watching")
    entry.setdefault("last_checked", today)
    entry["history"] = [{"date": today, "state": entry["state"], "note": "入池"}]
    entries.append(entry)
    save_watchlist(entries)
    return "added"


def update_watchlist_entry(ticker: str, *, state: Optional[str] = None,
                           note: str = "", **fields) -> bool:
    """更新条目状态/字段，并写一条 history。返回是否命中。"""
    entries = load_watchlist()
    entry = find_entry(entries, ticker)
    if entry is None:
        return False
    today = date.today().isoformat()
    if state:
        if state not in WATCHLIST_STATES:
            raise ValueError(f"非法状态 {state}，合法值：{WATCHLIST_STATES}")
        entry["state"] = state
    for k, v in fields.items():
        entry[k] = v
    entry["last_checked"] = today
    hist = entry.setdefault("history", [])
    hist.append({"date": today, "state": entry.get("state"),
                 "note": note or "更新"})
    save_watchlist(entries)
    return True


def active_entries(entries: Optional[list[dict]] = None) -> list[dict]:
    """未了结（非 removed/validated）的条目。"""
    if entries is None:
        entries = load_watchlist()
    return [e for e in entries if e.get("state") not in _CLOSED_STATES]


# ════════════════════════════════════════════════════════════
# Prediction Log
# ════════════════════════════════════════════════════════════
def load_predictions() -> pd.DataFrame:
    """读预测日志；不存在返回带列的空表。"""
    if not PREDICTIONS_FILE.exists():
        return pd.DataFrame(columns=PREDICTION_COLUMNS)
    try:
        df = pd.read_csv(PREDICTIONS_FILE, dtype={"id": "Int64"})
        for col in PREDICTION_COLUMNS:
            if col not in df.columns:
                df[col] = pd.NA
        # 文本列强制 object——空列会被 pandas 推断成 float64，导致后续写字符串报错
        for col in _TEXT_COLUMNS:
            if col in df.columns:
                df[col] = df[col].astype(object)
        return df[PREDICTION_COLUMNS]
    except Exception as e:
        print(f"[WARN] 读取 predictions 失败: {e}", file=sys.stderr)
        return pd.DataFrame(columns=PREDICTION_COLUMNS)


def append_prediction(record: dict) -> int:
    """
    追加一条预测留痕（append-only）。返回分配的 id。
    record 必填：ticker, name, tier, signal；其余可选。
    """
    df = load_predictions()
    next_id = (int(df["id"].max()) + 1) if len(df) and df["id"].notna().any() else 1

    row = {c: record.get(c, "") for c in PREDICTION_COLUMNS}
    row["id"] = next_id
    row["date"] = record.get("date") or date.today().isoformat()
    row["status"] = "pending"
    row["outcome"] = ""

    df = pd.concat([df, pd.DataFrame([row])], ignore_index=True)
    PREDICTIONS_FILE.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(PREDICTIONS_FILE, index=False)
    return next_id


def validate_prediction(pred_id: int, outcome: str,
                        price_at_validation: Optional[float] = None,
                        notes: str = "") -> bool:
    """
    给一条预测标定结果。outcome ∈ correct/wrong/partial。
    若给了 price_at_validation，自动算 return_pct。
    """
    if outcome not in ("correct", "wrong", "partial"):
        raise ValueError("outcome 必须是 correct/wrong/partial")
    df = load_predictions()
    mask = df["id"] == pred_id
    if not mask.any():
        return False
    df.loc[mask, "status"] = "validated"
    df.loc[mask, "outcome"] = outcome
    df.loc[mask, "validated_date"] = date.today().isoformat()
    if price_at_validation is not None:
        df.loc[mask, "price_at_validation"] = price_at_validation
        p0 = pd.to_numeric(df.loc[mask, "price_at_prediction"], errors="coerce").iloc[0]
        if p0 and not pd.isna(p0) and p0 != 0:
            df.loc[mask, "return_pct"] = round((price_at_validation / p0 - 1) * 100, 2)
    if notes:
        df.loc[mask, "notes"] = notes
    df.to_csv(PREDICTIONS_FILE, index=False)
    return True


def prediction_stats() -> dict:
    """
    按 档位/镜头/宏观状态 统计命中率——让知识库的判断可证伪。
    只统计 status=validated 的记录。
    """
    df = load_predictions()
    done = df[df["status"] == "validated"].copy()
    result = {
        "total": len(df),
        "validated": len(done),
        "pending": int((df["status"] == "pending").sum()),
        "by_tier": {}, "by_lens": {}, "by_macro": {}, "overall": {},
    }
    if done.empty:
        return result

    def _agg(sub: pd.DataFrame) -> dict:
        n = len(sub)
        correct = int((sub["outcome"] == "correct").sum())
        partial = int((sub["outcome"] == "partial").sum())
        rets = pd.to_numeric(sub["return_pct"], errors="coerce").dropna()
        return {
            "n": n,
            "correct": correct,
            "partial": partial,
            "wrong": int((sub["outcome"] == "wrong").sum()),
            "hit_rate": round(correct / n, 3) if n else None,
            "hit_rate_incl_partial": round((correct + 0.5 * partial) / n, 3) if n else None,
            "avg_return_pct": round(float(rets.mean()), 2) if len(rets) else None,
        }

    result["overall"] = _agg(done)
    for col, key in (("tier", "by_tier"), ("lens", "by_lens"), ("macro_state", "by_macro")):
        for val, sub in done.groupby(done[col].fillna("(空)")):
            result[key][str(val)] = _agg(sub)
    return result
