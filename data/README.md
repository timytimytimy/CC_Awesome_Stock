# 数据层

基于 akshare 的 A 股数据获取层，供 `a-stock-analyst` skill 调用。

## 安装

```bash
cd data
pip install uv  # 若未安装
uv venv && source .venv/bin/activate
uv pip install -e ".[dev]"
```

## CLI 脚本

所有脚本统一约定：
- stdout：结构化 Markdown（skill 直接消化）
- stderr：日志
- `--as-of YYYY-MM-DD`：指定日期（默认今日，支持历史回放）
- `--no-cache`：跳过缓存
- 退出码：0=成功；2=部分数据缺失（有降级标记）；非0=失败

### snapshot_market.py — 大盘快照

```bash
python scripts/snapshot_market.py
python scripts/snapshot_market.py --as-of 2026-01-15
```

输出：大盘状态、行业涨跌榜、资金流向、涨停数、连板高度。

### snapshot_stock.py — 单股快照

```bash
python scripts/snapshot_stock.py 600519.SH
python scripts/snapshot_stock.py 600519.SH --as-of 2026-01-15
```

输出：K线位置、最新财报摘要、估值分位、资金流、最新公告。

### screen_sectors.py — 行业筛选

```bash
python scripts/screen_sectors.py --top 10
python scripts/screen_sectors.py --top 5 --period 20
```

输出：行业按近N日涨跌幅排名，含成交额变化和估值分位。

### screen_by_criteria.py — 个股筛选

```bash
python scripts/screen_by_criteria.py --industry 801080 --school trend-growth
python scripts/screen_by_criteria.py --industry 801150 --min-roe 15
```

输出：满足条件的候选公司列表。

### find_similar_cases.py — 相似案例检索

```bash
python scripts/find_similar_cases.py 600519.SH
python scripts/find_similar_cases.py --theme consumer-recovery --outcome failure
```

输出：kb/cases/ 和 journal/ 中的相似历史案例。

## Token 配置（可选）

tushare token（akshare 不需要）：
```bash
export TUSHARE_TOKEN=your_token_here
```

或写入 `.env`（已 gitignore）：
```
TUSHARE_TOKEN=your_token_here
```
