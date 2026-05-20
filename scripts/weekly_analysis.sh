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
    --allowedTools "Bash,Read" \
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

当前工作目录：$PROJECT_DIR
" > "$REPORT_FILE" 2>/dev/null

echo "[$DATE] 分析完成 → $REPORT_FILE" >&2
echo "报告已写入: $REPORT_FILE"
