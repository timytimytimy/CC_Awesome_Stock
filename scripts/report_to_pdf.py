#!/usr/bin/env python3
"""
将 Markdown 格式的选股报告转换为格式化 PDF。
用法：python scripts/report_to_pdf.py [report.md] [output.pdf]
默认读取最新的 reports/*.md
"""

import sys
import os
import re
from pathlib import Path
from datetime import date

from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.lib import colors
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    HRFlowable, KeepTogether
)
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

# ── 注册中文字体 ──────────────────────────────────────────────
def _register_cjk_font():
    """尝试注册系统中文字体，降级到 Helvetica"""
    candidates = [
        ("/System/Library/Fonts/PingFang.ttc", "PingFang"),
        ("/System/Library/Fonts/STHeiti Light.ttc", "STHeiti"),
        ("/Library/Fonts/Arial Unicode MS.ttf", "ArialUnicode"),
        ("/usr/share/fonts/truetype/wqy/wqy-microhei.ttc", "WQY"),
    ]
    for path, name in candidates:
        if os.path.exists(path):
            try:
                pdfmetrics.registerFont(TTFont(name, path))
                return name
            except Exception:
                continue
    return "Helvetica"  # fallback（中文可能显示方块）

FONT = _register_cjk_font()

# ── 颜色主题 ──────────────────────────────────────────────────
C_DARK   = colors.HexColor("#1a1a2e")
C_BLUE   = colors.HexColor("#0066cc")
C_GREEN  = colors.HexColor("#00875a")
C_RED    = colors.HexColor("#de350b")
C_AMBER  = colors.HexColor("#ff8b00")
C_LIGHT  = colors.HexColor("#f4f5f7")
C_BORDER = colors.HexColor("#dfe1e6")

# ── 样式 ──────────────────────────────────────────────────────
def make_styles():
    base = getSampleStyleSheet()

    def P(name, **kw):
        return ParagraphStyle(name, fontName=FONT, **kw)

    return {
        "title":    P("title",    fontSize=22, leading=28, textColor=C_DARK,
                       spaceAfter=4, spaceBefore=0),
        "subtitle": P("subtitle", fontSize=11, leading=16, textColor=colors.grey,
                       spaceAfter=16),
        "h1":       P("h1",       fontSize=14, leading=20, textColor=C_BLUE,
                       spaceBefore=14, spaceAfter=6),
        "h2":       P("h2",       fontSize=12, leading=17, textColor=C_DARK,
                       spaceBefore=10, spaceAfter=4),
        "h3":       P("h3",       fontSize=11, leading=15, textColor=C_DARK,
                       spaceBefore=8, spaceAfter=3),
        "body":     P("body",     fontSize=9.5, leading=15, textColor=colors.HexColor("#333"),
                       spaceAfter=4),
        "bullet":   P("bullet",   fontSize=9.5, leading=14, leftIndent=12,
                       textColor=colors.HexColor("#333"), spaceAfter=2),
        "tag_fact": P("tag",      fontSize=8, textColor=C_GREEN, leading=12),
        "footer":   P("footer",   fontSize=7.5, textColor=colors.grey, leading=10,
                       alignment=1),
        "warning":  P("warning",  fontSize=9, textColor=C_AMBER, leading=13,
                       leftIndent=8, spaceAfter=4),
        "label":    P("label",    fontSize=8.5, textColor=C_BLUE, leading=12),
    }

# ── Tag 颜色映射 ──────────────────────────────────────────────
TAG_COLOR = {
    "事实": C_GREEN,
    "推断": C_BLUE,
    "假设": C_AMBER,
    "情绪": colors.HexColor("#6554C0"),
    "传闻": C_RED,
}

