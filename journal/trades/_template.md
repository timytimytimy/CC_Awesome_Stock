---
# ── 交易基本信息 ──
ticker: 000000.SZ
name: 公司名
action: buy                  # buy 建仓 / add 加仓 / reduce 减仓 / sell 清仓
date: YYYY-MM-DD
price: 0.00                  # 成交价
shares: 0                    # 成交股数
amount: 0                    # 成交金额（元）
industry: 行业名

# ── 仓位（计划 vs 实际，差异本身是行为信号）──
planned_position_pct: 5      # 计划占总资金 %
actual_position_pct: 5       # 实际占总资金 %

# ── 计划 ──
horizon: mid                 # swing / mid / long
stop_loss: 0.00              # 止损价
take_profit: 0.00            # 止盈价/条件
source_report: YYYY-MM-DD    # 来自哪份分析报告（若有）

# ── 状态 ──
status: open                 # open 持仓中 / closed 已平仓
exit_price: ~
exit_date: ~
pnl_pct: ~                   # 盈亏 %（含手续费后）
linked_lesson: ~             # 关联的 lessons/ 文件名（若有）
---

# [公司名] · [action] · [YYYY-MM-DD]

## 买入逻辑
> 一句话：为什么买这只、为什么是现在

## 核心假设（必填，事后要验证）
- [假设] ...
- [假设] ...

## 买入证据
- **事实**：[来自数据/公告/财报]
- **推断**：[基于事实的推断]

## 反对意见（必填，不允许空）
- ...
- ...

## 退出条件
- **止盈**：当 ... 时减仓/清仓
- **止损**：跌破 XX 元，无条件止损
- **论文证伪**：若 [核心假设] 被证伪，立即离场

---

## 事后复盘（平仓后填写）

- **离场日期 / 价格**：
- **盈亏（含手续费）**：  %
- **核心假设是否兑现**：
- **做对了什么**：
- **做错了什么**：
- **当时没想到什么**：

## 是否提炼为 lesson？
- [ ] 是 → 写入 `journal/lessons/<slug>.md`，并把文件名填回上方 `linked_lesson`
- [ ] 否 → 太特殊，不可复用
