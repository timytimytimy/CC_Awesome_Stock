# A 股分析与选股决策辅助系统 — Design Spec

- **Date**: 2026-05-20
- **Owner**: liumiao
- **Status**: Draft v1（待用户复核）
- **Approach**: 骨架优先、渐进填充（Approach B）

## 1. 目标与范围

构建一个面向 A 股（兼顾港股/中概/美股可迁移方法论）的**股票分析知识库 + Claude Code skill**。
目标不是收集荐股，而是系统化蒸馏优秀分析者的**分析流程**，沉淀为可复用的知识库，并提供一个能辅助"何时买、何时持、何时卖"的结构化决策 skill。

### 1.1 投资周期定位
- 主：中线（1–6 个月）
- 兼顾：波段（1–30 天）
- 长线（>6 月）/短线日内不在 MVP 范围

### 1.2 平台
- Claude Code skill（不是 Codex / OpenAI 平台）

### 1.3 本次 spec 覆盖范围（MVP）
1. 完整的知识库目录结构与 schema
2. 3 个示范作者档案（林园 / 冯柳 / William O'Neil，覆盖三大不同流派）
3. 六大流派抽象档案
4. 4 个核心 playbook
5. 完整版 skill（5 阶段流程 + 输出格式）
6. 数据层 Python 包（akshare 为主，CLI 契约）
7. backtest / journal 骨架与模板（先建空目录 + 模板，不强制内容）

### 1.4 后续迭代（不在本 spec 内）
- 增量填充剩余作者档案（每作者一个小 PR）
- 接入 tushare 增强数据
- 量化回测策略实现
- 个人交易日记积累

## 2. 仓库目录结构

```
CC_Awesome_Stock/
├── README.md
├── docs/
│   └── superpowers/specs/                    # 本 spec 在这里
├── kb/                                       # 知识库（核心资产）
│   ├── schools/                              # 六大流派抽象档案
│   │   ├── 01-main-line-capital.md
│   │   ├── 02-industry-trend.md
│   │   ├── 03-fundamental.md
│   │   ├── 04-trend-growth.md
│   │   ├── 05-long-value.md
│   │   └── 06-contrarian.md
│   ├── authors/
│   │   ├── _template.md
│   │   ├── _index.md
│   │   ├── lin-yuan.md                       # MVP 示范
│   │   ├── feng-liu.md                       # MVP 示范
│   │   └── william-oneil.md                  # MVP 示范
│   ├── cases/
│   │   ├── _template.md
│   │   └── _index.md
│   ├── playbooks/
│   │   ├── market-regime.md
│   │   ├── sector-rotation.md
│   │   ├── company-to-thesis.md
│   │   ├── entry-exit-rules.md
│   │   └── risk-checklist.md
│   ├── taxonomy/
│   │   ├── schools.yaml
│   │   ├── themes.yaml
│   │   └── industry-mapping.yaml
│   └── biases/
│       └── known-biases.md
├── data/                                     # Python 数据层（独立 uv 项目）
│   ├── pyproject.toml
│   ├── README.md
│   ├── stock_data/
│   │   ├── market.py
│   │   ├── company.py
│   │   ├── news.py
│   │   └── technical.py
│   ├── scripts/
│   │   ├── snapshot_market.py
│   │   ├── snapshot_stock.py
│   │   ├── screen_sectors.py
│   │   ├── screen_by_criteria.py
│   │   └── find_similar_cases.py
│   └── .cache/                               # 数据缓存（gitignore）
├── backtest/
│   ├── README.md
│   ├── strategies/
│   │   └── _template.py
│   ├── runs/                                 # gitignore 大文件
│   └── lib/
├── journal/
│   ├── README.md
│   ├── _template.md
│   ├── trades/
│   ├── reviews/
│   │   ├── weekly/
│   │   └── monthly/
│   └── lessons/
├── .claude/
│   └── skills/
│       └── a-stock-analyst/
│           ├── SKILL.md
│           ├── references/
│           │   ├── decision-tree.md
│           │   ├── output-format.md
│           │   ├── data-tools.md
│           │   └── source-tagging.md
│           └── prompts/
│               └── analysis-frame.md
└── log/                                      # 已存在
```

