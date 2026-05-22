# 五阶段决策树（详细版）

## 阶段 0 · 启动自检

```bash
# 读取个人化配置（根输入 — 决定仓位/止损/禁区/能力圈）
cat config/personal-profile.yaml 2>/dev/null || echo "[未建个人档案，将用通用假设]"
cat config/circle-of-competence.yaml 2>/dev/null || echo "[未建能力圈档案]"

# 读取交易日志与行为偏见汇总
cd data && python scripts/journal_summary.py 2>/dev/null; cd ..

# 读取所有教训（错题本）
ls journal/lessons/*.md 2>/dev/null && cat journal/lessons/*.md

# 检查过期档案
grep -l "review_due" kb/authors/*.md | xargs grep "review_due:"

# 读取能力路由表（决定各环节加载哪些视角 — 取代无脑全员交叉验证）
cat kb/taxonomy/capability-matrix.yaml

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

## 视角路由模型（贯穿全流程）

**不再无脑全员交叉验证。** 每个环节加载哪些作者/流派视角，由 `kb/taxonomy/capability-matrix.yaml` 决定：

- **第一层 `stage_routing`**：阶段 1/2/5 按环节加载。如阶段 1 只加载高善文、Howard Marks、李蓓；唐朝/张坤等不做宏观择时的人在 `avoid` 名单，本环节不加载。
- **第二层 `stock_type_routing`**：阶段 3 给候选股定性（消费品牌/成长科技/低估价值/逆向困境/周期），阶段 4 按类型加载对应 primary/secondary 作者。
- **第三层 `regime_weighting`**：按阶段 1 得出的市场状态（复苏/过热/滞胀/衰退/恐慌底）对视角调权。
- **强制对手（bear_case）**：每只候选股必须加载路由表为其类型指定的"强制对手"，作为最大反对理由来源。
- **置信度加权**：作者权重 = 路由命中 × confidence 系数（high 1.0 / medium 0.7 / low 0.4）。

加载视角时只读对应作者档案的指定章节（路由表 `author_sections` 字段，通常是 §2 分析流程 / §9 适用场景），不整篇读。

## 阶段 1 · 市场环境判断

**强制步骤（顺序不可变）：**

```bash
# 0. 数据健康体检（飞行前检查 — 必须最先跑）
cd data && python scripts/data_health.py

# 1. 宏观面板（必须先读 — 信用周期 + 市场温度计）
cd data && python scripts/snapshot_macro.py

# 2. 政策事件追踪（抓取最新政策 + 财经日历）
cd data && python scripts/policy_track.py

