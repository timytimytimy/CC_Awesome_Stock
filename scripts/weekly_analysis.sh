#!/usr/bin/env bash
# 每周一自动选股分析
# 调用 Claude Code CLI 跑完整五阶段流程，输出到 reports/YYYY-MM-DD.md

set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
CLAUDE_BIN="/Users/liumiao/.local/bin/claude"
DATE=$(date +%Y-%m-%d)
WEEKDAY=$(date +%u)   # 1=周一
REPORT_FILE="$PROJECT_DIR/reports/$DATE.md"

# 激活 Python 环境（数据脚本需要）
cd "$PROJECT_DIR/data"
if [ -f ".venv/bin/activate" ]; then
    source .venv/bin/activate
fi
cd "$PROJECT_DIR"

echo "[$DATE] 开始全市场选股分析..." >&2

# 用 claude --print 跑非交互分析
# --print 模式：输出结果到 stdout 后退出，不进入交互
"$CLAUDE_BIN" \
    --print \
    --allowedTools "Bash,Read,WebSearch,WebFetch" \
    -p "使用 a-stock-analyst skill 进行今日全市场选股分析。
要求：
1. 按完整五阶段流程运行（阶段0到阶段5）
2. **【强制】阶段 1 必须先跑 data/scripts/snapshot_macro.py 拿宏观面板**
   - 必须在报告 A 段引用：信用周期阶段（高善文框架）+ 市场温度评级（Howard Marks 框架）
   - 必须列出 PMI / PPI / 信贷脉冲 / 中美10Y利差 等核心数据
3. **【强制】阶段 1 必须跑 data/scripts/policy_track.py 抓取最新政策事件**
   - 读取 data/events/policy/_recent.md，在报告 A/B 段列出近期"真信号级"政策
   - 用 kb/event-stock-mapping.yaml 做政策→行业传导分析（参考先验，非硬查表）
   - 政策原文标 [事实]，传导链标 [推断]，涨跌预测标 [假设]
4. 调用 data/scripts/snapshot_market.py 获取大盘技术面数据
5. **【强制】阶段 2 必须先跑 data/scripts/snapshot_industry.py --top 15 拿行业基本面**
   - 必须在报告 B 段标注每个候选行业的"位置标签"（低估改善/高位过热/价值陷阱风险）
   - 必须列出价格分位（近3年）+ PE-TTM + 3月动量
   - 高位过热行业必须列入"已过热方向"，不得作为主线推荐
6. 调用 data/scripts/screen_sectors.py --top 10 获取当日资金/涨跌（次级证据）
7. 基于主线 + 宏观周期阶段（如过热期偏周期，复苏期偏成长）+ 行业位置（低估改善优先）从 industry-mapping.yaml 找候选公司
8. **【强制】阶段 4 每只候选股必须先跑 data/scripts/financial_check.py 拿财报体检**
   - 必须在报告 C 段列出：总分（/100）+ 五维评分 + 红旗清单 + CFO/净利润 + 5 年财务摘要
   - 财报体检总分 < 50 → 强制"放弃"
   - 总分 50-69 → 最高 C 档（跟踪事件），禁止 A/B 档
   - CFO/净利润 < 0.5 → 必须显式标记为"利润可能虚增"重大风险
9. 对每只候选股调用 data/scripts/snapshot_stock.py
10. 对每只候选股调用 data/scripts/find_similar_cases.py
11. 严格按 A/B/C/D/E 五段格式输出完整报告
12. 每个判断必须标注 [事实/推断/假设/情绪/传闻]
13. 报告开头写：# 周报 $DATE
14. 最多选出 6 只候选股进入 C 段
15. **【强制】若宏观信用周期=衰退或市场温度=极冷，最高只能给 B 档候选，禁止 A 档**

【重要】搜索要求——以下搜索步骤不可省略：
- 阶段1完成后：用 WebSearch 搜索今日大盘涨跌的具体催化剂，例如搜索：
  "$DATE A股 大盘 涨跌原因"、"$DATE 科创板 创业板 行情 消息"
- 阶段2完成后：对识别出的强主线板块，搜索最新政策/产业事件，例如：
  "$DATE [主线名称] 政策 消息 最新"
- 阶段4对每只候选股：必须搜索该公司最新公告、近期新闻，例如：
  "[股票名称] [代码] 公告 2025"、"[股票名称] 最新消息"
- 所有搜索结果来源必须标注为 [事实] 或 [传闻]（视信源权威性决定）
- 若搜索结果与价格动量相互印证，提升置信度；若相悖，必须在报告中说明矛盾

当前工作目录：$PROJECT_DIR
" > "$REPORT_FILE" 2>/dev/null

echo "[$DATE] 分析完成 → $REPORT_FILE" >&2
echo "报告已写入: $REPORT_FILE"
