"""嘉立创 SMT 在线计价工艺费（离线复刻，不含元器件费）。

费率来源：exports/jlc_smt_calc/rates/rates.json（REA + smtOnlinePricing 差分）。
合计使用 plateChangeMaterialCountMoney，不使用 changeMaterielMoney（后者仅展示）。
"""

from apps.simplequote.calculator.utils import SmtQuoteError, _int, _round4, _to_number


def _fee_block(
    *,
    project_money,
    pad_money,
    manual_pad_money,
    manual_project_money,
    change_materiel_money,
    plate_change_money,
    steel_money,
    package_money,
):
    total = _round4(
        project_money
        + pad_money
        + manual_pad_money
        + manual_project_money
        + plate_change_money
        + steel_money
        + package_money
    )
    return {
        "projectMoney": _round4(project_money),
        "padMoney": _round4(pad_money),
        "manualPadMoney": _round4(manual_pad_money),
        "manualWeldProjectMoney": _round4(manual_project_money),
        "changeMaterielMoney": _round4(change_materiel_money),
        "plateChangeMaterialCountMoney": _round4(plate_change_money),
        "steelMoney": _round4(steel_money),
        "packageMoney": _round4(package_money),
        "totalMoney": total,
    }


def calc_smt(inputs, params, tables=None):
    """SMT 工艺费（CNY）。同时给出经济型 / 标准型；落库主金额取标准型合计。"""
    del tables  # 费率走 QuoteParam，本轮无表

    board_length = _to_number(inputs.get("board_length_cm"), 0)
    board_width = _to_number(inputs.get("board_width_cm"), 0)
    if board_length <= 0 or board_width <= 0:
        raise SmtQuoteError("请输入有效的板子尺寸（cm）")

    location = str(inputs.get("patch_location") or "T").upper().strip()
    if location not in ("T", "TB"):
        raise SmtQuoteError("贴片面仅支持 T（单面）或 TB（双面）")

    patch_quantity = _int(inputs.get("patch_quantity"), 0)
    if patch_quantity < 2:
        raise SmtQuoteError("贴片数量至少 2 片")

    patch_pads = max(0, _int(inputs.get("patch_component_quantity"), 0))
    patch_types = max(0, _int(inputs.get("patch_component_type"), 0))
    plugin_pads = max(0, _int(inputs.get("plugin_quantity"), 0))
    plugin_type_count = max(0, _int(inputs.get("plugin_type"), 0))

    pad_unit = _to_number(params.get("pad_fee_per_joint"), 0.01)
    manual_pad_unit = _to_number(params.get("manual_pad_fee_per_joint"), 0.1)
    manual_project_fee = _to_number(params.get("manual_project_fee_if_plugin"), 20.0)
    package_base = _to_number(params.get("package_base"), 3.0)
    package_area_qty_rate = _to_number(params.get("package_area_qty_rate"), 0.0002)
    plate_change_per_type = _to_number(params.get("plate_change_per_type"), 5.0)
    change_eco = _to_number(params.get("change_materiel_per_type_economic"), 20.0)
    change_std = _to_number(params.get("change_materiel_per_type_standard"), 8.0)

    pad_money = pad_unit * patch_pads * patch_quantity
    has_plugin = plugin_pads > 0
    manual_pad_money = (manual_pad_unit * plugin_pads * patch_quantity) if has_plugin else 0.0
    manual_project_money = manual_project_fee if has_plugin else 0.0
    plate_change_money = plate_change_per_type * patch_types

    eco_available = location == "T" and patch_quantity <= 50

    economic = None
    if eco_available:
        economic = _fee_block(
            project_money=_to_number(params.get("project_fee_economic_T"), 50.0),
            pad_money=pad_money,
            manual_pad_money=manual_pad_money,
            manual_project_money=manual_project_money,
            change_materiel_money=change_eco * patch_types,
            plate_change_money=plate_change_money,
            steel_money=_to_number(params.get("steel_fee_economic"), 0.0),
            package_money=0.0,
        )

    if location == "TB":
        project_std = _to_number(params.get("project_fee_standard_TB"), 300.0)
        steel_std = _to_number(params.get("steel_fee_standard_TB"), 100.0)
    else:
        project_std = _to_number(params.get("project_fee_standard_T"), 150.0)
        steel_std = _to_number(params.get("steel_fee_standard_T"), 50.0)

    package_std = package_base + package_area_qty_rate * board_length * board_width * patch_quantity
    standard = _fee_block(
        project_money=project_std,
        pad_money=pad_money,
        manual_pad_money=manual_pad_money,
        manual_project_money=manual_project_money,
        change_materiel_money=change_std * patch_types,
        plate_change_money=plate_change_money,
        steel_money=steel_std,
        package_money=package_std,
    )

    total = standard["totalMoney"]
    breakdown = [
        {"label": "工程费 / Project (标准型)", "amount": round(standard["projectMoney"], 2)},
        {"label": "贴片焊点费 / SMT pads", "amount": round(standard["padMoney"], 2)},
        {"label": "手工焊点费 / Manual pads", "amount": round(standard["manualPadMoney"], 2)},
        {"label": "手工工程费 / Manual project", "amount": round(standard["manualWeldProjectMoney"], 2)},
        {"label": "换料计入 / Plate change", "amount": round(standard["plateChangeMaterialCountMoney"], 2)},
        {"label": "钢网费 / Stencil", "amount": round(standard["steelMoney"], 2)},
        {"label": "包装费 / Package", "amount": round(standard["packageMoney"], 2)},
    ]
    if economic:
        breakdown.append(
            {"label": "经济型合计 / Economic total", "amount": round(economic["totalMoney"], 2)}
        )

    return {
        "currency": "CNY",
        "board_length_cm": board_length,
        "board_width_cm": board_width,
        "patch_location": location,
        "patch_quantity": patch_quantity,
        "patch_component_quantity": patch_pads,
        "patch_component_type": patch_types,
        "plugin_quantity": plugin_pads,
        "plugin_type": plugin_type_count,
        "eco_available": eco_available,
        "economic": economic,
        "standard": standard,
        "excludes": ["元器件物料费"],
        "quantity": patch_quantity,
        "mold_fee": 0,
        "total": round(total, 2),
        "breakdown": breakdown,
        "notes": [
            "工艺费估算，对齐嘉立创 SMT 在线计价模型；非官方成交价。",
            "元器件费不下发，固定为下单时计算。",
            "经济型不可用于双面贴片或数量大于 50 片。",
        ],
    }
