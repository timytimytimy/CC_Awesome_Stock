# CC Awesome Stock — A股分析知识库 + 选股 Skill

面向 A 股的股票分析与选股决策辅助系统。

## 系统构成

```
知识库 (kb/)  +  数据层 (data/)  →  Skill (.claude/skills/a-stock-analyst/)
```

- **kb/**：蒸馏自多位优秀分析者的方法论知识库（schools/authors/playbooks/taxonomy）
- **data/**：基于 akshare 的行情/财报/资金 CLI 数据脚本
- **journal/**：你自己的交易复盘（权重最高）
- **backtest/**：量化回测
- **.claude/skills/a-stock-analyst/**：Claude Code skill，五阶段决策辅助

## 快速使用

### 1. 安装数据层

```bash
cd data
pip install uv
uv venv && source .venv/bin/activate
uv pip install -e ".[dev]"
```

### 2. 验证数据脚本

```bash
cd data
python scripts/snapshot_market.py
python scripts/snapshot_stock.py 600519.SH
python scripts/screen_sectors.py --top 5
```

### 3. 使用 Skill

在 Claude Code 中（项目目录下），直接对话：

```
"现在 A 股值得关注什么方向？"
"帮我分析 600519.SH"
"AI 板块里挑几只中线标的"
```

Skill 会自动按五阶段流程输出 A/B/C/D/E 结构化报告。

## 知识库扩展

### 添加新作者档案

```bash
cp kb/authors/_template.md kb/authors/<slug>.md
# 编辑档案，参考 william-oneil.md / lin-yuan.md / feng-liu.md
# 更新 kb/authors/_index.md
```

### 添加案例

```bash
cp kb/cases/_template.md kb/cases/<ticker>-<event>-<YYYY-MM-DD>.md
```

### 记录交易日记

```bash
cp journal/_template.md journal/trades/YYYY-MM-DD-TICKER.md
```

## MVP 内容清单

### 已完成（MVP）

- **流派档案** (6个): 主线资金/产业趋势/基本面财报/趋势成长/长期价值/逆向赔率
- **作者档案** (3个): William O'Neil / 林园 / 冯柳
- **Playbooks** (5个): 大盘判断/行业筛选/公司映射/买卖规则/风险检查
- **Taxonomy** (3个 YAML): schools/themes/industry-mapping
- **数据脚本** (5个): snapshot_market/snapshot_stock/screen_sectors/screen_by_criteria/find_similar_cases
- **Skill** (.claude/skills/a-stock-analyst)

### 待建（按优先级）

作者档案：段永平 / 唐朝 / 邱国鹭 / 高善文 / 任泽平（带偏见警示）/ 巴菲特 / 芒格 / Howard Marks

## 重要约束

1. 不把任何单一作者当权威
2. 每个判断必须标 [事实/推断/假设/情绪/传闻]
3. 不输出无依据的荐股
4. 所有输出仅作研究辅助，不构成投资建议

## 数据来源

主要：[akshare](https://akshare.akfamily.xyz/)（免费，无需 token）

可选增强：tushare（需申请 token，在 data/.env 中配置）