### 2.1 设计原则
- `kb/` 是核心资产，纯 Markdown + YAML，可直接 grep
- 流派档案放共性方法论，作者档案只放该作者独有的东西
- `playbooks/` 是跨作者提炼的**可执行手册**——skill 在分析时优先读 playbooks，作者档案按需 lazy load
- `data/` 是独立 Python 包，skill 通过 Bash 调用 CLI，不在 skill 内嵌 Python
- `journal/lessons/` 权重最高，是用户自己的失败教训库

## 3. 知识库 Schema

### 3.1 作者档案 schema (`kb/authors/<slug>.md`)

```markdown
---
name: <slug>
display_name: 林园
aliases: ["林園", "Lin Yuan"]
status: active                     # active / dormant / retired / deceased
markets: [a-share, hk]             # a-share / hk / us / cn-concept
horizon: [long]                    # short / swing / mid / long（可多选）
schools_primary: [long-value]      # 取自 kb/taxonomy/schools.yaml
schools_secondary: [contrarian]
methodology_tags:
  - moat-analysis
  - dividend-yield
  - long-hold
sources:
  - {platform: weibo,   url: "...", access: public}
  - {platform: book,    title: "...", year: 2008}
  - {platform: speech,  url: "...", date: "2018-06-01"}
representative_holdings: ["600519.SH", "000858.SZ"]
confidence: medium                 # low / medium / high
last_updated: 2026-05-20
review_due: 2026-08-20
distilled_by: claude               # human / claude / mixed
sources_count: 12
---

# <display_name> · <主流派中文名>

## 1. 一句话画像
## 2. 分析流程（process pipeline，6 步：市场→行业→公司→买入→持有→卖出，每步"输入/判断/输出"）
## 3. 关键指标（quantifiable，含阈值 + 引用）
## 4. 不可量化但关键的判断（qualitative）
## 5. 成功案例（链接到 kb/cases/）
## 6. 失败案例 / 误判（必填，至少一例）
## 7. 已知偏见与局限
## 8. 与其他作者/流派的关系
## 9. 适用场景 / 不适用场景
## 10. 反对意见与质疑
## 11. 引用与原文链接
```

**skill 默认读取章节**：frontmatter + §2 + §7 + §9 + §10。其他章节按需 lazy load。

### 3.2 流派档案 schema (`kb/schools/<num>-<slug>.md`)

类似作者档案，但：
- 没有 representative_holdings、aliases、sources
- 新增 `representative_authors: [<slug>...]`
- 新增 `opposing_schools: [<slug>...]`
- §2 写"流派通用流程"，§3-4 写"流派内多数人接受的指标/判断"

### 3.3 案例档案 schema (`kb/cases/<ticker>-<event>-<YYYY-MM-DD>.md`)

```markdown
---
ticker: 600519.SH
display_name: 贵州茅台
event_date: 2003-07-01
record_date: 2026-05-20
horizon: long
outcome: success                   # success / failure / mixed
authors_involved: [lin-yuan, but-bin]
schools_involved: [long-value]
lessons: [<lesson-slug>...]
---

# 事件经过
# 各方观点
# 为什么对（如 success）/ 为什么错（如 failure）
# 可复用规律
# 反例（不适用场景）
```

### 3.4 Playbook schema (`kb/playbooks/*.md`)

每个 playbook 包含：
1. **目的**（一句话）
2. **输入**（什么数据/什么前置判断）
3. **步骤**（带决策分支）
4. **输出**（结构化结果）
5. **失败模式**（什么情况下会失灵）
6. **对应 skill 调用点**（在 5 阶段流程的哪一步）

### 3.5 Taxonomy YAML

**`kb/taxonomy/schools.yaml`**：
```yaml
schools:
  - slug: main-line-capital
    name_zh: 主线资金派
    core_belief: 市场短期由资金主线驱动，跟主线赚钱效应
    key_questions: [...]
    typical_metrics: [涨停数, 连板高度, 北上净流入, 板块成交额占比]
    opposing: [long-value]
  - slug: long-value
    name_zh: 长期价值派
    ...
```