def colorize_tags(text: str, base_style) -> Paragraph:
    """把 [事实/推断/假设/情绪/传闻] 替换成带颜色的 span"""
    for tag, color in TAG_COLOR.items():
        hex_color = color.hexval() if hasattr(color, 'hexval') else '#666666'
        text = text.replace(
            f"[{tag}]",
            f'<font color="{hex_color}" size="8">[{tag}]</font>'
        )
    # 处理 ✅ ⚠️ ❌
    text = text.replace("✅", '<font color="#00875a">✅</font>')
    text = text.replace("⚠️", '<font color="#ff8b00">⚠️</font>')
    text = text.replace("❌", '<font color="#de350b">❌</font>')
    # 粗体 **...**
    text = re.sub(r'\*\*(.+?)\*\*', r'<b>\1</b>', text)
    return Paragraph(text, base_style)

# ── Markdown 解析 → Flowable ──────────────────────────────────
def md_to_flowables(md_text: str, styles: dict) -> list:
    flowables = []
    lines = md_text.split("\n")
    i = 0

    # 检查是否为表格行
    def is_table_line(line):
        return line.strip().startswith("|") and "|" in line[1:]

    def parse_table(lines, start):
        rows = []
        j = start
        while j < len(lines) and is_table_line(lines[j]):
            cells = [c.strip() for c in lines[j].strip().strip("|").split("|")]
            if not all(re.match(r'^[-: ]+$', c) for c in cells):
                rows.append(cells)
            j += 1
        return rows, j

    while i < len(lines):
        line = lines[i]

        # 空行
        if not line.strip():
            flowables.append(Spacer(1, 4))
            i += 1
            continue

        # 分隔线
        if line.strip() in ("---", "===", "***"):
            flowables.append(HRFlowable(width="100%", thickness=0.5,
                                         color=C_BORDER, spaceAfter=6, spaceBefore=6))
            i += 1
            continue

        # 标题
        if line.startswith("# "):
            flowables.append(Paragraph(line[2:], styles["title"]))
            i += 1
            continue
        if line.startswith("## "):
            flowables.append(HRFlowable(width="100%", thickness=1,
                                         color=C_BLUE, spaceAfter=4, spaceBefore=8))
            flowables.append(Paragraph(line[3:], styles["h1"]))
            i += 1
            continue
        if line.startswith("### "):
            flowables.append(Paragraph(line[4:], styles["h2"]))
            i += 1
            continue
        if line.startswith("#### "):
            flowables.append(Paragraph(line[5:], styles["h3"]))
            i += 1
            continue

        # 表格
        if is_table_line(line):
            rows, next_i = parse_table(lines, i)
            if rows:
                col_count = max(len(r) for r in rows)
                # 补齐
                data = [r + [""] * (col_count - len(r)) for r in rows]
                # 样式
                ts = TableStyle([
                    ("BACKGROUND",    (0, 0), (-1, 0),  C_BLUE),
                    ("TEXTCOLOR",     (0, 0), (-1, 0),  colors.white),
                    ("FONTNAME",      (0, 0), (-1, -1), FONT),
                    ("FONTSIZE",      (0, 0), (-1, -1), 8.5),
                    ("ROWBACKGROUNDS",(0, 1), (-1, -1), [colors.white, C_LIGHT]),
                    ("GRID",          (0, 0), (-1, -1), 0.3, C_BORDER),
                    ("TOPPADDING",    (0, 0), (-1, -1), 4),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                    ("LEFTPADDING",   (0, 0), (-1, -1), 6),
                    ("RIGHTPADDING",  (0, 0), (-1, -1), 6),
                    ("VALIGN",        (0, 0), (-1, -1), "MIDDLE"),
                ])
                # 把数据转成 Paragraph
                para_data = []
                for ri, row in enumerate(data):
                    para_row = []
                    for ci, cell in enumerate(row):
                        s = styles["label"] if ri == 0 else styles["body"]
                        cell = re.sub(r'\*\*(.+?)\*\*', r'<b>\1</b>', cell)
                        cell = cell.replace("✅", "✓").replace("⚠️", "⚠").replace("❌", "✗")
                        para_row.append(Paragraph(cell, s))
                    para_data.append(para_row)

                col_width = (A4[0] - 4*cm) / col_count
                t = Table(para_data, colWidths=[col_width] * col_count,
                          repeatRows=1, hAlign="LEFT")
                t.setStyle(ts)
                flowables.append(Spacer(1, 4))
                flowables.append(t)
                flowables.append(Spacer(1, 6))
            i = next_i
            continue

        # 引用块 >
        if line.startswith("> "):
            text = line[2:]
            text = re.sub(r'\*\*(.+?)\*\*', r'<b>\1</b>', text)
            flowables.append(Paragraph(f'<i>{text}</i>', styles["warning"]))
            i += 1
            continue

        # 列表项
        if re.match(r'^[-*•]\s', line):
            text = line[2:]
            flowables.append(colorize_tags("• " + text, styles["bullet"]))
            i += 1
            continue
        if re.match(r'^\d+\.\s', line):
            text = re.sub(r'^\d+\.\s', '', line)
            flowables.append(colorize_tags(text, styles["bullet"]))
            i += 1
            continue
        if re.match(r'^\s+[-*]\s', line):
            text = line.strip()[2:]
            s = ParagraphStyle("indent", parent=styles["bullet"], leftIndent=24)
            flowables.append(colorize_tags("– " + text, s))
            i += 1
            continue

        # 普通段落
        if line.strip():
            flowables.append(colorize_tags(line.strip(), styles["body"]))
        i += 1

    return flowables


