# Backtest

量化回测目录。存放策略定义和每次回测结果。

## 约定

- 策略文件：`strategies/<slug>.py`，文件头必须声明策略元数据（见 `_template.py`）
- 每次回测结果：`runs/<strategy>-<YYYY-MM-DD>/`，**不覆盖，只新建**
- 回测结果必须包含 `metrics.json`（标准化指标）和 `report.md`（人类可读总结）

## 标准化 metrics.json 格式

```json
{
  "strategy": "canslim-a-share-mid",
  "run_date": "2026-05-20",
  "backtest_period": {"start": "2020-01-01", "end": "2025-12-31"},
  "annualized_return": 0.18,
  "max_drawdown": -0.22,
  "sharpe_ratio": 1.1,
  "win_rate": 0.52,
  "profit_factor": 2.1,
  "total_trades": 87,
  "avg_hold_days": 45,
  "benchmark": "000300.SH",
  "benchmark_return": 0.09
}
```

## 技术栈

- Python 3.11+（uv 管理）
- 推荐：`backtrader` 或 `vectorbt`（轻量）
- 数据：使用 `data/` 模块的相同接口

## 注意

回测结果目录（`runs/`）已加入 `.gitignore`，不提交大文件。
如需保存重要回测，将 `report.md` 和 `metrics.json` 复制到 `runs/archive/`。