# 3. 大盘技术面板（已集成宏观摘要）
cd data && python scripts/snapshot_market.py
```

**数据体检处理（约束 B9）**：先看 `data_health.py` 结论——
- 任何"❌ 严重过期"的数据源，其相关结论必须降级：报告里显式写"基于滞后 N 天数据"。
- 若 CPI/M2/社融/信贷脉冲等严重过期 → 报告 A 段必须声明"宏观判断置信度下调（关键数据滞后）"。
- 北上资金等"数据失效"项不得作为资金面依据。
- 不要把过期数据当成当期事实——这是 2026-05 实测踩过的坑（CPI 滞后 9 个月被当期使用）。

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

**加载视角**（按路由表 `stage_routing.macro_market`）：读取 `kb/playbooks/market-regime.md` + 高善文 §2（信用周期定位）+ Howard Marks §2（市场温度/周期位置）+ 李蓓 §2（政策预判，medium confidence）。**不加载** 唐朝/张坤/林园/但斌/欧奈尔/Lynch——他们明确不做宏观择时，路由 `avoid` 名单已排除。

对照判断后，**必须执行以下搜索**：

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

**加载视角**（按路由表 `stage_routing.industry_screen`）：读取 `kb/playbooks/sector-rotation.md` + `kb/taxonomy/themes.yaml` + 邱国鹭 §2（"低估改善"四象限是行业判断核心框架）+ 高善文 §2（宏观→行业传导）+ 任泽平 §2（产业地图，low confidence，仅作联想先验）。

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

若存在 `data/scripts/screen_all_market.py`，优先运行（**全市场扫描，weekly_pick 首选**）：

```bash
# --enrich 0 = 流动性闸门内全部增强评分（不做有损初筛，避免漏掉"未启动的好票"）
# 首次跑约 30 分钟，结果按日缓存、崩溃自动续跑；同日再跑秒级返回
cd data && python scripts/screen_all_market.py --enrich 0 --top 40 --lens composite
```

**多镜头排序（强烈建议跑多个镜头）**：增强结果缓存后，切换 `--lens` 是秒级操作。
按本轮市场状态和想找的机会类型，至少再跑 1-2 个镜头：

```bash
# 同一批缓存因子，换镜头重排——不重新增强，秒出
cd data && python scripts/screen_all_market.py --lens value     --top 30   # 深度价值
cd data && python scripts/screen_all_market.py --lens reversal  --top 30   # 困境反转
cd data && python scripts/screen_all_market.py --lens growth    --top 30   # 趋势成长
```

镜头选择对接能力路由表 + **阶段 1 的信贷脉冲前瞻**：
- 信贷脉冲回升（`credit_pulse_lens_hint=growth`）→ 优先 `growth` 镜头
- 信贷脉冲回落（`credit_pulse_lens_hint=value`）→ 优先 `value`/`reversal` 镜头
- 过热/衰退期也优先 `value`/`reversal`，复苏期优先 `growth`

不同镜头捞出的候选不同——这是为了不被单一动量综合分漏掉机会。

`screen_all_market.py` 已内置两层信号：
- **宏观联动**：阶段 1 的信用周期 + PPI → 所属行业加减分（输出"宏观"列）
- **领先信号**：业绩预告（预增/扭亏/首亏等）→ 个股加减分（输出"业绩预告"列）——
  这让选股从"猎捕当前好状态"转向"猎捕正在变好的公司"。

**业绩预告雷达（领先信号，必看）**：

```bash
cd data && python scripts/earnings_radar.py --top 30           # 最强利好预告
cd data && python scripts/earnings_radar.py --negative --top 20 # 利空预告(风险预警)
```

业绩预告是 A 股强制披露、字面意义前瞻的信号——公司在正式财报前已说出利润方向。
候选股若同时出现在利好预告榜，是强力的"提前"加分项；若在利空榜，必须列入反对理由。

若不存在该脚本，必须在报告中披露：

> 候选池来自 `screen_sectors.py` + `industry-mapping.yaml` + `screen_by_criteria.py`，是主线行业代表公司筛选，不代表全 A 股穷尽扫描。

**股票类型定性（为阶段 4 视角路由做准备 — 必做）**：
对每只入围候选股，归入 `capability-matrix.yaml` 的 `stock_type_routing` 某一类型：
- `consumer_brand` 消费品牌型 — 白酒/食品/医药消费/品牌零售，靠定价权护城河
- `growth_tech` 成长科技型 — 半导体/新能源/科技硬件软件，靠产业趋势+业绩加速
- `deep_value` 低估价值型 — 银行/公用事业/传统行业 PE/PB 历史低分位
- `contrarian_turnaround` 逆向困境反转型 — 因利空暴跌的好公司、行业恐慌底
- `cyclical` 周期型 — 有色/钢铁/化工/航运/养殖，靠供需景气周期

一只股票可命中多个类型（如"消费+低估"），取并集，阶段 4 加载视角和强制对手都取并集。
类型决定阶段 4 加载谁——必须在进入阶段 4 前完成定性。

**个人化前置过滤（在深度分析前执行，节省时间）**：
1. **禁区过滤**：候选股若命中 `config/personal-profile.yaml` 的 `exclusions`（禁区行业/类型/个股黑名单），直接剔除，不进入阶段 4，并在报告说明排除原因。
2. **能力圈门槛**：用 `config/circle-of-competence.yaml` 标注每只候选股所属行业的能力圈评分（level 0-4），决定其档位上限：
   - level≥3 → 可进 A 档
   - level=2 → 最高 B 档
   - level=1 → 进 B 档需更高置信度
   - level=0 → 最高 C 档（跟踪事件）
3. **持仓去重**：对照 `journal/trades/` 已持仓标的，避免重复推荐。
4. **错题预筛**：对照 `journal/lessons/`，命中历史错题模式的候选标记警告。

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

对每只候选股，**按以下顺序执行，不可跳步**：

### Step 4.0 · 里海硬否决前置过滤（最快 30 秒，通过才继续）

读取 `kb/playbooks/lihai-stock-research-checklist.md` 的"硬否决清单"，逐条检查：

- 利润从哪里来讲不清 → 直接放弃
- 公司跨行业太多，主逻辑不清 → 直接放弃
- 现金流长期差，利润质量无法解释 → 直接放弃
- 大存大贷无法解释（参考康美药业式排雷） → 直接放弃
- 应收/存货增速显著高于营收 → 直接放弃
- 商誉巨大且并购标的质量不明 → 直接放弃
- 实控人高质押、资金占用、关联交易严重 → 直接放弃
- 只是低PE/PB，但没有未来改善逻辑 → 直接放弃
- 涨幅已充分反映变化，赔率消失 → 直接放弃
- 逻辑需要多个假设同时成立 → 直接放弃
- 日线/周线/月线仍处明显下跌趋势，无底部证据 → 直接放弃

**命中任意一条 → 标记放弃，不进入后续深度分析**，节省时间。

### Step 4.1 · 六问研究框架（定性主线）

通过硬否决后，用**里海六问法**构建研究主线：

1. 这家公司到底靠什么赚钱？（一句话说清，否则降级）
2. 过去几年利润/现金流/股价为什么这样变化？（还原历史驱动因子）
3. 未来推动公司重新定价的核心变量是什么？
4. 这个变量是否足够大，是否已被市场充分定价？（预期差评估）
5. 如果看错，亏损边界在哪里？（证伪条件）
6. 买入、持有、卖出的证据链分别是什么？

六问回答完毕后才进入财务数据验证。

### Step 4.2 · 数据采集

```bash
# 1. 财报体检（必须先跑 — 唐朝《手把手教你读财报》+ 巴菲特/林园 ROE 框架）
cd data && python scripts/financial_check.py <ticker>

