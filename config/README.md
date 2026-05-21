# config/ — 个人化配置

这个目录存放**你个人**的配置，是整个选股系统的"根输入"。

## 文件说明

| 文件 | 是否进 git | 说明 |
|---|---|---|
| `personal-profile.example.yaml` | ✅ 是 | 个人档案模板（带注释）|
| `personal-profile.yaml` | ❌ 否 | 你的真实档案（含资金等隐私）|
| `circle-of-competence.example.yaml` | ✅ 是 | 能力圈模板 |
| `circle-of-competence.yaml` | ❌ 否 | 你的真实能力圈 |

`*.yaml`（非 example）已在 `.gitignore` 中排除，不会被提交。

## 首次使用

仓库已自带一份默认值的 `personal-profile.yaml` 和 `circle-of-competence.yaml`
（从 example 复制而来）。**请务必按你的真实情况修改**，否则报告里的
仓位、止损、能力圈判断都基于默认假设。

```bash
# 编辑你的真实配置
vim config/personal-profile.yaml
vim config/circle-of-competence.yaml
```

## 这两份配置如何影响报告

| 配置 | 影响 |
|---|---|
| `capital.total` | 把"仓位上限 5%"换算成具体金额和股数 |
| `position_rules` | 单股/单行业/现金比例的硬约束，违反则候选降级 |
| `exclusions` | 禁区行业/类型的候选股直接过滤 |
| `risk.stop_loss_*` | 止损线按你的风险偏好设定 |
| `costs` | 换算扣除佣金/印花税后的真实收益 |
| `circle-of-competence` | 能力圈外标的提高决策门槛；A 档只允许能力圈内 |

## 验证配置

```bash
cd data && python scripts/position_calc.py 600519.SH --pct 5
```

会读取你的 profile，输出该仓位对应的具体金额、股数、手续费。
