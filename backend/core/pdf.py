"""通用 PDF 生成工具（基于 reportlab）。用于报价书、比较报价书、合同等。

返回 bytes，由调用方保存到 FileField 或直接下载。
"""

import io

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.cidfonts import UnicodeCIDFont
from reportlab.platypus import (
    Image as RLImage,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

BRAND = "MASS CONNECTED"

# reportlab 内置 CID 字体，支持韩文/中文/日文，无需打包字体文件。
CJK_FONT = "HYSMyeongJo-Medium"
_CJK_REGISTERED = False


def _ensure_cjk_font():
    """注册 CJK 字体，避免报价单中韩文/中文缺字。失败时回退默认字体。"""
    global _CJK_REGISTERED
    if _CJK_REGISTERED:
        return CJK_FONT
    try:
        pdfmetrics.registerFont(UnicodeCIDFont(CJK_FONT))
        _CJK_REGISTERED = True
        return CJK_FONT
    except Exception:
        return "Helvetica"


def _styles():
    styles = getSampleStyleSheet()
    font = _ensure_cjk_font()
    for style_name in ("Normal", "Title", "Heading1", "Heading2", "Heading3"):
        if style_name in styles.byName:
            styles[style_name].fontName = font
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
                        currency="KRW", notes=None, fx_rate=None, total_cny=None, total_krw=None):
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

    cur = (currency or "KRW").upper()
    rate = None
    try:
        if fx_rate is not None and float(fx_rate) > 0:
            rate = float(fx_rate)
    except (TypeError, ValueError):
        rate = None
    if rate:
        if cur == "CNY":
            converted = total_krw if total_krw is not None else round(float(total_amount) * rate)
            data.append([f"환산 / 换算 (KRW @ {_fmt_amount(rate, 4)})", _fmt_amount(converted)])
        else:
            converted = total_cny if total_cny is not None else round(float(total_amount) / rate, 2)
            data.append([f"환산 / 换算 (CNY @ {_fmt_amount(rate, 4)})", _fmt_amount(converted, 2)])

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


def _fmt_amount(value, decimals=0):
    if value is None:
        return "-"
    try:
        number = float(value)
    except (TypeError, ValueError):
        return str(value)
    if decimals:
        return f"{number:,.{decimals}f}"
    return f"{int(round(number)):,}"


_COLOR_LABELS = {
    "transparent": "투명 / 透明",
    "semi": "반투명 / 半透明",
    "normal": "일반 / 普通",
    "pantone": "PANTONE",
}


