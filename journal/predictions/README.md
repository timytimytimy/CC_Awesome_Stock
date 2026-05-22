# journal/predictions/ — 预测日志

解决系统**最致命的缺口：从不知道自己对不对**。

每个 A/B/C 档候选 + 每个"放弃/规避"判断都在这里留痕（append-only）。
3-6 个月后用 `validate` 标定结果，再用 `stats` 看哪些档位 / 镜头 / 宏观状态下
系统判断更可靠——让 18 位作者、能力路由、四镜头第一次**可证伪**。

## 文件

- `predictions.csv` — 预测数据（**不进 git**，含个人判断记录）。由脚本自动创建。

## 命令

```bash
cd data
python scripts/prediction_log.py log --ticker 603259.SH --name 药明康德 \
    --tier B --signal 可小仓试错 --lens value --stock-type deep_value \
    --thesis "..." --trigger "..." --horizon 3-6mo --price 104.23 \
    --macro 过热 --source reports/xxx.md
python scripts/prediction_log.py list [--pending|--validated]
python scripts/prediction_log.py validate --id 3 --outcome correct --price 130 --notes "..."
python scripts/prediction_log.py stats          # 按档位/镜头/宏观状态看命中率
```

## 为什么"放弃"也要记

一个被"放弃"的股票后来大涨，是和"推荐了却下跌"同等重要的**误判**。
只记成功候选会产生幸存者偏差——预测日志必须记录**全部**判断，好坏都算。

## 字段

`id / date / ticker / name / tier / signal / lens / stock_type / thesis /
trigger / horizon / price_at_prediction / macro_state / source_report /
status / validated_date / price_at_validation / return_pct / outcome / notes`

`outcome ∈ correct / wrong / partial`（验证时填）。