**`kb/taxonomy/themes.yaml`**：题材标签库（AI、半导体、新能源、医药、消费、军工、低空经济…），每个题材含：所属产业链、典型受益公司池、生命周期阶段、过热信号

**`kb/taxonomy/industry-mapping.yaml`**：申万一级↔申万二级↔代表公司↔主要题材

### 3.6 Journal schema

**`journal/_template.md`** 强制字段：
- 交易日期、ticker、方向、价格、仓位
- 买入逻辑
- 买入证据（数据/新闻/作者观点）
- 反对意见（必填）
- 退出条件（止盈 / 止损 / 时间止损）
- 实际结果（事后填）
- 事后反思
- 归类到哪条 lesson

**`journal/lessons/<slug>.md`**：抽象出的可复用教训。skill 启动时**强制全部加载**。

## 4. Skill 执行决策树

### 4.1 五阶段流程

```
[阶段 0] 启动自检
  - 加载 journal/lessons/ 全部教训
  - 扫描 kb/authors/*.md 中 review_due 过期档案，提示
  - 确认本次分析周期（默认 mid）

[阶段 1] 市场环境判断
  - 调用 data/scripts/snapshot_market.py
  - 读 kb/playbooks/market-regime.md
  - 输出：A 段
  - 决策门槛：高风险撤退 → 进入"等待"模式

[阶段 2] 主线/行业筛选
  - 输入：阶段 1 主线初判 + themes.yaml + 资金流
  - 读 kb/playbooks/sector-rotation.md + 产业趋势/主线资金流派档案
  - 调 data/scripts/screen_sectors.py
  - 输出：B 段

[阶段 3] 候选公司发现
  - 用 industry-mapping.yaml 取候选池
  - 调 data/scripts/screen_by_criteria.py 多档作者指标过滤
  - 对照 kb/playbooks/company-to-thesis.md
  - 输出：候选池 ≤ 8 只

[阶段 4] 单股深度分析
  - 调 data/scripts/snapshot_stock.py
  - 多流派交叉验证：长期价值 / 产业趋势 / 趋势成长 各打一分
  - 调 data/scripts/find_similar_cases.py 检索 kb/cases/ + journal/
  - 调 kb/playbooks/entry-exit-rules.md
  - 输出：C 段（每股完整字段）

[阶段 5] 风险检查 + 结论
  - 走 kb/playbooks/risk-checklist.md 7 项
  - 作者偏见对冲（检查主力流派偏见是否被触发）
  - 输出：D 段 + E 段
```

### 4.2 强制约束（写进 SKILL.md）
1. 每个判断必须标注 `[事实]` / `[推断]` / `[假设]` / `[情绪]` / `[传闻]`
2. 每个数据点必须带时间戳 `(as of YYYY-MM-DD)`
3. 每只候选股必须给出"反对意见"，不允许空
4. 若 journal/lessons/ 命中相似情形，必须显式引用并说明"本次为何不同"
5. 若主线在 sector-rotation playbook 中已标"过热"，必须降低置信度并显式说明
6. 决策权重：journal/lessons > kb/cases > 作者方法论 > 流派抽象
7. 不允许给"立即买入"指令，最终结论只能是 5 个枚举值之一
8. 若候选股所属策略无对应 backtest/runs/ 结果支持，必须显式标注"未回测，仅方法论推断"

### 4.3 最终结论枚举
- `强观察`
- `可小仓试错`
- `等待验证`
- `放弃`
- `跟踪事件`

## 5. 数据层 (Python)

### 5.1 数据源
| 类型 | 主源 | 备源 | Token |
|---|---|---|---|
| K线/分时 | akshare | baostock | 否 |
| 财报三表 | akshare | tushare | tushare 需要 |
| 资金流（北上、龙虎榜） | akshare | 东财抓取 | 否 |
| 涨停/连板 | akshare | 同花顺 | 否 |
| 公告/研报 | akshare（巨潮镜像） | 东财 | 否 |
| 行业分类 | 申万 + 中信 | akshare 内置 | 否 |
| 估值分位 | 自算（基于 akshare PE/PB 历史） | - | 否 |

