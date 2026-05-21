"""
个人化配置读取 + 仓位换算。
对接 personal-profile.yaml（约束条件）+ circle-of-competence.yaml（能力圈）。

让系统的"仓位上限 5%"这类抽象建议，变成"买 XX 股、花 XX 元、止损 XX"
这类对一个具体散户真正可执行的指令。
"""

from __future__ import annotations
import sys
import math
from pathlib import Path
from typing import Optional

PROJECT_ROOT = Path(__file__).resolve().parents[2]
CONFIG_DIR = PROJECT_ROOT / "config"


# ────────────────────────────────────────────────────────────
# 配置读取
# ────────────────────────────────────────────────────────────

def load_profile() -> Optional[dict]:
    """
    读取 config/personal-profile.yaml。
    若不存在返回 None（调用方应提示用户先建档）。
    """
    import yaml
    fp = CONFIG_DIR / "personal-profile.yaml"
    if not fp.exists():
        return None
    try:
        with open(fp, encoding="utf-8") as f:
            return yaml.safe_load(f)
    except Exception as e:
        print(f"[WARN] load_profile: {e}", file=sys.stderr)
        return None


def load_circle() -> Optional[dict]:
    """读取 config/circle-of-competence.yaml。"""
    import yaml
    fp = CONFIG_DIR / "circle-of-competence.yaml"
    if not fp.exists():
        return None
    try:
        with open(fp, encoding="utf-8") as f:
            return yaml.safe_load(f)
    except Exception as e:
        print(f"[WARN] load_circle: {e}", file=sys.stderr)
        return None


def profile_exists() -> bool:
    return (CONFIG_DIR / "personal-profile.yaml").exists()


# ────────────────────────────────────────────────────────────
# 能力圈
# ────────────────────────────────────────────────────────────

def get_circle_level(industry: str, circle: Optional[dict] = None) -> int:
    """
    返回某行业的能力圈评分 0-4。
    行业名做模糊匹配（申万/同花顺命名可能不同）。
    未登记的行业返回 0（视为完全不懂）。
    """
    if circle is None:
        circle = load_circle()
    if not circle or "circle" not in circle:
        return 0
    c = circle["circle"]
    # 精确匹配
    if industry in c:
        return int(c[industry].get("level", 0))
    # 模糊匹配
    for name, info in c.items():
        if industry and (industry in name or name in industry):
            return int(info.get("level", 0))
    return 0


def circle_gate(industry: str, circle: Optional[dict] = None) -> dict:
    """
    能力圈决策门槛。返回 {level, max_tier, note}。
    max_tier：该行业候选股允许的最高档位。
    """
    level = get_circle_level(industry, circle)
    if level >= 3:
        max_tier, note = "A", "能力圈内，允许进入 A 档"
    elif level == 2:
        max_tier, note = "B", "懂基本面，最高 B 档"
    elif level == 1:
        max_tier, note = "B", "仅懂概念，进 B 档需更高置信度"
    else:
        max_tier, note = "C", "能力圈外（level 0），最高 C 档跟踪"
    return {"industry": industry, "level": level, "max_tier": max_tier, "note": note}


# ────────────────────────────────────────────────────────────
# 禁区过滤
# ────────────────────────────────────────────────────────────

def check_exclusion(ticker: str, name: str = "", industry: str = "",
                    profile: Optional[dict] = None) -> Optional[str]:
    """
    检查标的是否落在用户禁区。
    命中返回原因字符串；未命中返回 None。
    """
    if profile is None:
        profile = load_profile()
    if not profile:
        return None
    exc = profile.get("exclusions", {}) or {}

    # 个股黑名单
    if ticker in (exc.get("tickers") or []):
        return f"个股黑名单"
    # 行业禁区
    for ind in (exc.get("industries") or []):
        if ind and industry and (ind in industry or industry in ind):
            return f"禁区行业：{ind}"
    # 类型禁区
    for t in (exc.get("types") or []):
        if t == "ST" and ("ST" in name.upper() or "st" in name):
            return "禁区类型：ST"
        if t == "北交所" and ticker.endswith(".BJ"):
            return "禁区类型：北交所"
    return None


