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

**强制步骤（顺序不可变）：**

```bash
# 1. 宏观面板（必须先读 — 信用周期 + 市场温度计）
cd data && python scripts/snapshot_macro.py

# 2. 政策事件追踪（抓取最新政策 + 财经日历）
cd data && python scripts/policy_track.py

# 3. 大盘技术面板（已集成宏观摘要）
cd data && python scripts/snapshot_market.py
```

**严禁**只看价格涨跌就下市场判断。必须先用 `snapshot_macro.py` 输出的：
- **信用周期阶段**（高善文框架：复苏 / 过热 / 滞胀 / 衰退）
- **市场温度评级**（Howard Marks 框架：极冷 / 偏冷 / 中性 / 偏暖 / 偏热）
- **PMI / PPI / M2 / 社融 / 信贷脉冲** 的具体数值和方向
- **中美 10 年利差**（影响北上资金）

并必须读取 `policy_track.py` 产出的 `data/events/policy/_recent.md`：
- 近 7 天政府官网（国务院/发改委/央行/证监会）政策动态
- 新闻联播财经/政策报道
- 财经日历（未来重要数据公布时点）
- 用 `kb/event-stock-mapping.yaml` 作为政策→行业传导的**参考先验**（不是硬查表）

作为市场判断的**第一证据**，价格行为只是次级证据。

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
- **宏观环境**：信用周期阶段（必填）、市场温度评级（必填）、关键利差状态
- **技术面**：大盘状态 A/B/C/D、主要指数 MA60 位置
- 风险偏好
- 资金方向
- 当前主线初判（**须与宏观周期+催化剂交叉印证**）
- 需要规避的环境

**决策门槛（升级）**：
- 若**信用周期 = 衰退** → 即使技术面 A，最高只能给 B 状态，原则上不进入新仓
- 若**市场温度 = 极冷** + 技术面 C → D 状态，仅允许逆向布局
- 若**信用周期 = 过热** → 严格控制成长股仓位，关注周期/有色/能源
- 状态为 C 或 D → 输出 A 段后停止，给出"等待"建议，不进入阶段 2

## 阶段 2 · 主线/行业筛选

**强制步骤（顺序不可变）：**

```bash
# 1. 行业基本面体检（必须先跑 — 邱国鹭"低估改善"框架）
cd data && python scripts/snapshot_industry.py --top 15

# 2. 行业当日资金/涨跌（同花顺）
cd data && python scripts/screen_sectors.py --top 10
```

**严禁**只看"今日 ETF 涨跌"就判断主线。必须先用 `snapshot_industry.py` 输出的：
- **申万一级 PE/PB 估值地图**（全 31 个行业当前位置）
- **重点行业位置标签**（低估改善 / 高位过热 / 价值陷阱风险 / 中位平稳）
- **价格历史分位**（近 3 年位置，PE 分位代理）
- **动量方向**（1/3/6/12 月）

判断框架（邱国鹭）：
- ⭐ **低估改善**（价格分位<30% + 动量转正）：最优买入区，胜率最高
- ⚠️ **高位过热**（价格分位>70% + 动量仍强）：追高风险大，等待回调
- ❌ **价值陷阱风险**（价格分位<30% + 动量恶化）：估值便宜但基本面恶化，避开
- 🚧 **高位回调**（价格分位>70% + 动量转负）：趋势已转弱，禁止新仓

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

**政策事件分析（必做）**：
读取 `data/events/policy/_recent.md`（阶段 1 已抓取），结合 `kb/event-stock-mapping.yaml`：
- 过去 7-30 天有哪些**真信号级**政策？（过滤掉"强调高质量发展"类套话）
- 每条政策的传导链（政策 → 产业链环节 → 受益行业）
- 重点做**前瞻**：政策可能催化哪些**还没涨**的方向（结合 `snapshot_industry.py` 的"低估改善"列表 → 政策强 + 行业还在低位 = 预期差机会）
- 政策的**确定性和时效**（已落地 vs 仅表态；本季见效 vs 明年见效）
- **标注规则**：政策原文 = [事实]；传导链 = [推断]；"所以某行业会涨" = [假设]

> ⚠️ `event-stock-mapping.yaml` 是参考先验，不是硬查表。同样的政策在不同市场环境/行业位置下效果完全不同，必须结合当下情况二次判断，避免刻舟求剑。

输出：
- 强主线（最多 2 个）+ **主线性质标注**（政策驱动/产业驱动/资金驱动/预期博弈）
- 潜在暗线（**优先来自 `snapshot_industry.py` 的"低估改善"列表 + 政策催化但未启动的方向**）
- 已过热方向（**强制采用 `snapshot_industry.py` 的"高位过热"列表**）
- 预期差方向（低估值 + 反转催化剂 / 政策强但行业仍在低位）
- 近期重要政策事件清单（来自 `_recent.md`，标注影响行业和时效）
- 价值陷阱警示（**强制采用 `snapshot_industry.py` 的"价值陷阱风险"列表**）

**决策门槛（升级）**：
- 强主线候选行业若位置标签为"高位过热"，必须降级为"已过热方向"，不允许追入
- 候选股所属行业若为"价值陷阱风险"，需要明确的反转催化剂证据才能进入阶段 3

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
# 1. 财报体检（必须先跑 — 唐朝《手把手教你读财报》+ 巴菲特/林园 ROE 框架）
cd data && python scripts/financial_check.py <ticker>

# 2. 行情快照
cd data && python scripts/snapshot_stock.py <ticker>

# 3. 相似案例（journal/lessons + kb/cases）
cd data && python scripts/find_similar_cases.py <ticker>
```

**严禁**只看 PE/ROE 当前快照就判断公司质量。必须用 `financial_check.py` 输出的：
- **总分及结论**（健康 / 尚可 / 警惕 / 回避）
- **5 维评分**（利润质量 / 增长性 / 安全性 / 盈利能力 / 股东回报）
- **红旗清单**（重大风险，例：CFO/净利润<0.5、ROE 亏损年份、扣非占比<70%）
- **5 年财务摘要**（营收/利润/毛利率/ROE/负债率趋势）
- **CFO vs 净利润对比**（利润含金量的核心证据）
- **主营构成**（识别"主题股"vs"真实业务公司"）
- **分红记录**（连续分红 = 利润真实性间接验证）

判断框架（唐朝 + 巴菲特 + 邱国鹭）：
- ⭐ **总分 ≥ 85**：唐朝标准"健康"，可进入 A/B 档
- ✅ **总分 70-84**：尚可，红旗清单需要逐项交叉验证
- ⚠️ **总分 50-69**：警惕，最高 C 档（跟踪事件）
- ❌ **总分 < 50**：基本面差，强制"放弃"

**任何一个红旗（❌）都必须在报告中显式列出，并影响最终档位**。
特别警惕：
- CFO/净利润 < 0.5 → 利润可能虚增（寒武纪式问题）
- 扣非/净利润 < 0.7 → 主营业务盈利能力存疑
- ROE 出现亏损年份 → 周期性差或商业模式不稳
- 资产负债率 > 80% → 杠杆过高

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