MVP **完全基于 akshare**，tushare 后续增强。

### 5.2 CLI 契约

所有脚本：
- 输入：命令行参数 + `--as-of YYYY-MM-DD`（默认今日，支持历史回放）
- 输出：stdout 是结构化 Markdown（skill 直接消化），stderr 是日志
- 缓存：默认 `data/.cache/<script>/<args-hash>-<date>.json`，`--no-cache` 可关
- 失败模式：网络失败退化为缓存 + 警告标记，不能让 skill 误以为数据 fresh
- 退出码：0 成功；2 部分数据缺失（带降级标记）；非 0 失败

### 5.3 脚本清单（MVP）
| 脚本 | 用途 | 阶段 |
|---|---|---|
| `snapshot_market.py` | 大盘+板块+北上+涨停+风格 | 1 |
| `screen_sectors.py --top 10` | 按资金/动量/估值排板块 | 2 |
| `screen_by_criteria.py --school <slug> --industry <code>` | 按流派指标筛公司 | 3 |
| `snapshot_stock.py <ticker>` | 单股 K线+财报+估值+资金+公告 | 4 |
| `find_similar_cases.py <ticker>` | 检索 kb/cases/ + journal/ | 4 |

### 5.4 工程约定
- Python 3.11+，uv 管理
- 所有外部 IO 走 `stock_data/` 模块，scripts 只做编排和格式化
- pytest 覆盖 scripts 输出格式（不测试外部数据正确性，测试契约）

## 6. Skill 设计 (`a-stock-analyst`)

### 6.1 SKILL.md frontmatter

```yaml
---
name: a-stock-analyst
description: |
  A 股股票分析与选股决策辅助 skill。基于一个蒸馏自多位优秀分析者方法论的本地知识库
  （kb/）和实时数据脚本（data/），按"市场环境→主线→候选→个股→风险→结论"五阶段
  输出结构化决策报告。中线为主，兼顾波段。当用户提到选股、A股分析、买入/卖出决策、
  题材主线判断、个股诊断、复盘、止损止盈、仓位调整时使用。不直接荐股，只输出结构
  化研究框架供用户参考。
---
```

### 6.2 触发场景
- 用户提到具体股票代码或公司名要求分析
- 用户问"现在什么主线/题材值得关注"
- 用户问"大盘怎么看"
- 用户复盘最近交易
- 用户问"X 行业里挑公司"

### 6.3 References 文件
- `references/decision-tree.md` — 5 阶段流程详细版（skill 主流程读它）
- `references/output-format.md` — A/B/C/D/E 段精确字段定义 + 示例
- `references/data-tools.md` — 数据脚本调用文档（参数、输出格式、失败处理）
- `references/source-tagging.md` — `[事实/推断/假设/情绪/传闻]` 标签规则

### 6.4 输出格式

完全采用用户原始 request 的 A/B/C/D/E 五段，新增：
- 每个判断附 `[事实|推断|假设|情绪|传闻]` 标签
- 每个数据点附 `(as of YYYY-MM-DD)`
- 每只股票末尾附 `置信度: low/mid/high` + `主要不确定性: ...`
- E 段从 5 枚举值选择

完整模板见 `references/output-format.md`。

## 7. 初始作者名单（18 人）