def build_injection_quotation_pdf(*, quote_no, product_name, inputs, result, valid_until, created_at):
    """注塑（사출·금형）自动报价单 PDF，对齐 AUTO QUOTATION 模板。金额单位 RMB。"""
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        leftMargin=15 * mm,
        rightMargin=15 * mm,
        topMargin=15 * mm,
        bottomMargin=15 * mm,
    )
    styles = _styles()
    font = _ensure_cjk_font()
    story = []

    mold = result.get("mold", {}) or {}
    parts = result.get("parts", []) or []
    rmb_to_krw = result.get("rmb_to_krw") or 0
    total = result.get("total", 0)
    total_krw = result.get("total_krw")

    story.append(Paragraph(f"<b>{BRAND}</b>", styles["Title"]))
    story.append(Paragraph("사출·금형견적 / AUTO QUOTATION", styles["Heading2"]))
    story.append(Spacer(1, 6))

    # 基本信息 + 右上汇总
    file_name = inputs.get("file_name", "-") or "-"
    mold_material = inputs.get("mold_material", "-") or "-"
    head_rows = [
        ["견적번호 / 编号", quote_no, "금형·단가 / 模具单价", f"{_fmt_amount(result.get('mold_fee'))} RMB"],
        ["고객사 / 客户", product_name, "제품·단가 합계 / 制品单价合计", f"{_fmt_amount(result.get('product_total'))} RMB"],
        ["작성일 / 作成", created_at, "금형재질 / 模具材质", mold_material],
        ["파일명 / 文件", file_name, "유효기간 / 有效期", valid_until],
    ]
    head_table = Table(head_rows, colWidths=[30 * mm, 55 * mm, 40 * mm, 55 * mm])
    head_table.setStyle(
        TableStyle(
            [
                ("FONTNAME", (0, 0), (-1, -1), font),
                ("FONTSIZE", (0, 0), (-1, -1), 8),
                ("TEXTCOLOR", (0, 0), (0, -1), colors.grey),
                ("TEXTCOLOR", (2, 0), (2, -1), colors.grey),
                ("TOPPADDING", (0, 0), (-1, -1), 3),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
            ]
        )
    )
    story.append(head_table)
    story.append(Spacer(1, 10))

    # 1. 금형비
    story.append(Paragraph("1. 금형비 / 模具费", styles["Heading3"]))
    mold_rows = [
        ["항목 / Item", "금액 / Amount (RMB)"],
        [f"기본금형비 / 基本模具费 ({mold.get('material', '-')})", _fmt_amount(mold.get("base"))],
        [f"슬라이드 / 滑块 x{mold.get('slider_count', 0)}", _fmt_amount(mold.get("slider_fee"))],
        ["정밀도 / 精密度 (≤0.2mm)", _fmt_amount(mold.get("precision_fee"))],
        [f"이윤 / 利润 (+{int(round(float(mold.get('profit_rate', 0)) * 100))}%) 후 합계", _fmt_amount(result.get("mold_fee"))],
    ]
    story.append(_amount_table(mold_rows, font))
    story.append(Spacer(1, 8))

    # 2. 제품단가 TOTAL
    story.append(Paragraph("2. 제품단가 TOTAL / 制品单价", styles["Heading3"]))
    part_rows = [["재질/材料", "색상/颜色", "중량(g)", "수량", "개당단가(RMB)"]]
    for part in parts:
        part_rows.append(
            [
                str(part.get("material", "-")),
                _COLOR_LABELS.get(part.get("color", "normal"), part.get("color", "-")),
                _fmt_amount(part.get("weight_g"), 2),
                _fmt_amount(part.get("quantity")),
                _fmt_amount(part.get("unit_price"), 4),
            ]
        )
    part_table = Table(part_rows, colWidths=[35 * mm, 40 * mm, 25 * mm, 25 * mm, 35 * mm])
    part_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1f2937")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTNAME", (0, 0), (-1, -1), font),
                ("FONTSIZE", (0, 0), (-1, -1), 8),
                ("ALIGN", (2, 0), (-1, -1), "RIGHT"),
                ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#d1d5db")),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ]
        )
    )
    story.append(part_table)
    story.append(Spacer(1, 6))

    # 生产/运输/VAT + 合计
    total_rows = [
        ["생산비용 / 生产费用 (개당)", _fmt_amount(result.get("production_fee"), 4)],
        ["운송비용 / 运输费用 (整单)", _fmt_amount(result.get("shipping_fee"), 2)],
        ["VAT", _fmt_amount(result.get("vat"))],
        ["총단가 / 总单价 (RMB)", _fmt_amount(total)],
    ]
    if rmb_to_krw and total_krw is not None:
        total_rows.append([f"환산 / 换算 (KRW @ {_fmt_amount(rmb_to_krw)})", _fmt_amount(total_krw)])
    story.append(_amount_table(total_rows, font, highlight_last=True))
    story.append(Spacer(1, 8))

    # 3. 산정기준명세서
    story.append(Paragraph("3. 산정기준명세서 / 计算基准明细", styles["Heading3"]))
    if parts:
        first = parts[0]
        detail_rows = [["단계 / 步骤", "값 / 值 (RMB)"]]
        for item in first.get("breakdown", []):
            detail_rows.append([item.get("label", "-"), _fmt_amount(item.get("amount"), 4)])
        if result.get("shipping_fee") is not None:
            detail_rows.append(["운송비 / 运输费 (整单)", _fmt_amount(result.get("shipping_fee"), 2)])
        story.append(_amount_table(detail_rows, font))
        story.append(Spacer(1, 6))

    moq_kg = result.get("moq_kg", 25)
    notes = [
        f"PANTONE 미지정 시 MOQ {_fmt_amount(moq_kg)}KG 적용.",
        "상기 단가는 참고용이며 실제 견적과 약 80% 정확도입니다.",
        "본 견적서는 작성일로부터 2주간 유지됩니다.",
        "FAMILY 견적 지원. 재질이 다를 경우 분리 업로드가 필요합니다.",
    ]
    for note in notes:
        story.append(Paragraph(f"• {note}", styles["Normal"]))

    doc.build(story)
    pdf = buffer.getvalue()
    buffer.close()
    return pdf


