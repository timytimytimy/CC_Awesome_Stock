# TODO

> **终极目标**：通过蒸馏大 V 和网络高手的分析、选股思路，构建**我个人（散户）**的选股决策系统。
> 评估标准：每一项 TODO 必须回答"对一个具体散户的决策质量有什么提升"，否则降级或剔除。

---

## P0：真实数据分析层 ✅ 已完成（P0.1-P0.4 全部接入，P0.5 跳过）

**痛点**：当前系统只用了"价格 + ETF 涨跌 + 涨停数"做判断，没有真正调用宏观、行业基本面、公司深度财报、政策事件这几条数据流——这与高善文、邱国鹭、唐朝等作者实际做的事**完全不在一个维度**。
**目标**：把作者们真正"每天/每周在看的事实流"接入系统，让"五阶段分析"不再是空壳。
**完成情况**：宏观/行业/财报/政策四条数据流已全部接入并集成到五阶段；2026-05-21 完成首次完整 weekly_pick 实测。

### P0.1 宏观数据流水线 ✅ 已完成

- [x] 建 `data/stock_data/macro.py`：PMI / PPI / CPI / M2 / 社融 / 信贷脉冲 / 10年国债收益率 / 中美利差 / 美联储决议。
- [x] 建 `data/scripts/snapshot_macro.py`：输出宏观月报快照，含趋势方向和拐点。
- [x] 实现"信用周期定位"逻辑（高善文框架）：当前处于复苏/过热/滞胀/衰退哪个阶段。
- [x] 实现"市场温度计"逻辑（Howard Marks 框架）：估值分位 + 利差 + 流动性温度。
- [x] 集成到阶段 1 市场判断：`snapshot_market.py` 顶部已嵌入宏观摘要。
- [x] skill 强制约束：禁止跳过宏观分析；衰退/极冷状态禁 A 档。

### P0.2 行业基本面流水线 ✅ 已完成

- [x] 建 `data/stock_data/industry.py`：申万一级 PE/PB/股息率、同花顺行业指数 3 年 K 线、价格历史分位。
- [x] 建 `data/scripts/snapshot_industry.py`：行业体检快照（全行业估值地图 + 重点行业位置评估）。
- [x] 实现"邱国鹭框架"分类：低估改善 / 低估恶化（价值陷阱）/ 高位过热 / 高位回调 / 中位平稳。
- [x] 集成到阶段 2 主线筛选：decision-tree 强制 `snapshot_industry.py` 优先于 `screen_sectors.py`。
- [x] skill 新约束 22/23：禁止跳过行业基本面；高位过热行业禁 A/B 档。
- [ ] （后续 P0.2+）行业 CR5/CR10 演变、ROE/毛利率聚合（需更细粒度数据）。

### P0.3 公司深度财报分析 ✅ 已完成

- [x] 建 `data/stock_data/financial.py`：同花顺财务摘要 + 新浪三大表（现金流、资产负债、利润）+ 主营构成 + 分红历史。
- [x] 建 `data/scripts/financial_check.py`：5 年财报体检表。
- [x] 实现唐朝《手把手教你读财报》5 维评分框架（100 分制）：
  - A. 利润质量（30 分）：CFO/净利润、毛利率稳定性、扣非占比
  - B. 增长性（20 分）：营收/净利润增速
  - C. 财务安全（20 分）：资产负债率、流动比率
  - D. 盈利能力（20 分）：ROE 持续性、ROE 平均水平（巴菲特/林园门槛）
  - E. 股东回报（10 分）：分红连续性
