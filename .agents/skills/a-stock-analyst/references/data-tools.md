# 数据工具调用说明

所有脚本在 `data/` 目录下运行。先确认 Python 环境：

```bash
cd data && source .venv/bin/activate  # 若已设置 venv
# 或直接：cd data && python scripts/XXX.py
```

## snapshot_market.py

**用途**: 阶段 1，大盘快照

```bash
python scripts/snapshot_market.py                    # 今日
python scripts/snapshot_market.py --as-of 2026-01-15  # 历史回放
```

**输出包含**: 主要指数位置/均线、涨停数、连板高度、北上资金、行业涨跌榜、大盘状态初判

**失败处理**: 若输出含 `⚠️ 降级`，相应数据不可信，在报告中标记数据缺失

## snapshot_stock.py

**用途**: 阶段 4，单股深度

```bash
python scripts/snapshot_stock.py 600519.SH
python scripts/snapshot_stock.py 000858.SZ --as-of 2026-01-15
```

**输出包含**: 技术位置、相对强度、估值（PE/PB分位）、财务摘要（ROE/净利率/资负率）、公告、新闻

## screen_sectors.py

**用途**: 阶段 2，行业排名

```bash
python scripts/screen_sectors.py --top 10         # 近5日前10行业
python scripts/screen_sectors.py --top 5 --period 20  # 近20日前5行业
```

## screen_by_criteria.py

**用途**: 阶段 3，个股筛选

```bash
python scripts/screen_by_criteria.py --industry 801080 --school trend-growth
python scripts/screen_by_criteria.py --tickers 600519.SH,000858.SZ
python scripts/screen_by_criteria.py --industry 801150 --min-roe 15
```

**行业代码参考**（申万一级）:
- 801080: 电子
- 801140: 汽车
- 801150: 医药生物
- 801120: 食品饮料
- 801750: 计算机
- 801880: 国防军工

## screen_all_market.py（weekly_pick 全市场优先入口）

**用途**: `weekly_pick` 模式的全市场第一层候选池。初筛=纯流动性闸门（去动量化）。

```bash
python scripts/screen_all_market.py --enrich 0 --top 40 --lens composite  # 全量增强,首次约30分钟
python scripts/screen_all_market.py --lens value     --top 30   # 切镜头秒级重排(复用缓存)
python scripts/screen_all_market.py --lens reversal  --top 30
python scripts/screen_all_market.py --lens growth    --top 30
```

四镜头：composite/value/growth/reversal；宏观联动 + 业绩预告领先信号自动生效（输出"宏观""业绩预告"列）。
若该脚本运行失败，报告必须披露：候选池来自 `screen_sectors.py` + `industry-mapping.yaml` + `screen_by_criteria.py` 的主线行业代表公司筛选，不代表全 A 股穷尽扫描。

## data_health.py（数据健康体检 · 飞行前检查）

**用途**: 阶段 1 之前的飞行前检查——核对所有关键数据源的新鲜度。

```bash
python scripts/data_health.py
```

输出每个数据源的滞后天数和 ✅/⚠️/❌ 状态。"❌严重过期"的数据源相关结论必须降级，
不得当作当期事实（2026-05 实测踩过坑：CPI 滞后 9 个月被当期使用）。

## earnings_radar.py（业绩预告雷达 · 领先信号）

**用途**: 阶段 2/3，扫描当期业绩预告——A 股强制披露、字面意义前瞻的信号。

```bash
python scripts/earnings_radar.py --top 30            # 最强利好预告（预增/扭亏）
python scripts/earnings_radar.py --negative --top 20 # 利空预告（首亏/预减，风险预警）
python scripts/earnings_radar.py --period 20260630   # 指定报告期
```

## find_similar_cases.py

**用途**: 阶段 4，相似案例检索（精确命中 + 行业相关案例）

```bash
python scripts/find_similar_cases.py 600519.SH --industry 白酒   # 必传 --industry
python scripts/find_similar_cases.py --theme consumer-recovery
python scripts/find_similar_cases.py --school contrarian-odds --outcome failure
```

## watchlist.py（观察池 · 系统闭环）

**用途**: 把研究过的 A/B/C 档候选持续盯住（`track` 模式 + 阶段 5 收尾）。

```bash
python scripts/watchlist.py list      # 列出观察池
python scripts/watchlist.py check     # 低成本复查：现价/止损/复核日，只报需关注的
python scripts/watchlist.py add --ticker ... --name ... --tier B ...   # 阶段5写入
python scripts/watchlist.py update --ticker ... --state triggered --note "..."
```

## prediction_log.py（预测日志 · 系统闭环）

**用途**: 每个判断（含放弃）留痕，事后验证，统计命中率——让知识库可证伪。

```bash
python scripts/prediction_log.py log --ticker ... --tier B --signal 可小仓试错 ...  # 阶段5写入
python scripts/prediction_log.py list [--pending|--validated]
python scripts/prediction_log.py validate --id 3 --outcome correct --price 130
python scripts/prediction_log.py stats     # 按档位/镜头/宏观状态看命中率
```

## 通用注意事项

- akshare 接口可能限流，若报错 `[WARN]` 且数据缺失，重试或使用 `--as-of` 历史日期
- 所有脚本 stdout 是给 skill 读的 Markdown，stderr 是日志
- 退出码 2 = 部分数据缺失（降级运行），非 0 = 完全失败