def build_nda_pdf(
    *,
    title,
    version,
    company_name,
    body,
    signed_at,
    business_reg_no="",
    company_address="",
    signer_name="",
    signature_image_path=None,
):
    """保密协议 PDF；签署后可附带客户签名图。"""
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
    _ensure_cjk_font()
    story = []

    story.append(Paragraph(f"<b>{BRAND}</b>", styles["Title"]))
    story.append(Paragraph(title, styles["Heading2"]))
    story.append(Paragraph(f"版本 / Version: {version}", styles["Normal"]))
    story.append(Paragraph(f"签署日期 / Signed: {signed_at}", styles["Normal"]))
    story.append(Paragraph(f"客户 / Client: {company_name}", styles["Normal"]))
    story.append(Spacer(1, 12))

    for paragraph in (body or "").split("\n"):
        text = paragraph.strip()
        if text:
            story.append(Paragraph(text.replace("<", "&lt;").replace(">", "&gt;"), styles["Normal"]))
            story.append(Spacer(1, 4))

    story.append(Spacer(1, 16))
    story.append(Paragraph("供方 / CONNECTED: 커넥티드（CONNECTED）", styles["Normal"]))
    story.append(Paragraph("事业者登记号: 652-18-02371", styles["Normal"]))
    story.append(
        Paragraph(
            "地址: 首尔特别市 衿川区 数码路10街 37，16层 1607号（加山洞，Ask Tower）",
            styles["Normal"],
        )
    )
    story.append(Paragraph("代表: 홍승범", styles["Normal"]))
    story.append(Spacer(1, 10))
    story.append(Paragraph(f"客户 / Client: {company_name}", styles["Normal"]))
    if business_reg_no:
        story.append(Paragraph(f"事业者登记号: {business_reg_no}", styles["Normal"]))
    if company_address:
        story.append(Paragraph(f"地址: {company_address}", styles["Normal"]))
    if signer_name:
        story.append(Paragraph(f"签署人: {signer_name}", styles["Normal"]))

    if signature_image_path:
        try:
            img = RLImage(signature_image_path, width=50 * mm, height=20 * mm)
            story.append(Spacer(1, 8))
            story.append(Paragraph("客户签名 / Signature:", styles["Normal"]))
            story.append(img)
        except Exception:
            pass

    doc.build(story)
    pdf = buffer.getvalue()
    buffer.close()
    return pdf


