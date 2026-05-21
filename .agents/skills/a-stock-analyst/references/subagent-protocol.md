# Subagent 编排协议

## 何时使用 subagent

默认不为简单问题开 subagent。只有在以下场景使用：
- `weekly_pick`：全市场/周度主动选股，需要并行核验多个独立证据面。
- `deep_dive`：候选股已经入围，需要多视角审查。
- 用户明确要求用 subagent。

`quick_scan` 不使用 subagent，只输出市场和行业方向。

## 核心原则

1. 不按单个大 V / 作者开 agent。按流派或功能开 agent。
2. 作者和博主只是 checklist 来源，不是投票委员。
3. subagent 只交证据、评分、疑点、反对意见；最终结论只能由主 agent 汇总。
4. 不输出“某某会买/某某推荐”。只能输出“按某流派检查项，通过/不通过”。
5. watchlist 来源只能用于情绪、传播、噪音、外盘映射，不得让候选股加分。

## 推荐分工

### weekly_pick

- `market-regime agent`：大盘状态、风险偏好、资金方向、是否允许进攻。
- `industry-catalyst agent`：政策、产业、价格、订单、库存、外盘映射。
- `data-quality agent`：财务、估值、技术、流动性、降级项。
- `bear-case agent`：处罚、减持、业绩不及预期、逻辑反证、替代方案。
- `retail-execution agent`：ETF 替代、仓位、盯盘需求、心理承受力。

#### industry-catalyst agent 的政策分析专项要求

输入：`data/events/policy/_recent.md`（近 7 天政策归档）+ `kb/event-stock-mapping.yaml`（先验）+ `snapshot_industry.py` 输出（行业位置）。

必须输出政策事件分析表：

```markdown
## 政策事件分析
| 政策事件 | 来源 | 影响行业 | 利好/利空 | 强度 | 时效 | 当前行业位置 | 是否预期差 |
|---|---|---|---|---|---|---|---|
| [原文标题] | [国务院/央行/...] | [行业] | [利好/利空] | [强/中/弱] | [已落地/本季/明年] | [来自snapshot_industry] | [是/否] |
```

判断规则：
- 过滤套话：只保留"真信号级"政策（有具体行业、具体金额、具体措施）。
- 重点找前瞻机会：政策强 + 行业位置仍在"低估"区 = 预期差，优先标记。
- 政策原文标 [事实]；传导链标 [推断]；涨跌预测标 [假设]。
- `event-stock-mapping.yaml` 仅作联想参考，最终判断基于政策原文 + 当前行业位置。
- 禁止把"政策利好"直接转为"买入信号"。

### deep_dive

- `trend-growth lens`：O'Neil / 趋势成长检查项。
- `long-value lens`：巴菲特 / 芒格 / 段永平 / 林园检查项。
- `industry-trend lens`：产业趋势、政策和景气检查项。
- `contrarian-odds lens`：冯柳 / Howard Marks / 邱国鹭检查项。
- `retail-execution lens`：E大 / 银行螺丝钉 / 望京博格 / 沈潜执行检查项。
- `bear-case lens`：只找不买理由和矛盾证据。

## subagent 输出契约

每个 subagent 必须按以下格式返回：

```markdown
## 结论摘要
- 视角：
- 通过/不通过/需要验证：
- 最高置信事实：
- 最大反对证据：

## Evidence Table
| 证据 | 来源 | 时间 | 标签 | 支持/反对 | 可靠性 | 需要验证什么 |
|---|---|---|---|---|---|---|

## 打分
| 维度 | 分数 | 理由 |
|---|---:|---|

## 禁止上调项
- 哪些内容只能作为线索，不能作为事实或买入依据：
```

## 主 agent 汇总规则

- 若数据事实与博主/研报/情绪冲突，以可核验事实优先。
- 若两个以上独立视角给出红色风险，最终结论不得高于 `等待验证`。
- 若 `bear-case agent` 找到未披露重大负面，必须进入 D 段风险检查。
- 若 `retail-execution agent` 判定“困难”，仓位建议必须降级或改为 ETF/等待。
- 若没有可核验催化剂，不能输出 `可小仓试错`。
- 若候选池来自 `industry-mapping.yaml` 而非全市场扫描，必须说明“非全 A 股穷尽筛选”。