- [x] 集成到阶段 4 单股深度分析：decision-tree 强制先跑 `financial_check.py`。
- [x] skill 新约束 24/25：财报体检义务 + 红旗约束（总分<50 强制放弃；CFO/净利润<0.5 提升风险扣分）。
- [x] 实测验证：茅台 76 分（CFO/净利润 0.75 黄旗）、寒武纪 74 分（CFO/净利润 -0.24 红旗，利润可能虚增）。
- [ ] （后续 P0.3+）按行业差异化阈值；杜邦分解 ROE；商誉/应收账款占比详细告警。
- [ ] （后续 P0.3+）**金融股专用体检**：当前 `financial_check.py` 对银行/券商/保险只做"框架不适用"诚实降级；需建专用评分器（银行：ROE/不良率/拨备覆盖率/资本充足率；券商：ROE/净资本/杠杆率；保险：EV/NBV/综合成本率）。

### P0.4 政策事件追踪 ✅ 已完成

- [x] 建 `data/stock_data/policy.py`：政府官网（国务院/发改委/央行/证监会）+ 新闻联播 + 财经日历抓取。
- [x] 建 `data/scripts/policy_track.py`：抓取 + 归档（按日归档 + 近 7 天滚动汇总 `_recent.md`）。
- [x] 建 `kb/event-stock-mapping.yaml`：15 条政策→行业传导先验（货币/科技战/地产/消费/新能源等）。
- [x] 集成到阶段 1/2：decision-tree 强制读取 `_recent.md`；industry-catalyst subagent 政策分析专项格式。
- [x] skill 新约束 26：政策事件义务（原文标[事实]、传导标[推断]、预测标[假设]）。
- [x] 设计原则落地：脚本只抓取归档，影响判断交给分析阶段的 LLM/subagent。
- [ ] （后续 P0.4+）业绩预告/股东户数（东财源被墙，需找替代源）；政策正文深度抓取。

### P0.5 作者实时观点追踪 ⏭️ 已决定跳过

- 跳过原因：公众号无开放接口、雪球强反爬、账号封禁风险高；性价比低。
- 替代方案：WebSearch 已能在分析时按需搜到作者最新观点，已部分覆盖此需求。
- ~~建 `track_authors.py` 定期抓取作者公开发文~~（如未来确有需要再重启）

---

## P1：个人化基础（系统的根）✅ 已完成

整个系统当前最大的缺口之一——所有输出仍然是通用的"散户视角"，没有真正反映"我自己"。
**完成情况**：四个模块的数据层 + 脚本 + skill 集成全部就位（2026-05-21）。

- [x] **`config/personal-profile.yaml`**（资金/风险/仓位规则/禁区/成本/能力时间）
  - 建 example 模板 + README + 本地默认配置。
  - 建 `data/stock_data/profile.py`（读取 + 仓位换算 + 禁区过滤 + 能力圈门槛）。
  - 建 `data/scripts/position_calc.py`：把"仓位 X%"换算成具体股数/金额/止损价/手续费。
  - skill 集成：约束 27（个人化配置义务）、28（禁区过滤）、30（仓位换算义务）。

- [x] **打通 `journal/trades/` 真闭环**
  - 建 `journal/trades/_template.md`（含计划 vs 实际仓位字段）。
  - 建 `data/scripts/journal_summary.py`：交易表现统计 + 行为偏见检测（仓位失控/亏损加仓/持有期过短）。
  - skill 启动自检读取交易日志，避免重复推荐已持仓标的。

- [x] **能力圈追踪（`config/circle-of-competence.yaml`）**
  - 行业 0-4 理解度评分；建 example + 本地配置。
  - skill 集成：约束 29（能力圈门槛——level 决定档位上限，A 档只允许 level≥3）。

- [x] **错题本（`journal/lessons/`）**
  - 建 `journal/lessons/_template.md`（标签分类 + 命中检测关键词）。
  - skill 集成：约束 31（错题命中检测——命中历史错题模式必须警告并降级）。

---

## ✅ 选股漏斗重构（2026-05-22 完成）

> 2026-05-21 weekly_pick 实跑暴露：旧 `screen_all_market.py` 的 `base_score`=成交额+当日涨幅
> 初筛闸门只看当日量价，与"提前预测、抓未启动机会"的目标矛盾——基本面好但当天没动的
> 股票在基本面评分前就被砍掉。本次 5 项全部重构完成。