# ────────────────────────────────────────────────────────────
# 仓位换算（核心）
# ────────────────────────────────────────────────────────────

def calc_position(price: float, target_pct: float,
                  profile: Optional[dict] = None) -> dict:
    """
    把"目标仓位 X%"换算成对一个具体散户真正可执行的指令。

    输入：股价、目标仓位百分比
    输出：目标金额、可买股数（A股按手取整）、实际金额、实际仓位%、
          买入成本、卖出成本、往返手续费、可执行性检查。
    """
    if profile is None:
        profile = load_profile()
    if not profile:
        return {"error": "personal-profile.yaml 缺失，无法换算仓位"}

    cap = profile.get("capital", {})
    total = float(cap.get("total", 0))
    rules = profile.get("position_rules", {})
    costs = profile.get("costs", {})

    if total <= 0 or price <= 0:
        return {"error": "资金或股价无效"}

    target_amount = total * target_pct / 100
    lot_value = price * 100                      # A 股一手 = 100 股
    lots = math.floor(target_amount / lot_value)
    shares = lots * 100
    actual_amount = shares * price
    actual_pct = round(actual_amount / total * 100, 2)

    # 手续费
    comm_rate = float(costs.get("commission_rate", 0.00025))
    comm_min = float(costs.get("commission_min", 5))
    stamp_rate = float(costs.get("stamp_tax_rate", 0.0005))
    transfer_rate = float(costs.get("transfer_fee_rate", 0.00001))

    buy_commission = max(actual_amount * comm_rate, comm_min) if shares > 0 else 0
    buy_transfer = actual_amount * transfer_rate
    buy_cost = buy_commission + buy_transfer

    sell_commission = max(actual_amount * comm_rate, comm_min) if shares > 0 else 0
    sell_stamp = actual_amount * stamp_rate
    sell_transfer = actual_amount * transfer_rate
    sell_cost = sell_commission + sell_stamp + sell_transfer

    round_trip_cost = buy_cost + sell_cost
    round_trip_pct = round(round_trip_cost / actual_amount * 100, 3) if actual_amount > 0 else 0

    # 可执行性检查
    warnings = []
    min_order = float(rules.get("min_order_amount", 0))
    max_single = float(rules.get("max_single_stock_pct", 100))

    if shares == 0:
        warnings.append(f"❌ 资金不足买入 1 手（1 手需 {lot_value:,.0f} 元）")
    elif actual_amount < min_order:
        warnings.append(f"⚠️ 实际金额 {actual_amount:,.0f} 元 < 最小下单额 {min_order:,.0f} 元，不值得操作")
    if actual_pct > max_single:
        warnings.append(f"❌ 实际仓位 {actual_pct}% 超过单股上限 {max_single}%")

    return {
        "price": price,
        "target_pct": target_pct,
        "target_amount": round(target_amount, 0),
        "shares": shares,
        "lots": lots,
        "actual_amount": round(actual_amount, 0),
        "actual_pct": actual_pct,
        "buy_cost": round(buy_cost, 2),
        "sell_cost": round(sell_cost, 2),
        "round_trip_cost": round(round_trip_cost, 2),
        "round_trip_cost_pct": round_trip_pct,
        "executable": len([w for w in warnings if "❌" in w]) == 0 and shares > 0,
        "warnings": warnings,
    }


def get_stop_loss(horizon: str = "mid", profile: Optional[dict] = None) -> float:
    """按持有周期返回用户设定的默认止损线（%）。"""
    if profile is None:
        profile = load_profile()
    if not profile:
        return -12.0
    risk = profile.get("risk", {})
    if horizon == "swing":
        return float(risk.get("stop_loss_swing", -8))
    return float(risk.get("stop_loss_mid", -12))