| # | 作者 | 市场 | 主流派 | 次流派 | 优先级 | MVP |
|---|---|---|---|---|---|---|
| 1 | 林园 | A | 长期价值 | 逆向 | P0 | ★ |
| 2 | 段永平 | A/US | 长期价值 | - | P0 | |
| 3 | 唐朝（老唐） | A | 基本面财报 | 长期价值 | P0 | |
| 4 | 冯柳（高毅） | A | 逆向赔率 | 基本面 | P0 | ★ |
| 5 | 邱国鹭（高毅） | A | 基本面财报 | 逆向 | P0 | |
| 6 | 张坤（易方达） | A | 基本面财报 | 价值成长 | P1 | |
| 7 | 朱少醒（富国） | A | 趋势成长 | 基本面 | P1 | |
| 8 | 但斌 | A | 长期价值 | - | P1 | |
| 9 | 董宝珍 | A | 逆向赔率 | 长期价值 | P1 | |
| 10 | 任泽平 | A | 产业趋势 | 宏观 | P0（带偏见警示）| |
| 11 | 高善文（安信） | A | 产业趋势 | 宏观 | P0 | |
| 12 | 李蓓（半夏） | A | 宏观对冲 | 逆向 | P1 | |
| 13 | 姜诚（中泰） | A | 基本面财报 | 长期价值 | P2 | |
| 14 | 巴菲特 | US | 长期价值 | - | P0 | |
| 15 | 芒格 | US | 长期价值 | 逆向 | P0 | |
| 16 | Peter Lynch | US | 趋势成长 | 基本面 | P1 | |
| 17 | William O'Neil | US | 趋势成长 | 主线资金 | P0 | ★ |
| 18 | Howard Marks | US | 逆向赔率 | 宏观 | P0 | |

**MVP 三个示范档案**（★）：林园 / 冯柳 / William O'Neil — 三大不同流派，最能压力测试 schema。

⚠️ 任泽平：使用其产业图谱，**不使用其市场/政策预测**。该约束写入其作者档案 §7 已知偏见 + skill 偏见对冲表。

## 8. 重要约束（写入 SKILL.md 顶部）

1. 不把任何单一作者当成权威
2. 不只总结结论，要提炼流程
3. 不输出无依据的荐股
4. 每个判断必须标依据来源或推理链
5. 短线/波段/中线/长线使用不同标准
6. 必须保留反对意见和失败场景
7. 必须考虑仓位和风控
8. 不允许把历史成功案例过拟合为未来规律
9. 所有输出仅作研究辅助，不构成投资建议
10. 决策权重顺序：journal/lessons > kb/cases > 作者方法论 > 流派抽象

## 9. 信息流总览

```
[journal/lessons]  ──┐
[kb/cases]         ──┼──>  [SKILL: 5-stage pipeline]  ──>  A/B/C/D/E 报告
[kb/playbooks]     ──┤             ↑
[kb/authors]       ──┤             │
[kb/schools]       ──┘             │
                                   │
[data/ CLI scripts] ───────────────┘
       ↑
  [akshare/tushare/baostock]
```

## 10. 验收标准（DoD）

MVP 完成时应能：
1. ✅ 目录结构与所有模板文件齐全
2. ✅ 6 个流派档案完整
3. ✅ 3 个示范作者档案（林园/冯柳/William O'Neil）完整
4. ✅ 5 个 playbook 完整
5. ✅ 3 个 taxonomy YAML 完整
6. ✅ 5 个数据 CLI 脚本可独立运行，stdout 是合格 Markdown
7. ✅ Skill 能完整跑一个端到端示例：用户问"现在 A 股值得关注什么"，输出完整 A/B/C/D/E 报告
8. ✅ Skill 能跑单股诊断：用户问"分析 600519.SH"，输出 C+D+E
9. ✅ journal / backtest 目录与模板就位（可空）
10. ✅ README.md 解释如何安装、如何使用、如何扩展

## 11. 非目标 (Non-Goals)

- ❌ 自动下单 / 经纪商对接
- ❌ 实时盯盘 / 推送
- ❌ 量化高频策略
- ❌ 自动训练模型
- ❌ 用户管理 / 多账户
- ❌ Web UI（纯命令行 + Markdown 输出）

## 12. 风险与开放问题

- **数据源稳定性**：akshare 接口可能变更或被限流。缓解：备源 baostock + 缓存机制 + 优雅降级
- **知识库陈旧**：作者观点会变。缓解：`review_due` 字段 + skill 启动自检
- **方法论冲突**：不同流派结论可能相反。缓解：skill 强制多流派打分 + 偏见对冲 + 输出反对意见
- **过拟合历史案例**：缓解：约束 #8 + cases 必须含失败案例
- **缺乏作者原文访问**（公众号/付费内容）：MVP 三个示范作者优先选公开素材丰富的，后续作者由用户混合供料
- **回测 vs 推断的边界**：MVP 不实现回测，但 skill 在荐股时声明"未回测，仅方法论推断"