def build_paper_box_quotation_pdf(*, quote_no, product_name, inputs, result, valid_until, created_at):
    """纸盒包装报价单 PDF。"""
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        leftMargin=15 * mm,
        rightMargin=15 * mm,
        topMargin=15 * mm,
        bottomMargin=15 * mm,
    )
    styles = _styles()
    font = _ensure_cjk_font()
    story = []

    geometry = result.get("geometry") or {}
    story.append(Paragraph(f"<b>{BRAND}</b>", styles["Title"]))
    story.append(Paragraph("纸盒包装 견적 / Paper Box Quote (FEFCO 0201)", styles["Heading2"]))
    story.append(Spacer(1, 6))

    meta_rows = [
        ["견적번호 / 编号", quote_no, "고객 / 客户", product_name or "-"],
        ["盒型 / Box", f"FEFCO {result.get('box_code', '0201')}", "材质 / Board", str(result.get("board_type", "-"))],
        [
            "展开尺寸 / Blank",
            f"{geometry.get('blank_width_mm', '-')} x {geometry.get('blank_height_mm', '-')} mm",
            "展开面积 / Area",
            f"{result.get('unfold_area_m2', '-')} m²",
        ],
        ["작성일 / 作成", created_at, "유효기간 / 有效期", valid_until],
        ["数量 / Qty", str(result.get("quantity", 1)), "印刷色数 / Colors", str(result.get("print_colors", 0))],
    ]
    meta_table = Table(meta_rows, colWidths=[30 * mm, 55 * mm, 30 * mm, 55 * mm])
    meta_table.setStyle(
        TableStyle(
            [
                ("FONTNAME", (0, 0), (-1, -1), font),
                ("FONTSIZE", (0, 0), (-1, -1), 8),
                ("TOPPADDING", (0, 0), (-1, -1), 3),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
            ]
        )
    )
    story.append(meta_table)
    story.append(Spacer(1, 10))

    story.append(Paragraph("1. 费用明细 / Cost Breakdown", styles["Heading3"]))
    line_rows = [["항목 / Item", "금액(RMB)"]]
    for item in result.get("breakdown") or []:
        line_rows.append([str(item.get("label", "-")), _fmt_amount(item.get("amount"))])
    story.append(_amount_table(line_rows, font))
    story.append(Spacer(1, 8))

    total_rows = [
        ["单价 / Unit (RMB)", _fmt_amount(result.get("unit_price"), 4)],
        ["합계 / Total (RMB)", _fmt_amount(result.get("total"))],
    ]
    rmb_to_krw = result.get("rmb_to_krw") or result.get("cny_to_krw")
    if result.get("total_krw") is not None and rmb_to_krw:
        total_rows.append(
            [f"환산 / 换算 (KRW @ {_fmt_amount(rmb_to_krw, 4)})", _fmt_amount(result.get("total_krw"))]
        )
    elif result.get("total_krw"):
        total_rows.append(["환산 / KRW", _fmt_amount(result.get("total_krw"))])
    story.append(_amount_table(total_rows, font, highlight_last=True))

    notes = [
        "展开面积由系统按 FEFCO 0201 标准公式重算，刀版图请以前端导出文件为准。",
        "本报价为系统自动生成的初步报价，仅供参考。",
        "最终价格以详细报价及双方确认内容为准。",
    ]
    for note in notes:
        story.append(Paragraph(f"• {note}", styles["Normal"]))

    doc.build(story)
    pdf = buffer.getvalue()
    buffer.close()
    return pdf


def _amount_table(rows, font, highlight_last=False):
    """两列（项目/金额）表格，首行表头，可选高亮末行合计。"""
    table = Table(rows, colWidths=[110 * mm, 55 * mm])
    style = [
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1f2937")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, -1), font),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("ALIGN", (1, 0), (1, -1), "RIGHT"),
        ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#d1d5db")),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
    ]
    if highlight_last:
        style.append(("BACKGROUND", (0, -1), (-1, -1), colors.HexColor("#f3f4f6")))
    table.setStyle(TableStyle(style))
    return table