- [x] **初筛去动量化**：删除 `base_score`/`score_base_row`。初筛 = 纯流动性闸门
  （成交额≥阈值 + 排除 ST/停牌/北交所），当日涨幅完全不参与过滤。
  （快照 CSV 实测只有 14 列、无 PE/PB，EM 接口又常被墙——故初筛不做估值评分，
  估值留到 enrich 阶段算；这比原计划的"PE/PB 初筛"更干净。）
- [x] **取消有损初筛**：`--enrich 0` = 闸门内全部增强评分（实测约 1200 只）。
  增强结果按日缓存（`screen_enrich_<date>.csv`），每 50 只落盘、崩溃自动续跑，
  同日再跑秒级返回；per-stock try/except，单只失败不中断。
- [x] **多镜头筛选**：composite / value / growth / reversal 四镜头，`--lens` 选择；
  缓存因子 + 切换镜头秒级重排，对接 capability-matrix 的 stock_type。
- [x] **宏观联动**：新建 `kb/taxonomy/macro-industry-mapping.yaml`（信用周期四象限 +
  PPI 方向 → 行业加减分）+ `stock_data/macro_industry.py`（行业解析 + 个股行业映射，
  雪球接口、fail-safe）。screen 输出新增"宏观"列。政策（policy）按 P0.4 原则
  仍交分析阶段 LLM，不硬编码。
- [x] **回归测试** `tests/data/test_screen_funnel.py`：11 项，覆盖"低估值+当日走平的
  股票不被初筛漏掉""多镜头排序差异""宏观加减分""反转镜头亏损股闸门"。全套 16 项通过。
- [x] decision-tree 阶段 3 已接入新接口（`--enrich 0` + 多镜头）。
- [ ] （后续）ticker→行业 当前用雪球单股接口（可缓存但慢）；如需更快可找批量源。

---

## ✅ 系统闭环：从"扫描器"到"预测系统"（2026-05-22 四项全部完成）

> 2026-05-22 复盘：系统原本是"扫描器"（回答"此刻哪些股票看起来好"），
> 不是"预测系统"。差距全在**时间维度**——没有记忆、没有反馈、领先信号不驱动任何东西。
> 本轮四项闭环全部建成：① watchlist+预测日志 ② 领先信号层 ③ 反人性护栏
> ④ 数据可靠性闸门（并修复了闸门暴露的宏观数据源冻结问题）。

### 1. Watchlist + Prediction Log ✅ 已完成（2026-05-22）

- [x] `watchlist/` 数据结构 + 状态机（watching/triggered/active_trial/downgraded/removed/validated）；
      `stock_data/tracking.py` + `scripts/watchlist.py`（list/check/add/update/remove）
- [x] `prediction_log`：每个 A/B/C/放弃 判断都留痕、append-only、可回溯验证——
      `scripts/prediction_log.py`（log/list/validate/stats）
- [x] watchlist `check`：低成本复查（现价/止损/复核日），只报"有变化的"
- [x] `stats`：按档位/镜头/宏观状态统计命中率——让知识库可证伪
- [x] skill 接入：启动自检读观察池、`track` 新模式、约束 B8（阶段5留痕义务）、
      阶段5收尾自动写入两者
- [x] 用 2026-05-21 weekly_pick 结果做种子（药明康德/中国巨石入观察池 + 4 条预测留痕）
- [x] 回归测试 `tests/data/test_tracking.py` 12 项，全套 27 项通过
- [ ] （后续）持续追踪报告 `reports/tracking/YYYY-MM-DD.md` 自动归档；收盘后自动化复查

### 2. 领先信号层 ✅ 已完成（2026-05-22）

- [x] **业绩预告抓取**：`stock_data/earnings_forecast.py`（`stock_yjyg_em` 东财源
      实测可用，TODO 原"被墙"已不成立）+ `scripts/earnings_radar.py` 业绩预告雷达。
      预增/略增/扭亏/续盈/减亏 → 利好信号；预减/略减/首亏/续亏/增亏 → 利空。
