"""
策略模板

策略元数据（必填）
---
name: strategy-slug
display_name: 策略中文名
school: trend-growth            # 对应 kb/taxonomy/schools.yaml 的 slug
author: william-oneil           # 对应 kb/authors/ 的 slug（可选）
horizon: mid                    # short / swing / mid / long
universe: a-share               # a-share / hk / us
data_requirements:
  - daily_kline
  - financials_quarterly
  - industry_classification
assumptions:
  - 可以在涨停价买入次日开盘
  - 忽略冲击成本，仅计算固定手续费
  - 使用申万一级行业分类
version: 0.1.0
---
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "data"))

from stock_data.market import get_index_data
from stock_data.company import get_kline, get_financials


class StrategyTemplate:
    """
    实现你的策略。

    必须实现：
    - generate_signals(date) -> list[Signal]
    - get_universe(date) -> list[str]

    Signal 格式：
    {
        "ticker": "600519.SH",
        "action": "buy" | "sell" | "hold",
        "size_pct": 5,          # 占总仓位百分比
        "reason": "...",
        "stop_loss": 0.92,      # 相对于买入价的比例
        "take_profit": 1.25,
    }
    """

    def get_universe(self, date: str) -> list[str]:
        """返回当天可选的股票池"""
        raise NotImplementedError

    def generate_signals(self, date: str, portfolio: dict) -> list[dict]:
        """返回当天的交易信号"""
        raise NotImplementedError