def build_pcba_quotation_pdf(*, quote_no, product_name, inputs, result, valid_until, created_at):
    """PCBA 加工费报价单 PDF。"""
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        leftMargin=15 * mm,
        rightMargin=15 * mm,
        topMargin=15 * mm,
        bottomMargin=15 * mm,
    )
    styles = _styles()
    font = _ensure_cjk_font()
    story = []

    story.append(Paragraph(f"<b>{BRAND}</b>", styles["Title"]))
    story.append(Paragraph("PCBA 가공비 견적 / PCBA Assembly Quote", styles["Heading2"]))
    story.append(Spacer(1, 6))

    meta_rows = [
        ["견적번호 / 编号", quote_no, "고객 / 客户", product_name or "-"],
        ["작성일 / 作成", created_at, "유효기간 / 有效期", valid_until],
        ["PCB 수량 / PCB Qty", str(result.get("pcb_quantity", 1)), "ARRAY 수", str(result.get("array_count", 1))],
    ]
    meta_table = Table(meta_rows, colWidths=[30 * mm, 55 * mm, 30 * mm, 55 * mm])
    meta_table.setStyle(
        TableStyle(
            [
                ("FONTNAME", (0, 0), (-1, -1), font),
                ("FONTSIZE", (0, 0), (-1, -1), 8),
                ("TOPPADDING", (0, 0), (-1, -1), 3),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
            ]
        )
    )
    story.append(meta_table)
    story.append(Spacer(1, 10))

    story.append(Paragraph("1. 고정비 / 基础固定费", styles["Heading3"]))
    fixed_rows = [["항목 / Item", "금액(RMB)"]]
    for item in (result.get("breakdown") or [])[:3]:
        fixed_rows.append([item.get("label", "-"), _fmt_amount(item.get("amount"))])
    story.append(_amount_table(fixed_rows, font))
    story.append(Spacer(1, 8))

    story.append(Paragraph("2. 부품별 가공비 / 元件加工费", styles["Heading3"]))
    comp_rows = [["封装/Package", "Tech", "Qty", "Score", "Fee(RMB)"]]
    for line in result.get("line_items") or []:
        comp_rows.append(
            [
                str(line.get("package", "-")),
                str(line.get("tech", "-")),
                str(line.get("qty", 0)),
                str(line.get("score", 0)),
                _fmt_amount(line.get("fee_rmb"), 4),
            ]
        )
    comp_table = Table(comp_rows, colWidths=[40 * mm, 25 * mm, 20 * mm, 25 * mm, 35 * mm])
    comp_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1f2937")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTNAME", (0, 0), (-1, -1), font),
                ("FONTSIZE", (0, 0), (-1, -1), 8),
                ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#d1d5db")),
            ]
        )
    )
    story.append(comp_table)
    story.append(Spacer(1, 8))

    total_rows = [
        ["합계 / Total (RMB)", _fmt_amount(result.get("total"))],
    ]
    rmb_to_krw = result.get("rmb_to_krw") or result.get("cny_to_krw")
    if result.get("total_krw") is not None and rmb_to_krw:
        total_rows.append(
            [f"환산 / 换算 (KRW @ {_fmt_amount(rmb_to_krw, 4)})", _fmt_amount(result.get("total_krw"))]
        )
    elif result.get("total_krw"):
        total_rows.append(["환산 / KRW", _fmt_amount(result.get("total_krw"))])
    story.append(_amount_table(total_rows, font, highlight_last=True))

    excludes = result.get("excludes") or []
    notes = ["본 견적은 SMT/DIP 가공비(인건비)만 포함합니다."]
    notes.extend([f"미포함: {x}" for x in excludes])
    for note in notes:
        story.append(Paragraph(f"• {note}", styles["Normal"]))

    doc.build(story)
    pdf = buffer.getvalue()
    buffer.close()
    return pdf