# 2. 行情快照
cd data && python scripts/snapshot_stock.py <ticker>

# 3. 相似案例（journal/lessons + kb/cases）
#    必须传 --industry（阶段 3 已定性的行业），否则板块级案例（如医药集采）匹配不到
cd data && python scripts/find_similar_cases.py <ticker> --industry <所属行业>

# 4. 业绩预告（领先信号）—— 查该股是否已透露利润方向
cd data && python scripts/earnings_radar.py --top 60 | grep <ticker或名称>   # 在利好榜?
cd data && python scripts/earnings_radar.py --negative --top 60 | grep <ticker或名称>  # 在利空榜?
```

**业绩预告是高优先级前瞻证据**：它是官方强制披露、且在正式财报之前——
若该股有"预增/扭亏"，是支持论文的强力前瞻证据（写入 Evidence Table，标 [事实]）；
若有"预减/首亏"，必须列入反对理由并提升风险扣分。无预告则说明无强制披露级变动。

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

**执行视角交叉验证（按路由表加载，不再固定全 4 流派）**：

根据该候选股在阶段 3 定性的 `stock_type`，查 `capability-matrix.yaml` 的 `stock_type_routing`，加载对应视角：

| 股票类型 | 加载的 primary 视角 | 强制对手（bear_case） |
|---|---|---|
| consumer_brand | 张坤 / 林园 / 段永平 / Lynch | Howard Marks（估值是否透支/抱团）+ 冯柳（博弈/接盘位） |
| growth_tech | 欧奈尔 / 朱少醒 | 姜诚（成长溢价该不该付）+ 唐朝（三年后还在吗） |
| deep_value | 唐朝 / 姜诚 / 巴菲特 | 欧奈尔（没趋势的死钱）+ 邱国鹭（是不是价值陷阱） |
| contrarian_turnaround | 冯柳 / 董宝珍 / Howard Marks | 唐朝（结构性损毁还是一次性冲击）+ 芒格（接下落的刀） |
| cyclical | 高善文 / 李蓓 | Howard Marks（是不是景气顶部用低 PE 买高利润） |

加载规则：
- 只读路由表 `author_sections` 指定的章节（通常 §2 分析流程 / §9 适用场景），不整篇读。
- 命中多个类型 → 视角和对手都取并集。
- 按 `regime_weighting` 用阶段 1 的市场状态调权（如恐慌底 → 逆向派权重拉满）。
- 按 `confidence` 调权：low confidence 作者（任泽平）不得作为唯一依据。

**强制对手（结构化反对）**：必须实际加载 bear_case 指定对手的视角，认真回答其 challenge 问题，结论写入候选详情的”反对理由”和执行信号表的”最大反对理由”。对手意见不是走形式——若对手提出的反对成立，必须降档。

多视角输出必须是 checklist 结果，不得写”某某会买/某某推荐”。

**里海 20 问自检（对照 `kb/playbooks/lihai-stock-research-checklist.md`）**：

在视角交叉验证完成后，对照里海 20 问清单做最终自检，重点确认：
- 问题 3：利润增长的来源拆解（价格/销量/毛利率/费用率/资产注入/周期/并购）
- 问题 11-12：核心变化是什么 + 是否已被市场定价（预期差有无）
- 问题 14：战术机会 vs 战略机会（对应短/中/长逻辑分类）
- 问题 16：证伪条件是什么（买入逻辑什么时候算错了）
- 问题 20：仓位上限是多少以及理由

同时用里海**五类机会分类**标注当前候选的机会性质：
- `战略长周期`：商业模式简单+大变化+未定价+低位结构 → 可考虑重仓
- `战术机会`：有修复催化但长期空间不清 → 设明确退出条件，到位要走
- `等待验证`：逻辑合理但关键证据缺失 → 不动仓位，记录跟踪
- `放弃`：太复杂/赔率消失/财务说不清 → 直接删除候选
- `可买入`：长周期逻辑+赔率+财务+价格+证伪位同时满足 → 执行信号表给出具体操作

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

**仓位换算（必做）**：对每只进入 A/B/C 档的候选股，运行：

```bash
cd data && python scripts/position_calc.py <ticker> --pct <建议仓位>
```

把抽象的"仓位上限 X%"换算成**具体股数 + 金额 + 止损价 + 往返手续费**。
- 若结果"不可执行"（买不起一手 / 低于 min_order_amount / 超过 max_single_stock_pct），
  必须在执行信号表显式标注，并给出替代方案（ETF / 换标的 / 等待）。
- 止损价用 `personal-profile.yaml` 的 `risk.stop_loss_*`，不得用通用默认值。

**错题命中检测（必做）**：每只候选股对照 `journal/lessons/`，命中错题模式则显式引用并降级。

**反人性护栏检查（必做，约束 B10）**：

```bash
cd data && python scripts/behavior_check.py --candidates <所有候选代码,逗号分隔>
```

处理 high 级告警（不得隐藏，必须影响结论）：
- **连续亏损·冷静期** → 本轮不出 A 档，首选"只看不动"，建议先复盘。
- **追高/FOMO**（候选 discount_52w ≥ -3，贴近 52 周高点）→ 该候选**降一档**，
  追高风险写入"反对理由"和执行信号表"最大反对理由"。
- **反复改主意**（此前判过放弃又推荐）→ 报告必须说清出现了什么**新的实质变化**；
  说不清就降档或退回"等待验证"。
- **亏损加仓** → 仅在"原始逻辑未变 + 下跌纯属市场情绪"时允许，且必须用
  `position_calc.py` 重算合并后的总仓位。
- **已在观察池** → 不要当成新机会重复建仓，复用既有研究和触发条件。

> 追高检测：skill 直接用候选的 `discount_52w`（screen/snapshot_stock 已有）判定，
> 无需脚本；脚本负责反复改主意/重复推荐/亏损加仓（需查预测日志和持仓）。

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

### 阶段 5 收尾 · 判断留痕（必做，约束 B8）

报告产出后，**每个判断都要写进闭环**——这是系统能验证自己、能改进的前提：

```bash
cd data
# 1. 每个 A/B/C 档候选 + 每个"放弃/规避"判断 → 预测日志（放弃也要记，否则幸存者偏差）
python scripts/prediction_log.py log --ticker <代码> --name <名称> --tier <A/B/C/放弃> \
    --signal <强观察/可小仓试错/等待验证/放弃/跟踪事件> --lens <镜头> --stock-type <类型> \
    --thesis "<一句话逻辑>" --trigger "<触发条件>" --horizon 3-6mo \
    --price <现价> --macro <信用周期> --source reports/<本报告>.md

