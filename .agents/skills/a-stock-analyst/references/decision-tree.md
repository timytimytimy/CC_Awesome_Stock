# 五阶段决策树（详细版）

## 阶段 0 · 启动自检

```bash
# 读取所有教训
ls journal/lessons/*.md 2>/dev/null && cat journal/lessons/*.md

# 检查过期档案
grep -l "review_due" kb/authors/*.md | xargs grep "review_due:"

# 如需引用散户实践者，先读来源质量规则
test -f kb/retail-practitioners/source-quality.md && sed -n '1,220p' kb/retail-practitioners/source-quality.md

# 自动选择 skill 引用目录（Claude/Codex 两套目录均支持）
SKILL_REF_DIR=".claude/skills/a-stock-analyst/references"
test -d "$SKILL_REF_DIR" || SKILL_REF_DIR=".agents/skills/a-stock-analyst/references"

# 主动选股或候选排序时读取评分规则
test -f "$SKILL_REF_DIR/scoring-rubric.md" && sed -n '1,220p' "$SKILL_REF_DIR/scoring-rubric.md"

# 使用 subagent 时读取编排协议
test -f "$SKILL_REF_DIR/subagent-protocol.md" && sed -n '1,220p' "$SKILL_REF_DIR/subagent-protocol.md"
```

若教训文件不存在，提示："journal/lessons/ 尚为空，请在每次交易后填写 journal/_template.md"

确认运行模式：
- `quick_scan`：只做阶段 1→2，不输出个股候选。
- `weekly_pick`：阶段 1→5，主动产出分档候选。
- `deep_dive`：阶段 4→5，对指定股票深度分析。

若用户说“推荐股票 / 主动选股 / 全市场选股 / 本周候选”，默认 `weekly_pick`。

## 阶段 1 · 市场环境判断

```bash
cd data && python scripts/snapshot_market.py
```

读取 `kb/playbooks/market-regime.md` 对照判断后，**必须执行以下搜索**：

```
WebSearch: "{today} A股 大盘 涨跌 原因"
WebSearch: "{today} 沪深两市 行情 消息"
WebSearch: "{today} A股 政策 消息"
```

搜索目的：
- 确认今日大盘涨跌的实际催化剂（政策文件？经济数据？海外联动？）
- 识别是否有突发事件影响市场情绪
- 补全 snapshot_market.py 无法抓取的定性信息

搜索结果处理规则：
- 来自官方媒体（新华社/人民日报/证监会官网）→ 标注 `[事实]`
- 来自财经媒体（东方财富/财联社/Wind）→ 标注 `[事实]`（数据部分）或 `[推断]`（分析部分）
- 来自社交媒体/匿名来源 → 标注 `[传闻]`

输出内容：
- 大盘状态 A/B/C/D
- 风险偏好
- 资金方向
- 当前主线初判（**须与搜索到的催化剂交叉印证**）
- 需要规避的环境

**决策门槛**：若状态为 C 或 D → 输出 A 段后停止，给出"等待"建议，不进入阶段 2

## 阶段 2 · 主线/行业筛选

```bash
cd data && python scripts/screen_sectors.py --top 10
```

读取 `kb/playbooks/sector-rotation.md` 和 `kb/taxonomy/themes.yaml`。

识别出强主线后，**必须搜索该主线最新产业动态**：

```
WebSearch: "{today} [主线名称] 政策 最新"
WebSearch: "{today} [主线名称] 行业 消息"
WebSearch: "[主线名称] 产业链 动态 近期"
```

例如主线为"半导体国产替代"时，搜索：
- `"2026 半导体 国产替代 政策"`
- `"芯片 出口管制 最新进展"`
- `"国产GPU 订单 进展"`

搜索目的：判断当前主线是"政策催化型"、"产业验证型"还是"预期博弈型"，直接影响置信度和持仓周期建议。

输出：
- 强主线（最多 2 个）+ **主线性质标注**（政策驱动/产业驱动/资金驱动/预期博弈）
- 潜在暗线
- 已过热方向（来自 sector-rotation playbook 的过热标记）
- 预期差方向

## 阶段 3 · 候选公司发现

```bash
cd data && python scripts/screen_by_criteria.py --industry <code> --school <slug>
```

读取 `kb/playbooks/company-to-thesis.md` 和 `kb/taxonomy/industry-mapping.yaml`，
输出候选池（≤ 8 只），每只附：龙头/次龙头/补涨/待确认 分类。

若存在 `data/scripts/screen_all_market.py`，优先运行：

```bash
cd data && python scripts/screen_all_market.py --top 30
```

若不存在该脚本，必须在报告中披露：

