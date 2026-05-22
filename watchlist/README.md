# watchlist/ — 观察池

把一次性研究变成**持续盯盘的活标的**。skill 阶段 5 研究完一只 A/B/C 档候选，
就把它连同触发条件写进这里；之后用低成本复查盯着扳机，而不是每轮从零重新研究。

## 文件

- `watchlist.yaml` — 观察池数据（**不进 git**，含个人跟踪标的）。由脚本自动创建。

## 命令

```bash
cd data
python scripts/watchlist.py list      # 列出全部条目
python scripts/watchlist.py check     # 低成本复查：价格/止损/复核日，只报要关注的
python scripts/watchlist.py add --ticker 603259.SH --name 药明康德 --tier B \
    --stock-type deep_value --thesis "..." --trigger "..." --invalidation "..." \
    --stop-loss 91.72 --price 104.23 --macro 过热 \
    --source reports/xxx.md --next-review 2026-05-29
python scripts/watchlist.py update --ticker 603259.SH --state triggered --note "站上MA60"
python scripts/watchlist.py remove --ticker 603259.SH --note "论文证伪"
```

## 状态机

```
watching → triggered → active_trial → downgraded / removed / validated
```

- `watching` — 已研究，等待触发条件
- `triggered` — 触发条件满足，可考虑行动
- `active_trial` — 已小仓试错（用户更新）
- `downgraded` — 逻辑走弱，降级观察
- `removed` — 证伪/失效，移出
- `validated` — 逻辑兑现，成功了结

## 条目字段

`ticker / name / tier / state / stock_type / thesis / trigger / invalidation /
stop_loss / price_at_add / next_review / macro_at_add / source_report /
last_checked / history`