- [x] **业绩预告进选股**：`screen_all_market.py` 评分时注入领先信号因子（输出"业绩预告"列），
      四镜头通用——选股从"猎捕当前好状态"转向"猎捕正在变好的公司"。
- [x] **信贷脉冲前瞻**：`macro.classify_credit_cycle` 新增 `credit_pulse_outlook` +
      `credit_pulse_lens_hint`——脉冲回升→growth 镜头，回落→value/reversal；
      snapshot_macro 显式输出；decision-tree 阶段 3 据此选镜头。
- [x] 边际变化因子：业绩预告本身即"边际变化"信号（公司透露利润方向），已覆盖该需求。
      盈利预测调整/在手订单增速等更细粒度因子留作后续增强。
- [x] 回归测试 `tests/data/test_earnings_forecast.py` 10 项，全套 37 项通过。
- [x] decision-tree 阶段 3/4 接入业绩预告雷达；data-tools 登记。

### 3. 反人性护栏 ✅ 已完成（2026-05-22）

- [x] **护栏模块** `stock_data/behavior_guard.py`：决策时检测 追高/FOMO、反复改主意、
      已在观察池；行为状态检测 过度交易、连续亏损冷静期、持有期过短、亏损加仓。
- [x] **检查脚本** `scripts/behavior_check.py`：行为状态报告 + `--candidates` 候选陷阱扫描。
- [x] profile 新增 `behavior` 段（月度交易上限/冷静期触发/最短持有期/反复回看窗口）。
- [x] skill 接入：启动自检跑行为状态、约束 B10、decision-tree 阶段 5 候选陷阱扫描+降档规则。
- [x] 回归测试 `tests/data/test_behavior_guard.py` 18 项，全套 67 项通过。
- [x] 实测：德方纳米（此前被判放弃）命中"反复改主意"、药明康德命中"已在观察池"。

### 4. 数据可靠性闸门 ✅ 已完成（2026-05-22）

- [x] **数据新鲜度模块** `stock_data/data_freshness.py`：按数据类型（月度宏观/日度行情/
      季度财报/美联储）设最大滞后阈值，判定 新鲜/滞后/严重过期；值级失效检测（北上资金=0）。
- [x] **接入 snapshot_macro**：PMI/PPI/CPI/M2/社融/信贷脉冲/国债每个数据点带新鲜度标签；
      CPI 严重过期时显式警告"不可作为当期通胀判断依据"。
- [x] **接入 snapshot_market**：北上资金恰为 0 → 标"数据失效"，不再当成真实读数。
- [x] **数据体检脚本** `scripts/data_health.py`：飞行前一次性核对所有关键数据源。
- [x] skill 接入：约束 B9（阶段 1 前必跑体检，严重过期数据相关结论降级）；decision-tree 阶段 1。
- [x] 回归测试 `tests/data/test_data_freshness.py` 12 项，全套 49 项通过。
### 4b. 宏观数据源修复 ✅ 已完成（2026-05-22）

> 闸门暴露的真问题：多个 akshare 宏观接口冻结，返回陈旧数据。已逐一换源修复。

- [x] **CPI**：`macro_china_cpi_monthly`（金十日历源，冻结在 2025-08，且返回月率却当同比用）
      → `macro_china_cpi` 全国-同比增长。修正后 2026-04 同比 +1.2%（原误显示 +0.4%）。
- [x] **M2**：`macro_china_m2_yearly`（冻结 2025-08）→ `macro_china_money_supply`。2026-04 同比 +8.6%。
- [x] **社融/信贷脉冲**：`macro_china_shrzgm`（冻结 2025-12）→ `macro_china_new_financial_credit`
      （新增人民币贷款，当期到 2026-04）。**信贷脉冲从 +10.38（信用扩张）修正为 -15.87（信用收缩）
      ——原来是完全相反的信号**，直接影响领先信号层和市场判断。
