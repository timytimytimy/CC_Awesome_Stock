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
2. 调用 data/scripts/snapshot_market.py 获取大盘数据
3. 调用 data/scripts/screen_sectors.py --top 10 获取行业数据
4. 基于主线从 industry-mapping.yaml 找候选公司
5. 对每只候选股调用 data/scripts/snapshot_stock.py
6. 对每只候选股调用 data/scripts/find_similar_cases.py
7. 严格按 A/B/C/D/E 五段格式输出完整报告
8. 每个判断必须标注 [事实/推断/假设/情绪/传闻]
9. 报告开头写：# 周报 $DATE
10. 最多选出 6 只候选股进入 C 段

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
