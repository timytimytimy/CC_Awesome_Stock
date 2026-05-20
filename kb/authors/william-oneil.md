---
name: william-oneil
display_name: William O'Neil
aliases: ["威廉·欧奈尔", "O'Neil"]
status: deceased
markets: [us, a-share]
horizon: [swing, mid]
schools_primary: [trend-growth]
schools_secondary: [main-line-capital]
methodology_tags:
  - CANSLIM
  - relative-strength
  - chart-pattern
  - earnings-acceleration
  - market-timing
sources:
  - {platform: book, title: "How to Make Money in Stocks", year: 1988, access: public}
  - {platform: book, title: "The Successful Investor", year: 2004, access: public}
  - {platform: website, url: "https://www.investors.com", access: public}
representative_holdings: []
confidence: high
last_updated: 2026-05-20
review_due: 2027-05-20
distilled_by: claude
sources_count: 2
---

# William O'Neil · 趋势成长派

## 1. 一句话画像
> 用 CANSLIM 系统买基本面加速、价格突破新高的成长龙头，以 7-8% 止损为代价换取 20-25%+ 的盈利机会，跟随市场节奏进出。

## 2. 分析流程（Process Pipeline）

### Step 1 · 市场环境判断（M — Market Direction，最高优先级）
- 输入：大盘指数（标普500/纳斯达克，A 股对应沪深300/创业板指）、成交量趋势、"分布日"计数
- 判断标准：
  - 确认上升趋势：指数在 50 日均线以上，上涨日成交量 > 下跌日成交量
  - 熊市确认：指数跌破 200 日均线 + 出现 5+ 个分布日（高量单日大跌）
  - 分布日定义：当日指数跌 > 0.2% 且成交量 > 前日
- 输出：做多 / 减仓 / 清仓。**熊市不做多，无论个股多好。**

### Step 2 · 行业/题材筛选
- 输入：各行业 RS Rating（相对强度评分）
- 判断：优先选 RS Rating 排名前 10% 的行业（A股可用行业相对强弱近 3 月表现）
- "3 到 4 只上涨股票中，有 1 只来自强势行业"——行业 beta 是个股 alpha 的基础
- 输出：候选行业（≤ 3 个）

### Step 3 · 公司筛选（CANSLIM 全检）
**C — Current Earnings**
- 当季 EPS 同比 ≥ 25%，且 vs 上季度加速
- 当季销售收入同比 ≥ 25%（防止利润靠降本而非增长）

**A — Annual Earnings**
- 过去 3 年 EPS 年均增速 ≥ 25%
- ROE ≥ 17%（A 股放宽至 15%）
- EPS 稳定性：没有负增长年份

**N — New**
- 新产品 / 新市场 / 新管理层 / 价格突破 52 周高点
- "没有 N 的成长股不是真正的成长股"

**S — Supply/Demand**
- 小流通盘（弹性更大）
- 突破日成交量 ≥ 50 日均量的 1.5–2 倍（量是确认，没量的突破是假突破）
- 管理层持股高、有回购计划

**L — Leader**
- 选同行业中 RS Rating 最高的公司
- 不买"同概念但涨幅落后的"补涨股

**I — Institutional Sponsorship**
- 机构数量和持仓比例季度环比增加
- 至少 3 个以上机构持仓

### Step 4 · 买入时机（形态学）
**杯柄形态（Cup with Handle）**
- 杯：从高点回调 15–30%（健康），形成圆弧底
- 柄：杯口下方 10–15% 区域窄幅震荡 1–2 周，成交量萎缩
- 买点：柄的上沿放量突破（Pivot Point）

**平底突破（Flat Base）**
- 横盘整理 5–7 周，跌幅 < 15%
- 放量突破整理高点

**A 股注意：T+1 + 涨停板制度调整**
- 涨停板次日开盘是一类"买点"（类似突破后的确认）
- 成交量用相对换手率替代绝对量

### Step 5 · 持有与减仓
- 买入后若表现正常（涨 20–25%），持有
- 若涨 20–25% 内 **3 周内完成**（急涨信号）→ 可能是最后一涨，考虑兑现部分

### Step 6 · 卖出与止损
- **止损：买入后跌 7–8%，无条件出**（这是整个系统最重要的规则）
- 获利卖出：
  - 涨 20–25% 后开始考虑减仓（除非基本面仍在加速）
  - 出现 5+ 个分布日 → 市场见顶，清仓