# ── 主函数 ────────────────────────────────────────────────────
def generate_pdf(md_path: Path, pdf_path: Path):
    styles = make_styles()
    md_text = md_path.read_text(encoding="utf-8")

    doc = SimpleDocTemplate(
        str(pdf_path),
        pagesize=A4,
        leftMargin=2*cm, rightMargin=2*cm,
        topMargin=2*cm, bottomMargin=2.5*cm,
        title=f"A股选股报告 {date.today()}",
        author="CC Awesome Stock",
    )

    story = []

    # 封面区
    story.append(Spacer(1, 0.3*cm))
    story.append(HRFlowable(width="100%", thickness=3, color=C_BLUE, spaceAfter=10))
    story.append(Paragraph("A股选股分析报告", styles["title"]))
    story.append(Paragraph(f"Generated by CC Awesome Stock · {date.today()}", styles["subtitle"]))
    story.append(HRFlowable(width="100%", thickness=0.5, color=C_BORDER, spaceAfter=12))

    # 正文
    story += md_to_flowables(md_text, styles)

    # 免责声明页脚
    story.append(Spacer(1, 1*cm))
    story.append(HRFlowable(width="100%", thickness=0.5, color=C_BORDER))
    story.append(Spacer(1, 4))
    story.append(Paragraph(
        "本报告由 AI 辅助生成，仅供研究参考，不构成投资建议。"
        "所有判断均已标注来源类型（事实/推断/假设/情绪/传闻）。"
        "投资有风险，入市须谨慎。",
        styles["footer"]
    ))

    def footer(canvas, doc):
        canvas.saveState()
        canvas.setFont(FONT, 7.5)
        canvas.setFillColor(colors.grey)
        canvas.drawString(2*cm, 1.2*cm, f"CC Awesome Stock · {date.today()}")
        canvas.drawRightString(A4[0]-2*cm, 1.2*cm, f"第 {doc.page} 页")
        canvas.restoreState()

    doc.build(story, onFirstPage=footer, onLaterPages=footer)
    print(f"PDF 已生成：{pdf_path}")


if __name__ == "__main__":
    project_root = Path(__file__).parent.parent
    reports_dir = project_root / "reports"
    reports_dir.mkdir(exist_ok=True)

    # 参数
    if len(sys.argv) >= 2:
        md_path = Path(sys.argv[1])
    else:
        # 找最新的报告
        md_files = sorted(reports_dir.glob("*.md"), reverse=True)
        if not md_files:
            print("找不到报告文件，请先运行 weekly_analysis.sh 或指定 .md 文件路径")
            sys.exit(1)
        md_path = md_files[0]

    if len(sys.argv) >= 3:
        pdf_path = Path(sys.argv[2])
    else:
        pdf_path = md_path.with_suffix(".pdf")

    generate_pdf(md_path, pdf_path)
