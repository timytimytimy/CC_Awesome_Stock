# 五阶段决策树（详细版）

## 阶段 0 · 启动自检

```bash
# 读取所有教训
ls journal/lessons/*.md 2>/dev/null && cat journal/lessons/*.md

# 检查过期档案
grep -l "review_due" kb/authors/*.md | xargs grep "review_due:"
```

若教训文件不存在，提示："journal/lessons/ 尚为空，请在每次交易后填写 journal/_template.md"

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

读取 `kb/playbooks/entry-exit-rules.md` 给出操作框架。

检查 `kb/biases/known-biases.md`：本次推荐的主要流派在此类标的上是否有已知偏见？

## 阶段 5 · 风险检查 + 结论

走 `kb/playbooks/risk-checklist.md` 全部 7 项。

输出 D 段 + E 段。
E 段结论从 5 个枚举值之一选择：
- `强观察`：基本面确定性高，等待技术入场点
- `可小仓试错`：逻辑成立但存在不确定性，先 3-5% 仓位
- `等待验证`：逻辑合理但关键假设未验证，有催化剂再动
- `放弃`：逻辑不成立或风险太高
- `跟踪事件`：有趣但需等待某个具体事件发展