- [x] **北上资金**：查实——沪深交易所自 2024-08 停止披露北向实时净额，数据永久不可用。
      `get_northbound_flow` 改为显式返回 discontinued 标记，不再把 0 当真实读数。
- [x] 清除陈旧缓存 pkl；data_health 实测 CPI/M2/新增信贷/信贷脉冲 全部 ✅ 新鲜。
- [ ] **美联储利率**：`macro_bank_usa_interest_rate` 冻结在 2025-07-31，暂无当期 akshare 源。
      影响小（中美利差由当期国债收益率承载），闸门已标 ❌，待后续找替代源。

> 原 P2"决策结构（thesis card 等）"后移——它是研究的组织形式，不解决"系统是否有效"。
> 原 P3 的 watchlist / prediction log / 持续追踪 已并入本节第 1 项。

---

## P2：决策结构（每只股票的研究单元）

- [ ] **`thesis card` 结构化**：候选理由 / 证据表 / 决策表 / 反对意见 / 触发条件 / 失效条件 / 跟踪事件。
- [ ] **核心假设生命周期**：每条 `[假设]` 必须绑定验证事件、日期、通过/失败标准、失败后动作。
- [ ] **组合层约束**：单股/单行业仓位、主题相关性、现金比例；不同市场状态对应不同上限。
- [ ] **机会成本对照（强制项）**：每只候选必须 vs 行业 ETF/龙头/等待 做比较。
- [ ] **`regime matrix`**：A/B/C/D 市场状态决定哪些策略可用。
- [ ] **风险检查前置到阶段 3**：硬排除项前置以节省深度分析时间。

---

## P3：候选股持续追踪 — 主体已完成（见上方"系统闭环"第 1 项）

- [x] `watchlist/` 数据结构 + 状态机（watching/triggered/active_trial/downgraded/removed/validated）。
- [x] 触发器复查：`watchlist.py check` 只汇报"有变化/需关注"的项目。
- [x] `prediction log`：每个判断留痕、可验证、按档位/镜头/宏观状态统计命中率。
- [x] `track` 运行模式：轻量复查观察池 + 命中率。
- [ ] **持续追踪报告**（`reports/tracking/YYYY-MM-DD.md` 自动归档）。
- [ ] **追踪自动化**（收盘后定时复查 + 触发推送）。

---

## P4：反人性护栏 — 核心已完成（见上方"系统闭环"第 3 项）

- [x] 认知偏见监测器：FOMO/追高、反复改主意、已在观察池（`behavior_guard.py`）。
- [x] 反过度交易约束：月度交易上限、单股最短持有期、连续亏损后冷静期。
- [x] 现实约束模拟器：`position_calc.py` 已按真实资金换算股数/金额/手续费/止损价。
- [ ] **一句话决策输出（简化模式）**：30 秒能看完的"今日决策摘要"。
- [ ] **场景化决策库**：套牢 / 踏空 / 止盈犹豫 的具体决策树。

---

## P5：数据与回测可靠性

- [x] **宏观到行业评分联动**：`kb/taxonomy/macro-industry-mapping.yaml`（信用周期四象限 +
      PPI 方向 → 行业加减分）已建并接入 `screen_all_market.py`（个股"宏观"列），
      回归测试覆盖复苏/过热/滞胀/衰退四象限。
- [x] **回归测试基础**：`tests/data/` 已有 67 项，覆盖数据层/选股漏斗/系统闭环/领先信号/
      数据闸门/反人性护栏。（仍待补：macro 各 getter 的接口级 mock 测试，防接口变化静默失真。）
- [ ] **定义第一版回测公共接口**：策略 → signals → metrics.json + report.md。
- [ ] **回测防过拟合护栏**：样本内/外区间、参数搜索次数、换手率、最大回撤、稳定性。
- [ ] **`snapshot_market.py` 与 playbook 指标对齐**：缺失指标要么补，要么显式标。

