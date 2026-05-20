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

读取 `kb/playbooks/market-regime.md` 对照判断：
- 大盘状态 A/B/C/D
- 风险偏好
- 资金方向
- 当前主线初判
- 需要规避的环境

**决策门槛**：若状态为 C 或 D → 输出 A 段后停止，给出"等待"建议，不进入阶段 2

## 阶段 2 · 主线/行业筛选

```bash
cd data && python scripts/screen_sectors.py --top 10
```

读取 `kb/playbooks/sector-rotation.md` 和 `kb/taxonomy/themes.yaml`，输出：
- 强主线（最多 2 个）
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
