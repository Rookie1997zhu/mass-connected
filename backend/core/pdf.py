"""通用 PDF 生成工具（基于 reportlab）。用于报价书、比较报价书、合同等。

返回 bytes，由调用方保存到 FileField 或直接下载。
"""

import io

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import (
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

BRAND = "MASS CONNECTED"


def _styles():
    styles = getSampleStyleSheet()
    return styles


def build_comparison_pdf(*, title, quote_no, headers, rows, notes=None):
    """生成多方案比较报价 PDF。

    headers: list[str] 表头列名
    rows: list[list[str]] 每行数据
    """
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        leftMargin=12 * mm,
        rightMargin=12 * mm,
        topMargin=18 * mm,
        bottomMargin=18 * mm,
    )
    styles = _styles()
    story = []
    story.append(Paragraph(f"<b>{BRAND}</b>", styles["Title"]))
    story.append(Paragraph(title, styles["Heading2"]))
    story.append(Paragraph(f"编号 / No.: {quote_no}", styles["Normal"]))
    story.append(Spacer(1, 10))

    col_count = len(headers)
    col_width = (165 * mm) / max(col_count, 1)
    data = [headers] + [[str(cell) for cell in row] for row in rows]
    table = Table(data, colWidths=[col_width] * col_count, repeatRows=1)
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1f2937")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTSIZE", (0, 0), (-1, -1), 8),
                ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#d1d5db")),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ]
        )
    )
    story.append(table)
    story.append(Spacer(1, 12))
    default_notes = [
        "本比较报价书为平台整理后的方案对比，仅供参考。",
        "最终价格与交期以双方确认合同为准。",
    ]
    for note in (notes or default_notes):
        story.append(Paragraph(f"• {note}", styles["Normal"]))
    doc.build(story)
    pdf = buffer.getvalue()
    buffer.close()
    return pdf


def build_quotation_pdf(*, title, quote_no, meta_rows, line_items, total_label, total_amount,
                        currency="KRW", notes=None):
    """生成通用报价/文档 PDF。

    meta_rows: list[(label, value)] 基本信息
    line_items: list[(label, amount)] 明细
    """
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        leftMargin=18 * mm,
        rightMargin=18 * mm,
        topMargin=18 * mm,
        bottomMargin=18 * mm,
    )
    styles = _styles()
    story = []

    story.append(Paragraph(f"<b>{BRAND}</b>", styles["Title"]))
    story.append(Paragraph(title, styles["Heading2"]))
    story.append(Paragraph(f"编号 / No.: {quote_no}", styles["Normal"]))
    story.append(Spacer(1, 8))

    if meta_rows:
        meta_table = Table([[str(k), str(v)] for k, v in meta_rows], colWidths=[45 * mm, 120 * mm])
        meta_table.setStyle(
            TableStyle(
                [
                    ("FONTSIZE", (0, 0), (-1, -1), 9),
                    ("TEXTCOLOR", (0, 0), (0, -1), colors.grey),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                    ("TOPPADDING", (0, 0), (-1, -1), 4),
                ]
            )
        )
        story.append(meta_table)
        story.append(Spacer(1, 10))

    data = [["项目 / Item", f"金额 / Amount ({currency})"]]
    for label, amount in line_items:
        data.append([str(label), f"{int(amount):,}"])
    data.append([total_label, f"{int(total_amount):,}"])
    item_table = Table(data, colWidths=[110 * mm, 55 * mm])
    item_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1f2937")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTSIZE", (0, 0), (-1, -1), 9),
                ("ALIGN", (1, 0), (1, -1), "RIGHT"),
                ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#d1d5db")),
                ("BACKGROUND", (0, -1), (-1, -1), colors.HexColor("#f3f4f6")),
                ("FONTNAME", (0, -1), (-1, -1), "Helvetica-Bold"),
                ("TOPPADDING", (0, 0), (-1, -1), 5),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ]
        )
    )
    story.append(item_table)
    story.append(Spacer(1, 12))

    default_notes = [
        "本报价为系统自动生成的初步报价，仅供参考。",
        "最终价格以详细报价及双方确认内容为准。",
        "报价有效期以文档标注为准，逾期需重新确认。",
    ]
    for note in (notes or default_notes):
        story.append(Paragraph(f"• {note}", styles["Normal"]))

    doc.build(story)
    pdf = buffer.getvalue()
    buffer.close()
    return pdf