### P5.1 数据源丰富与冗余 ⭐（2026-05-22 — 调研完成，方案见 `docs/data-sources.md`）

> 本轮反复栽在数据源上。已完成免费数据源调研：**baostock 0.9.10 本项目已装、
> 实测数据当期可用**（K线/财报/货币供应），是零新增依赖的现成第二供应商。
> 完整方案见 `docs/data-sources.md`，分四层免费优先推进：

- [ ] **Layer 1 · akshare 内部择优**（零成本）：财报优先同花顺/新浪、少用东财；
      宏观换统计局源已完成。
- [ ] **Layer 2 · baostock 作第二供应商**（零新增依赖，优先做）：日K线 + 财报 +
      货币供应 建"主源 akshare → 备源 baostock"自动回退。
- [ ] **Layer 3 · FRED 修美联储利率**（一次免费注册）：`get_fed_rate` 接 FRED
      `DFF`/`FEDFUNDS` 序列，修复冻结的美联储利率。
- [ ] **provider 标注**：抽象 provider 回退层，记录实际用的哪家；`data_health.py` 每行标注。
- [ ] **数据源巡检**：定期跑 `data_health.py`，接口冻结早发现。
- ~~tushare~~：免费版积分受限且有停运先例，对"免费优先"定位性价比低，保持可选。

---

## P6：知识库补全（对照最初目标的遗留项）

> 2026-05-21 对照项目最初目标复核：知识库结构 11 项中"典型分析案例"
> 完全空白，是明确遗漏；机构作者库还有 7 位待建。

### P6.1 典型分析案例库（`kb/cases/`）✅ 已完成（2026-05-21）

- [x] 贵州茅台 600519 — 长期价值派完整周期（含塑化剂逆向案例）
- [x] 白酒板块 2013 反腐打压 — 逆向赔率布局（行业恐慌底三条件验证）
- [x] 半导体板块 — 趋势成长派 CANSLIM 完整周期（2019-2021）
- [x] 医药板块集采冲击 — 困境反转 vs 价值毁灭（仿制药/创新药/CRO分化）
- [x] 更新 `kb/cases/_index.md`：按结果/流派/可复用规律速查索引
- 决策权重 `journal/lessons > kb/cases > playbooks` 已补足 cases 层
- 后续待录入：价值陷阱失败案例、杠杆牛追高失败案例（降级为非紧急）

### P6.2 机构作者档案扩充 ✅ 已完成（2026-05-21）

- [x] 张坤（易方达）：长期价值·消费品牌·集中持股
- [x] 朱少醒（富国）：均衡成长·GARP·低换手
- [x] 但斌（东方港湾）：长期价值·伟大企业论·茅台
- [x] 董宝珍（否极泰）：深度逆向·集中重仓·安全边际
- [x] 李蓓（半夏投资）：宏观对冲·信用周期·多空多资产
- [x] Peter Lynch（麦哲伦）：GARP·十倍股·六类公司框架
- [x] 姜诚（中泰资管）：深度价值·"慢就是快"·低估值
- [x] 更新 `kb/authors/_index.md`：总计 18 人，流派覆盖新增宏观对冲派
- 扩充完成：趋势成长派（+朱少醒/Lynch）、逆向赔率派（+董宝珍）、宏观对冲派（+李蓓）全部多角度覆盖

### P6.3 散户实践者层后续补全

- [ ] 扩充 A 股财报拆解型博主、可转债/低风险套利、长期公开复盘型普通投资者。
- [ ] 每个档案补 3-5 篇代表内容 + 1 个失败/不适用场景。
- [ ] `watchlist` 来源季度复核。
- [ ] `prediction log` 验证散户实践者层是否真的改善决策质量。

---

## P7：报告产出与日志

- [ ] `scripts/weekly_analysis.sh` 保存 stderr/运行日志。
- [ ] 周报生成保留数据脚本输出摘要、搜索来源摘要、失败降级项。
- [ ] `reports/_index.md` 自动更新，可按时间/主题/股票快速回溯。

