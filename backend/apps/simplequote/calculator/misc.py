"""软件、IC 方案与纸盒包装报价计算。"""

from apps.simplequote.calculator.utils import (
    PaperBoxQuoteError,
    _int,
    _round4,
    _to_number,
)


def calc_software(inputs, params):
    modules = _int(inputs.get("module_count"), 0)
    breakdown = [{"label": "基础开发费", "amount": round(params.get("base_fee", 0))}]
    if modules:
        breakdown.append({"label": f"功能模块 x{modules}", "amount": round(params.get("module_fee", 0) * modules)})
    if inputs.get("need_ui"):
        breakdown.append({"label": "UI 设计", "amount": round(params.get("ui_fee", 0))})
    if inputs.get("need_deploy"):
        breakdown.append({"label": "服务器部署", "amount": round(params.get("deploy_fee", 0))})
    breakdown.append({"label": "测试费用", "amount": round(params.get("test_fee", 0))})
    total = sum(item["amount"] for item in breakdown)
    return {"unit_price": total, "mold_fee": 0, "quantity": 1, "total": total, "breakdown": breakdown}


def calc_ic(inputs, params):
    breakdown = [{"label": "方案设计费", "amount": round(params.get("design_fee", 0))}]
    if inputs.get("need_pcb"):
        breakdown.append({"label": "PCB 设计", "amount": round(params.get("pcb_fee", 0))})
    if inputs.get("need_program"):
        breakdown.append({"label": "程序开发", "amount": round(params.get("program_fee", 0))})
    if inputs.get("need_sample"):
        breakdown.append({"label": "样品制作", "amount": round(params.get("sample_fee", 0))})
    breakdown.append({"label": "测试费用", "amount": round(params.get("test_fee", 0))})
    total = sum(item["amount"] for item in breakdown)
    return {"unit_price": total, "mold_fee": 0, "quantity": 1, "total": total, "breakdown": breakdown}


def calc_paper_box(inputs, params):
    """纸盒包装报价（RMB）。展开面积由后端权威重算，忽略前端传入面积。"""
    from apps.simplequote.packaging import PaperBoxGeometryError, unfold_by_code

    box_code = str(inputs.get("box_code", "0201"))

    length_mm = _to_number(inputs.get("length_mm"), 0)
    width_mm = _to_number(inputs.get("width_mm"), 0)
    height_mm = _to_number(inputs.get("height_mm"), 0)
    thickness_mm = _to_number(inputs.get("thickness_mm"), 1.5)
    dimension_type = inputs.get("dimension_type", "internal")
    quantity = max(1, _int(inputs.get("quantity"), 1))
    print_colors = max(0, _int(inputs.get("print_colors"), 0))
    board_type = str(inputs.get("board_type", "E") or "E")

    try:
        geometry = unfold_by_code(
            box_code,
            length_mm,
            width_mm,
            height_mm,
            thickness_mm=thickness_mm,
            dimension_type=dimension_type,
            glue_tab_mm=params.get("glue_tab_mm", 25),
        )
    except PaperBoxGeometryError as exc:
        raise PaperBoxQuoteError(str(exc)) from exc

    area_m2 = geometry["unfold_area_m2"]
    board_key = f"board_price_{board_type}"
    board_price = params.get(board_key, params.get("board_price_E", 4.5))
    loss_factor = params.get("loss_factor", 0.05)

    material_cost = area_m2 * board_price * (1 + loss_factor) * quantity
    print_cost = params.get("print_setup", 200) + print_colors * params.get("print_per_color", 0.15) * quantity
    die_cut_cost = params.get("die_cut_fee", 150)
    glue_cost = params.get("glue_per_unit", 0.08) * quantity
    subtotal = material_cost + print_cost + die_cut_cost + glue_cost
    profit_rate = params.get("profit_rate", 0.15)
    total = round(subtotal * (1 + profit_rate))
    rmb_to_krw = params.get("rmb_to_krw", 190)
    total_krw = round(total * rmb_to_krw) if rmb_to_krw else None
    unit_price = _round4(total / quantity) if quantity else total

    breakdown = [
        {"label": "材料费 / Material", "amount": round(material_cost)},
        {"label": "印刷费 / Print", "amount": round(print_cost)},
        {"label": "模切费 / Die cut", "amount": round(die_cut_cost)},
        {"label": "粘盒费 / Glue", "amount": round(glue_cost)},
        {"label": f"利润 / Profit (+{int(profit_rate * 100)}%)", "amount": total - round(subtotal)},
    ]

    return {
        "currency": "CNY",
        "box_code": box_code,
        "board_type": board_type,
        "geometry": geometry,
        "unfold_area_m2": area_m2,
        "blank_width_mm": geometry["blank_width_mm"],
        "blank_height_mm": geometry["blank_height_mm"],
        "print_colors": print_colors,
        "material_cost": round(material_cost),
        "print_cost": round(print_cost),
        "die_cut_cost": round(die_cut_cost),
        "glue_cost": round(glue_cost),
        "profit_rate": profit_rate,
        "rmb_to_krw": rmb_to_krw,
        "total_krw": total_krw,
        "unit_price": unit_price,
        "mold_fee": 0,
        "quantity": quantity,
        "total": total,
        "breakdown": breakdown,
    }