def build_pcb_dev_quotation_pdf(*, quote_no, product_name, inputs, result, valid_until, created_at):
    """PCB 开发成本报价单 PDF。"""
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        leftMargin=15 * mm,
        rightMargin=15 * mm,
        topMargin=15 * mm,
        bottomMargin=15 * mm,
    )
    styles = _styles()
    font = _ensure_cjk_font()
    story = []

    base_item = result.get("base_item") or {}
    story.append(Paragraph(f"<b>{BRAND}</b>", styles["Title"]))
    story.append(Paragraph("PCB 개발비 견적 / PCB Development Quote", styles["Heading2"]))
    story.append(Spacer(1, 6))

    meta_rows = [
        ["견적번호 / 编号", quote_no, "고객 / 客户", product_name or "-"],
        ["개발유형 / Type", base_item.get("label_zh", "-"), "개발기간 / Days", str(result.get("development_days", "-"))],
        ["작성일 / 作成", created_at, "유효기간 / 有效期", valid_until],
    ]
    meta_table = Table(meta_rows, colWidths=[30 * mm, 55 * mm, 30 * mm, 55 * mm])
    meta_table.setStyle(
        TableStyle(
            [
                ("FONTNAME", (0, 0), (-1, -1), font),
                ("FONTSIZE", (0, 0), (-1, -1), 8),
                ("TOPPADDING", (0, 0), (-1, -1), 3),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
            ]
        )
    )
    story.append(meta_table)
    story.append(Spacer(1, 10))

    story.append(Paragraph("1. 비용明細 / 费用明细", styles["Heading3"]))
    line_rows = [["항목 / Item", "금액(KRW)"]]
    for item in result.get("breakdown") or []:
        amount_min = item.get("amount_min")
        amount_max = item.get("amount_max")
        if (
            amount_min is not None
            and amount_max is not None
            and amount_min != amount_max
        ):
            amount_text = f"{_fmt_amount(amount_min)} ~ {_fmt_amount(amount_max)}"
        else:
            amount_text = _fmt_amount(item.get("amount"))
        line_rows.append([str(item.get("label", "-")), amount_text])
    story.append(_amount_table(line_rows, font))

    story.append(Spacer(1, 8))
    total_min = result.get("total_min")
    total_max = result.get("total_max")
    if total_min is not None and total_max is not None and total_min != total_max:
        total_rows = [
            [
                "개발비 합계 구간 / Total range (VAT 별도)",
                f"{_fmt_amount(total_min)} ~ {_fmt_amount(total_max)}",
            ],
            ["개발비 합계(中位) / Total mid (VAT 별도)", _fmt_amount(result.get("total"))],
        ]
    else:
        total_rows = [["개발비 합계 / Total (VAT 별도)", _fmt_amount(result.get("total"))]]
    fx_rate = result.get("rmb_to_krw") or result.get("cny_to_krw")
    if result.get("total_cny") is not None and fx_rate:
        total_rows.append(
            [f"환산 / 换算 (CNY @ {_fmt_amount(fx_rate, 4)})", _fmt_amount(result.get("total_cny"), 2)]
        )
    story.append(_amount_table(total_rows, font, highlight_last=True))

    manufacturing = result.get("pcb_manufacturing") or {}
    if manufacturing.get("enabled"):
        process_defaults = {
            "fr4": {
                "board_thickness": "1.6",
                "solder_color": "绿色",
                "surface_finish": "有铅喷锡",
                "copper_thickness": "1oz",
                "solder_mask_coverage": "过孔盖油",
                "panel_design_count": "1",
            },
            "fpc": {
                "board_thickness": "0.11",
                "solder_color": "页面默认",
                "surface_finish": "沉金",
                "copper_thickness": "1oz",
                "solder_mask_coverage": "页面默认",
                "panel_design_count": "1",
            },
            "aluminum": {
                "board_thickness": "1.6",
                "solder_color": "绿色",
                "surface_finish": "无铅喷锡",
                "copper_thickness": "1oz",
                "solder_mask_coverage": "过孔盖油",
                "panel_design_count": "1",
            },
        }
        selected_process = {
            **process_defaults.get(manufacturing.get("material_key"), {}),
            **(manufacturing.get("selected_process") or {}),
        }
        process_adjustments = manufacturing.get("process_adjustments") or []
        process_adjustment_text = "; ".join(
            f"{item.get('field', '-')}: {item.get('value', '-')} ({float(item.get('amount_cny') or 0):+.2f} CNY)"
            for item in process_adjustments
            if abs(float(item.get("amount_cny") or 0)) > 0.005
        ) or "Standard / None"
        if manufacturing.get("pricing_display_mode") == "range":
            jlc_text = (
                f"{_fmt_amount(manufacturing.get('jlc_estimate_cny_min'), 2)}"
                f" ~ {_fmt_amount(manufacturing.get('jlc_estimate_cny_max'), 2)}"
            )
            customer_cny_text = (
                f"{_fmt_amount(manufacturing.get('customer_quote_cny_min'), 2)}"
                f" ~ {_fmt_amount(manufacturing.get('customer_quote_cny_max'), 2)}"
            )
            customer_krw_text = (
                f"{_fmt_amount(manufacturing.get('customer_quote_krw_min'))}"
                f" ~ {_fmt_amount(manufacturing.get('customer_quote_krw_max'))}"
            )
        else:
            jlc_text = _fmt_amount(manufacturing.get("jlc_estimate_cny"), 2)
            customer_cny_text = _fmt_amount(manufacturing.get("customer_quote_cny"), 2)
            customer_krw_text = _fmt_amount(manufacturing.get("customer_quote_krw"))
        story.append(Spacer(1, 8))
        story.append(Paragraph("2. PCB 샘플 제작비 / PCB 样板制造费", styles["Heading3"]))
        mfg_rows = [
            ["항목 / Item", "값 / Value"],
            ["Material", manufacturing.get("material_label") or manufacturing.get("material_key", "-")],
            ["Layers", str(manufacturing.get("layers", "-"))],
            [
                "Size / Qty",
                f"{manufacturing.get('width_mm', '-')} x {manufacturing.get('height_mm', '-')} mm / {manufacturing.get('quantity', '-')}",
            ],
            ["Finished thickness", f"{selected_process.get('board_thickness', '-')} mm"],
            ["Solder mask", selected_process.get("solder_color", "-")],
            ["Surface finish", selected_process.get("surface_finish", "-")],
            ["Copper weight", selected_process.get("copper_thickness", "-")],
            ["阻焊覆盖 / Solder mask coverage", selected_process.get("solder_mask_coverage", "-")],
            ["拼板款数 / Panel designs", selected_process.get("panel_design_count", "-")],
            [
                "SMT需求 / SMT required",
                "是 / Yes（贴片费另计，不含于制造费）" if manufacturing.get("smt_required") else "否 / No",
            ],
            ["JLC estimate (CNY)", jlc_text],
            ["Customer quote (CNY)", customer_cny_text],
            ["Converted (KRW)", customer_krw_text],
            [
                "Pricing mode",
                "Verified estimate" if manufacturing.get("is_estimated") else "Exact lookup",
            ],
            [
                "Display mode",
                manufacturing.get("pricing_display_mode") or "legacy",
            ],
            ["Base pricing mode", manufacturing.get("base_pricing_mode") or manufacturing.get("pricing_mode") or "-"],
            ["工艺调整 / Process adjustment", process_adjustment_text],
            ["Process validation", manufacturing.get("process_validation_status") or "-"],
            [
                "风险状态 / Risk status",
                manufacturing.get("risk_status") or ("-" if not manufacturing.get("risk_zone") else "manual_review"),
            ],
            [
                "Confidence",
                f"{float(manufacturing.get('confidence') or 0) * 100:.1f}%"
                if manufacturing.get("is_estimated")
                else "100%",
            ],
            ["Price version", manufacturing.get("active_price_version") or manufacturing.get("price_version") or "-"],
            ["Acceptance status", manufacturing.get("acceptance_status") or "legacy"],
            ["Fallback version", manufacturing.get("fallback_version") or "-"],
            ["Estimator version", manufacturing.get("estimator_version") or "-"],
            ["Process model version", manufacturing.get("process_model_version") or "-"],
        ]
        story.append(_amount_table(mfg_rows, font))

    notes = [
        "VAT 미포함 / 不含增值税",
        "≤300만원 개발비 100% 선불 / 300万韩元以下开发费100%预付",
        "광고 동의 시 개발비 10% 할인 적용 가능",
        "배송비는 PCB 개발 견적용 간소 규칙 적용",
        "PCB样板制造费基于 JLC 公开采样价 + 10% margin，不含运费/税费/Gerber 审核附加费。",
    ]
    if manufacturing.get("pricing_display_mode") == "range":
        notes.append(
            "PCB样板制造费与总价展示为 ±20% 参考区间（相对中位价），实际下单价格可能落在区间外。"
        )
    if result.get("ad_consent"):
        notes.append("광고 동의: 예 / 广告同意: 是")
    if manufacturing.get("acceptance_status") and manufacturing.get("acceptance_status") != "passed":
        notes.append(
            "独立验收未通过：非精确命中规格的估算/工艺自动报价已受限"
            f"（fallback={manufacturing.get('fallback_version') or 'jlc-cn-pcb-v6-20260712'}）。"
        )
    if manufacturing.get("requires_manual_review"):
        reasons = "；".join(manufacturing.get("manual_review_reasons") or ["需人工确认"])
        notes.append(f"PCB样板制造费待人工确认：{reasons}")
    elif manufacturing.get("is_estimated"):
        notes.append("PCB样板制造费为通过 JLC live holdout 门禁的估算价，实际下单价格可能发生变化。")
    for note in notes:
        story.append(Paragraph(f"• {note}", styles["Normal"]))

    doc.build(story)
    pdf = buffer.getvalue()
    buffer.close()
    return pdf
