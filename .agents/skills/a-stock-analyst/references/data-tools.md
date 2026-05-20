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

## screen_all_market.py（待实现优先入口）

**用途**: `weekly_pick` 模式的全市场第一层候选池。

```bash
python scripts/screen_all_market.py --top 30
```

若该脚本不存在或运行失败，报告必须披露：候选池来自 `screen_sectors.py` + `industry-mapping.yaml` + `screen_by_criteria.py` 的主线行业代表公司筛选，不代表全 A 股穷尽扫描。

## find_similar_cases.py

**用途**: 阶段 4，相似案例检索

```bash
python scripts/find_similar_cases.py 600519.SH
python scripts/find_similar_cases.py --theme consumer-recovery
python scripts/find_similar_cases.py --school contrarian --outcome failure
```

## 通用注意事项

- akshare 接口可能限流，若报错 `[WARN]` 且数据缺失，重试或使用 `--as-of` 历史日期
- 所有脚本 stdout 是给 skill 读的 Markdown，stderr 是日志
- 退出码 2 = 部分数据缺失（降级运行），非 0 = 完全失败