## 3. 关键指标

| 指标 | 阈值 | 来源 |
|---|---|---|
| 当季 EPS 增速 | ≥ 25% 且加速 | How to Make Money in Stocks |
| 当季收入增速 | ≥ 25% | 同上 |
| 3年年均 EPS 增速 | ≥ 25% | 同上 |
| ROE | ≥ 17%（A股 ≥ 15%）| 同上 |
| 突破成交量 | ≥ 50日均量 × 1.5 | 同上 |
| 行业 RS 排名 | 前 10% | IBD 标准 |
| 止损线 | -7% 至 -8% | 硬规则 |
| 获利目标 | +20% 至 +25% | 3:1 赔率 |

## 4. 不可量化但关键的判断

- **形态美观性**：杯柄形态的"弧度"是否圆润，柄是否在杯口下方（而不是杯口上方）
- **情绪判断**：突破日是否"感觉对"（成交量放大 + 价格没有立刻回调）
- **行业故事是否"新"**：N 里面的新变化，是否是市场还没充分定价的
- **避开"危险区"**：股价已经比整理区高出太多（>5%）不追

## 5. 成功案例

- **美国案例**：1960s 买施乐（Xerox）、1980s 买康帕克，早年亲历 CANSLIM 系统验证
- **方法论层面**：IBD（Investor's Business Daily）日报创立，基于 CANSLIM 的选股专栏数十年稳定输出

## 6. 失败案例 / 误判

- O'Neil 承认在自己系统中最大的失败是：**在亏损持仓上坚持希望**（不执行止损）。他说自己早期也曾因不止损损失了大量资本，CANSLIM 的 7-8% 止损规则正是从这些失败中提炼
- 熊市中多次在系统确认前就进场，被套

## 7. 已知偏见与局限

- **美股背景**：CANSLIM 开发于美股，T+1 不存在，无涨跌停制度。A 股直接使用需调整
- **高换手率**：频繁止损在 A 股手续费成本较高，需注意仓位和交易频率
- **对宏观不敏感**：系统里"M"是最重要的，但 O'Neil 对宏观驱动力（如利率、汇率）不如基本面派敏感
- **幸存者偏差**：案例多以成功案例著称，失败的追涨案例较少提及
- **不适用于 A 股小盘炒作**：CANSLIM 要求真实业绩增长，纯主题炒作的票不符合

## 8. 与其他作者/流派的关系

- 与**长期价值派（林园/巴菲特）**：对立。O'Neil 不在意护城河，只在意当下增速和趋势
- 与**逆向赔率派（冯柳）**：对立。O'Neil 买的是市场认同的龙头，冯柳买的是市场抛弃的公司
- 与**主线资金派**：有交集（都关注资金和动量），但 O'Neil 有严格基本面过滤，主线资金派没有

## 9. 适用场景 / 不适用场景

- ✅ A 股创业板/科创板成长型公司（高增速、有故事）
- ✅ 市场上升趋势中找中线波段机会
- ✅ 行业景气上行期（产业趋势派确认行业后，用 CANSLIM 选个股）
- ❌ 熊市或震荡市（O'Neil 明确说：熊市不做多）
- ❌ 低估值蓝筹、国企、价值型公司（成长率不够）
- ❌ 日内或超短线交易

## 10. 反对意见与质疑

- "止损 7-8% 在 A 股涨跌停机制下有时做不到"（涨停买，次日开盘即跌停，止损点早已过）
- "基本面数据在中国存在造假风险，C 和 A 的数据可靠性存疑"
- "CANSLIM 需要实时数据和高执行力，个人投资者难以严格执行"
- "高频交易税费侵蚀利润，7% 盈亏比在高费率下实际盈亏比要差得多"

## 11. 引用与原文链接

- O'Neil, William J. *How to Make Money in Stocks: A Winning System in Good Times and Bad*. McGraw-Hill, 1988（第四版 2009）
- O'Neil, William J. *The Successful Investor*. McGraw-Hill, 2004
- IBD 官网：https://www.investors.com（每日 IBD 50 列表、RS Rating 工具）
- 中译版《笑傲股市》，机械工业出版社