---

## 已完成（历史记录）

### 数据层基础
- [x] 修复 `get_valuation()`（改用百度数据源）。
- [x] 修复 `get_announcements()`（改用 `stock_individual_notice_report`）。
- [x] 修正 `compute_rps()` 真正实现相对基准强度。
- [x] 替换东方财富被墙接口：行业板块改同花顺、K 线改新浪。
- [x] 修复 `backtest/strategies/_template.py` 过期导入。

### 知识库
- [x] 6 流派档案、11 位机构作者档案、10 位散户实践者档案。
- [x] `kb/retail-practitioners/source-quality.md`：准入/排除/评分/复核规则。

### Skill 框架
- [x] 三种运行模式：`quick_scan` / `weekly_pick` / `deep_dive`。
- [x] 19 条强制约束（含搜索义务、矛盾披露、散户实践者限制、利益冲突披露、subagent 限制、候选池披露、无结果分支、执行信号优先）。
- [x] `scoring-rubric.md`：8 模块打分 + A/B/C 档位定义。
- [x] `subagent-protocol.md`：按流派/功能分工而非按单人开 agent。
- [x] `output-format.md`：执行信号表前置 + Evidence Table + 假设生命周期框架。
- [x] WebSearch/WebFetch 工具开放 + 搜索义务强制。

### 仓库卫生
- [x] 更新 README 反映当前 MVP 状态。
- [x] `.agents/` 与 `.claude/` 双 skill 入口同步。
- [x] `.gitignore` 补充 `reports/*.pdf`、`.DS_Store`、`data/events/policy/*.md`。
- [x] PDF 导出脚本 `scripts/report_to_pdf.py` 含中文字体支持。

### 真实数据分析层（P0，2026-05-21 完成）
- [x] P0.1 宏观数据流水线（macro.py + snapshot_macro.py，高善文/Howard Marks 框架）。
- [x] P0.2 行业基本面流水线（industry.py + snapshot_industry.py，邱国鹭框架）。
- [x] P0.3 公司财报体检（financial.py + financial_check.py，唐朝框架）。
- [x] P0.4 政策事件追踪（policy.py + policy_track.py + event-stock-mapping.yaml）。
- [x] skill 强制约束从 19 条扩到 26 条（宏观/行业/财报/政策义务全部上锁）。

### 实测与修复（2026-05-21）
- [x] 跑通首次完整 `weekly_pick` 五阶段实测 → `reports/2026-05-21.md`。
      结果：A/B 档 0 只，诚实输出"本轮无候选通过 A/B 档过滤"（市场过热环境下的正确防御性输出）。
- [x] 修复 `screen_all_market.py` 评分缺陷：当日涨幅改钟形评分（涨停不再霸榜），
      新增"距 52 周高点"惩罚 + 估值分位惩罚加重，弱化纯动量/趋势单因子。
- [x] `screen_all_market.py` 输出新增"距 52 周高点"列，个股层面过热度直接可见。

### 知识库扩充与路由重构（2026-05-21）
- [x] P6.1 典型案例库 4 个（茅台/白酒反腐/半导体/医药集采），从空白到完整。
- [x] P6.2 作者档案扩充至 18 位（新增张坤/朱少醒/但斌/董宝珍/李蓓/Lynch/姜诚）。
- [x] 加入里海实践者档案 + 单股研究清单 playbook（六问/20问/硬否决/五类机会）。
- [x] **能力路由表 `kb/taxonomy/capability-matrix.yaml`**：按"分析环节+市场状态+股票类型"
      路由视角，取代无脑全员交叉验证；含强制对手（结构化反对）和置信度加权。
- [x] **约束体系重构**：32 条扁平强制约束 → 四层结构（A 硬门/B 流程/C 质量/D 视角调用）；
      D 层把"固定 4 流派交叉验证"改为"读路由表动态加载 3-5 视角"。
- [x] decision-tree/subagent-protocol/scoring-rubric 全部接入路由表。