# 2. 每个 A/B/C 档候选 → 观察池（放弃的不进观察池）
python scripts/watchlist.py add --ticker <代码> --name <名称> --tier <A/B/C> \
    --stock-type <类型> --thesis "..." --trigger "..." --invalidation "..." \
    --stop-loss <止损价> --price <现价> --macro <信用周期> \
    --source reports/<本报告>.md --next-review <下次复核日,通常+1周>
```

报告末尾注明："本轮 N 个判断已写入预测日志，M 只候选已加入观察池。"

## track 模式 · 观察池复查（不重新选股）

用户说"复查观察池 / 看看 watchlist / 有什么触发了吗 / 跟踪"时进入。轻量流程：

```bash
cd data
python scripts/watchlist.py check          # 复查现价/止损/复核日，只报需关注的
python scripts/prediction_log.py stats     # 累计命中率（按档位/镜头/宏观状态）
```

1. 对 `check` 列出的每个"需要关注"标的，判断其自由文本触发条件是否真的满足
   （触发条件是文本，脚本只给现价；满足与否需要你判断，必要时补 WebSearch）。
2. 触发成立 → 提示"可执行"，`watchlist.py update --ticker X --state triggered --note "..."`。
3. 证伪/失效 → `watchlist.py update --ticker X --state removed --note "..."`，
   并去预测日志 `validate` 对应记录。
4. 止损击穿 / 复核日到 → 在简报里显式提示。
5. 输出"观察池跟踪简报"：**只写有变化、需行动的**；没变化的标的一句话带过，不展开。

> track 模式是低成本高频动作（可每日/每周跑），与 weekly_pick 的重度选股分开。
> 它把"研究过的标的"持续盯住——研究成果不再每轮被扔掉、触发不再被漏。