> 候选池来自 `screen_sectors.py` + `industry-mapping.yaml` + `screen_by_criteria.py`，是主线行业代表公司筛选，不代表全 A 股穷尽扫描。

同时读取 `kb/retail-practitioners/_index.md`，对候选池做散户可执行性初筛：
- 若个股逻辑不能明显优于行业 ETF / 宽基 ETF / 现金等待，标记为"可执行性不足"。
- 若候选股依赖高频盯盘、低流动性、复杂衍生品或重仓单一主题，降低进入阶段 4 的优先级。
- 散户实践者观点只能用于提出替代方案和执行难度，不得作为候选股入选的事实依据。

`weekly_pick` 模式可使用 subagent，但必须按 `references/subagent-protocol.md` 分工：
- market-regime
- industry-catalyst
- data-quality
- bear-case
- retail-execution

不得按“每个作者/大 V 一人一个 agent”来模拟。

## 阶段 4 · 单股深度分析

对每只候选股：

```bash
cd data && python scripts/snapshot_stock.py <ticker>
cd data && python scripts/find_similar_cases.py <ticker>
```

**每只候选股必须执行以下搜索（不可省略）**：

```
WebSearch: "[公司名称] [股票代码] 最新公告 {today}"
WebSearch: "[公司名称] 近期 消息 动态"
WebSearch: "[公司名称] 业绩 订单 合同"
```

搜索重点核查项：
- **今日大涨/大跌原因**：是否有公告、传闻、分析师报告？
- **近期重大事项**：增发/减持/回购/股权激励/重组？
- **业绩跟踪**：最新一期财报或业绩预告如何？
- **管理层动态**：高管变动、大股东增减持？
- **行业地位变化**：是否有竞争对手重大事件？

若搜索发现与价格走势相悖的负面信息（如：股价大涨当日有负面公告），**必须在反对理由中明确列出，并提升风险等级**。

若搜索结果无法获取或信息不足，明确标注"[数据缺失] 网络搜索未找到近期可靠信息，以下基于价格动量推断"，**不允许假装知情**。

执行多流派交叉验证：
1. **长期价值派视角**（读 kb/schools/05-long-value.md + kb/authors/lin-yuan.md §2/§9）
2. **产业趋势派视角**（读 kb/schools/02-industry-trend.md §2/§9）
3. **趋势成长派视角**（读 kb/schools/04-trend-growth.md + kb/authors/william-oneil.md §2）
4. **逆向赔率派视角**（读 kb/schools/06-contrarian.md + kb/authors/feng-liu.md §2）

多流派输出必须是 checklist 结果，不得写“某某会买/某某推荐”。

读取 `kb/playbooks/entry-exit-rules.md` 给出操作框架。

检查 `kb/biases/known-biases.md`：本次推荐的主要流派在此类标的上是否有已知偏见？

执行散户可执行性检查：
1. 读取 `kb/retail-practitioners/_index.md`，按工具类型选择相关档案（ETF/指数、组合实践、基金投教）。
2. 比较"买这只股票"与"买行业 ETF / 买宽基 ETF / 买龙头 / 等待"的机会成本。
3. 若引用散户实践者，必须写明其用途是执行参考，不是单股背书。
4. 若实践者存在产品、课程、社群、投顾组合等商业化关系，必须在风险段披露。

每只进入阶段 4 的股票必须生成 Evidence Table：

| 证据 | 来源 | 时间 | 标签 | 支持/反对 | 可靠性 | 需要验证什么 |
|---|---|---|---|---|---|---|

证据优先级：
1. 公告 / 财报 / 政策 / 交易所 / 官方数据
2. 行业协会 / 海关 / 产业数据 / 主流财经媒体
3. 研报的数据、假设和风险提示
4. 雪球 / X / 公众号 / 博主，仅作情绪或线索

研报评级和目标价默认低权重；watchlist 博主不得让候选股加分。

## 阶段 5 · 风险检查 + 结论

走 `kb/playbooks/risk-checklist.md` 全部项目。

按 `references/scoring-rubric.md` 计算候选排序和分档。评分只用于排序，不得跳过风险检查。

输出 D 段 + E 段。
E 段结论从 5 个枚举值之一选择：
- `强观察`：基本面确定性高，等待技术入场点
- `可小仓试错`：逻辑成立但存在不确定性，先 3-5% 仓位
- `等待验证`：逻辑合理但关键假设未验证，有催化剂再动
- `放弃`：逻辑不成立或风险太高
- `跟踪事件`：有趣但需等待某个具体事件发展

最终候选数量上限：
- A 档 `强观察`：最多 3 只
- B 档 `可小仓试错`：最多 3 只
- C 档 `跟踪事件`：最多 5 只

若没有候选股达标，输出：`本轮无候选通过过滤`。
