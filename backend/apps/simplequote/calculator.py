"""参数驱动的简单报价计算引擎。V1 覆盖注塑模具与 3D 打印，其余类型给出基础估算。

所有金额单位默认 KRW，参数可由后台 QuoteParam 覆盖默认值。
"""

from decimal import Decimal

DEFAULT_PARAMS = {
    # 注塑自动报价（AUTO QUOTATION）。金额单位 RMB。
    # 材料键使用规范化名称：ABS / ABS_Gf / PC / PA66 / PP（可后台新增）。
    "injection": {
        # 基本模具费（按材料）
        "mold_base_ABS": 15000,
        "mold_base_ABS_Gf": 20000,
        "mold_base_PC": 20000,
        "mold_base_PA66": 20000,
        "mold_base_PP": 15000,
        # 基本单价（RMB/kg）
        "unit_price_kg_ABS": 11,
        "unit_price_kg_ABS_Gf": 13,
        "unit_price_kg_PC": 18,
        "unit_price_kg_PA66": 22,
        "unit_price_kg_PP": 9,
        # 基本报价（1g 以下，RMB）
        "unit_base_ABS": 0.14,
        "unit_base_ABS_Gf": 0.16,
        "unit_base_PC": 0.18,
        "unit_base_PA66": 0.20,
        "unit_base_PP": 0.14,
        # 附加规则
        "slider_unit": 1000,       # 滑块每个加价
        "precision_add": 2000,     # 精密度 ≤0.2mm 加价
        "loss_factor": 2,          # 耗材重量 = 单件重量 × 系数（含流道/损耗）
        "color_transparent": 0.10,  # 透明加重 +10%
        "color_semi": 0.05,         # 半透明加重 +5%
        "packaging_rate": 0.03,     # 包装费 = 塑料费用的 3%
        "profit_rate": 0.20,        # 利润 +20%
        "rmb_to_krw": 190,          # 展示换算汇率
        "moq_kg": 25,               # 未指定 PANTONE 时 MOQ
        # 材料密度（g/cm³），用于上传 STP 后由体积估算重量
        "density_ABS": 1.05,
        "density_ABS_Gf": 1.23,
        "density_PC": 1.20,
        "density_PA66": 1.14,
        "density_PP": 0.91,
    },
    "print3d": {
        "material_price_PLA": 60,
        "material_price_ABS": 70,
        "material_price_PETG": 80,
        "material_price_Resin": 150,
        "material_price_Nylon": 180,
        "material_price_TPU": 160,
        "loss_factor": 1.1,
        "machine_hour_rate": 5000,
        "post_none": 0,
        "post_sanding": 3000,
        "post_paint": 8000,
        "rush_factor": 1.3,
    },
    "pcb": {
        "schematic_fee": 500000,
        "layout_fee_per_layer": 200000,
        "prototype_fee": 300000,
        "smt_fee": 500000,
        "bom_fee": 300000,
        "test_fee": 200000,
        "ad_discount_rate": 0.10,
        "valid_days": 30,
    },
    "pcba": {
        "smt_score_price": 0.01,
        "dip_score_price": 0.03,
        "rmb_to_krw": 226,
        "mask_fee": 150,
        "smt_test_fee": 0.3,
        "packaging_fee": 0.3,
        "default_smt_score": 2,
        "default_dip_score": 2,
    },
    "software": {
        "base_fee": 3000000,
        "module_fee": 1500000,
        "ui_fee": 2000000,
        "deploy_fee": 1000000,
        "test_fee": 800000,
    },
    "ic": {
        "design_fee": 2000000,
        "pcb_fee": 800000,
        "program_fee": 1500000,
        "sample_fee": 500000,
        "test_fee": 300000,
    },
    "paper_box": {
        "board_price_E": 4.5,
        "board_price_B": 5.5,
        "board_price_C": 6.0,
        "board_price_白卡": 8.0,
        "loss_factor": 0.05,
        "print_setup": 200,
        "print_per_color": 0.15,
        "die_cut_fee": 150,
        "glue_per_unit": 0.08,
        "profit_rate": 0.15,
        "rmb_to_krw": 190,
        "glue_tab_mm": 25,
    },
}


def _to_number(value, default=0):
    try:
        if isinstance(value, Decimal):
            return float(value)
        return float(value)
    except (TypeError, ValueError):
        return default


def build_param_map(quote_type, overrides):
    params = dict(DEFAULT_PARAMS.get(quote_type, {}))
    for key, value in (overrides or {}).items():
        params[key] = _to_number(value, params.get(key, 0))
    return params


def _int(value, default=0):
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _normalize_material(material):
    """规范化材料名用于参数键：ABS+Gf → ABS_Gf。"""
    return str(material or "ABS").replace("+", "_").replace(" ", "_").replace("-", "_")


def _round4(value):
    return round(float(value), 4)


class InjectionQuoteError(ValueError):
    """注塑报价输入错误（如 FAMILY 材料不一致）。"""


class PcbQuoteError(ValueError):
    """PCB 开发报价输入错误。"""


class PcbaQuoteError(ValueError):
    """PCBA 加工费报价输入错误。"""


class PaperBoxQuoteError(ValueError):
    """纸盒包装报价输入错误。"""


def _build_parts(inputs):
    """兼容单零件旧输入与 FAMILY 多零件输入，统一返回 parts 列表。"""
    parts = inputs.get("parts")
    if parts and isinstance(parts, list):
        return parts
    return [
        {
            "material": inputs.get("material", "ABS"),
            "color": inputs.get("color", "normal"),
            "weight_g": inputs.get("product_weight_g", inputs.get("weight_g", 0)),
            "cavity": inputs.get("cavity", 1),
            "slider_count": inputs.get("slider_count", 0),
            "quantity": inputs.get("quantity", 1),
        }
    ]


def weight_from_volume(volume_cm3, material, params):
    """由几何体积(cm³)与材料密度估算单件重量(g)。密度缺失时返回 None。"""
    density = params.get(f"density_{_normalize_material(material)}")
    if density is None or volume_cm3 is None:
        return None
    weight = _to_number(volume_cm3, 0) * _to_number(density, 0)
    return _round4(weight) if weight > 0 else None


def _color_factor(color, params):
    if color == "transparent":
        return 1 + params.get("color_transparent", 0.10)
    if color == "semi":
        return 1 + params.get("color_semi", 0.05)
    return 1.0


def _calc_part_unit_price(part, params):
    """按需求 5 步链式计算单件单价（RMB）。"""
    material = _normalize_material(part.get("material", "ABS"))
    weight = _to_number(part.get("weight_g"), 0)
    color = part.get("color", "normal")

    unit_price_kg = params.get(f"unit_price_kg_{material}", params.get("unit_price_kg_ABS", 11))
    unit_base = params.get(f"unit_base_{material}", params.get("unit_base_ABS", 0.14))
    loss = params.get("loss_factor", 2)
    packaging_rate = params.get("packaging_rate", 0.03)
    profit_rate = params.get("profit_rate", 0.20)

    material_cost = unit_price_kg * (weight * loss) / 1000
    base_sum = unit_base + material_cost
    after_color = base_sum * _color_factor(color, params)
    after_packaging = after_color * (1 + packaging_rate)
    unit_price = after_packaging * (1 + profit_rate)

    return {
        "material": part.get("material", "ABS"),
        "color": color,
        "weight_g": weight,
        "quantity": max(1, _int(part.get("quantity"), 1)),
        "unit_price": _round4(unit_price),
        "breakdown": [
            {"label": "재료비 / 材料费", "amount": _round4(material_cost)},
            {"label": "기본합계 / 基本合计", "amount": _round4(base_sum)},
            {"label": "색상 / 颜色加重", "amount": _round4(after_color)},
            {"label": "포장 / 包装费", "amount": _round4(after_packaging)},
            {"label": "이윤 / 利润后单价", "amount": _round4(unit_price)},
        ],
    }


def calc_injection(inputs, params):
    parts = _build_parts(inputs)
    if not parts:
        raise InjectionQuoteError("至少需要一个零件")

    materials = {_normalize_material(p.get("material", "ABS")) for p in parts}
    is_family = len(parts) > 1
    if is_family and len(materials) > 1:
        raise InjectionQuoteError("FAMILY 模具要求所有零件材料一致，请分开上传/分开报价")

    profit_rate = params.get("profit_rate", 0.20)
    slider_unit = params.get("slider_unit", 1000)
    precision_add = params.get("precision_add", 2000)

    # 模具费：基本费(按材料，取一次) + 滑块累加 + 精密度加价，× 利润
    mold_material = _normalize_material(parts[0].get("material", "ABS"))
    mold_base = params.get(f"mold_base_{mold_material}", params.get("mold_base_ABS", 15000))
    slider_total = sum(max(0, _int(p.get("slider_count"), 0)) for p in parts)
    slider_fee = slider_total * slider_unit
    is_precision = bool(inputs.get("is_precision"))
    precision_fee = precision_add if is_precision else 0
    mold_before_profit = mold_base + slider_fee + precision_fee
    mold_fee = round(mold_before_profit * (1 + profit_rate))

    # 各零件单价
    part_results = [_calc_part_unit_price(p, params) for p in parts]
    product_total = round(sum(r["unit_price"] * r["quantity"] for r in part_results))

    total = round(mold_fee + product_total)
    rmb_to_krw = params.get("rmb_to_krw", 0)
    total_krw = round(total * rmb_to_krw) if rmb_to_krw else None

    breakdown = [
        {"label": "금형비 / 模具费", "amount": mold_fee},
        {"label": "제품단가 합계 / 制品单价合计", "amount": product_total},
    ]

    return {
        "currency": "CNY",
        "is_family": is_family,
        "mold": {
            "material": parts[0].get("material", "ABS"),
            "base": round(mold_base),
            "slider_count": slider_total,
            "slider_fee": slider_fee,
            "precision_fee": precision_fee,
            "profit_rate": profit_rate,
            "total": mold_fee,
        },
        "parts": part_results,
        "mold_fee": mold_fee,
        "product_total": product_total,
        "production_fee": None,
        "shipping_fee": None,
        "vat": None,
        "moq_kg": params.get("moq_kg", 25),
        "rmb_to_krw": rmb_to_krw,
        "total_krw": total_krw,
        "quantity": sum(r["quantity"] for r in part_results),
        "total": total,
        "breakdown": breakdown,
    }


def calc_print3d(inputs, params):
    material = inputs.get("material", "PLA")
    weight = _to_number(inputs.get("model_weight_g"), 0)
    print_hours = _to_number(inputs.get("print_hours"), 0)
    quantity = max(1, _int(inputs.get("quantity"), 1))
    post = inputs.get("post_process", "none")
    rush = bool(inputs.get("rush"))

    material_unit = params.get(f"material_price_{material}", params.get("material_price_PLA", 60))
    loss = params.get("loss_factor", 1.1)
    material_cost = weight * material_unit * loss
    machine_cost = print_hours * params.get("machine_hour_rate", 5000)
    post_cost = params.get(f"post_{post}", 0)
    unit_price = material_cost + machine_cost + post_cost
    if rush:
        unit_price *= params.get("rush_factor", 1.3)
    unit_price = round(unit_price)
    total = unit_price * quantity
    breakdown = [
        {"label": "材料费", "amount": round(material_cost)},
        {"label": "设备使用费", "amount": round(machine_cost)},
        {"label": "后处理费", "amount": round(post_cost)},
    ]
    return {
        "unit_price": unit_price,
        "mold_fee": 0,
        "quantity": quantity,
        "total": total,
        "breakdown": breakdown,
    }


def _calc_sum(inputs, params, items):
    breakdown = []
    total = 0
    for key, label in items:
        include = inputs.get(key, True)
        if include:
            amount = round(params.get(key, 0))
            breakdown.append({"label": label, "amount": amount})
            total += amount
    return {"unit_price": total, "mold_fee": 0, "quantity": 1, "total": total, "breakdown": breakdown}


def _match_score(package, tech, tables):
    scores = (tables or {}).get("component_scores") or []
    pkg = str(package or "").upper().strip()
    tech = str(tech or "smt").lower()
    for row in scores:
        if str(row.get("tech", "")).lower() == tech and str(row.get("package", "")).upper() == pkg:
            return _to_number(row.get("score"), 0), False
    return None, True


def calc_pcba(inputs, params, tables=None):
    """PCBA SMT/DIP 计分制加工费（RMB），展示 KRW。"""
    components = inputs.get("components") or []
    pcb_qty = max(1, _int(inputs.get("pcb_quantity"), 1))
    array_count = max(1, _int(inputs.get("array_count"), 1))

    smt_price = params.get("smt_score_price", 0.01)
    dip_price = params.get("dip_score_price", 0.03)
    default_smt = params.get("default_smt_score", 2)
    default_dip = params.get("default_dip_score", 2)

    smt_total = 0
    dip_total = 0
    line_items = []
    warnings = []

    for comp in components:
        qty = max(1, _int(comp.get("qty"), 1))
        tech = str(comp.get("tech", "smt")).lower()
        package = comp.get("package", "")
        score, used_default = _match_score(package, tech, tables)
        if score is None:
            score = default_smt if tech == "smt" else default_dip
            used_default = True
        if used_default:
            warnings.append(f"{package}({tech}) 使用默认计分 {score}")

        unit_price = smt_price if tech == "smt" else dip_price
        line_fee = score * unit_price * qty
        if tech == "smt":
            smt_total += line_fee
        else:
            dip_total += line_fee
        line_items.append(
            {
                "package": package,
                "tech": tech,
                "qty": qty,
                "score": score,
                "fee_rmb": _round4(line_fee),
            }
        )

    mask_fee = params.get("mask_fee", 150)
    test_fee = params.get("smt_test_fee", 0.3) * pcb_qty
    pack_fee = params.get("packaging_fee", 0.3) * array_count
    fixed_total = mask_fee + test_fee + pack_fee
    process_total = smt_total + dip_total
    total_rmb = _round4(fixed_total + process_total)
    rmb_to_krw = params.get("rmb_to_krw", 226)
    total_krw = round(total_rmb * rmb_to_krw)

    breakdown = [
        {"label": "钢网 / METAL MASK", "amount": round(mask_fee)},
        {"label": "SMT 测试费 / SMT test", "amount": round(test_fee)},
        {"label": "包装费 / Packaging", "amount": round(pack_fee)},
        {"label": "SMT 加工费 / SMT labor", "amount": round(smt_total)},
        {"label": "DIP 加工费 / DIP labor", "amount": round(dip_total)},
    ]

    return {
        "currency": "CNY",
        "pcb_quantity": pcb_qty,
        "array_count": array_count,
        "smt_total_rmb": _round4(smt_total),
        "dip_total_rmb": _round4(dip_total),
        "fixed_total_rmb": _round4(fixed_total),
        "line_items": line_items,
        "warnings": warnings,
        "excludes": ["元器件物料费", "开机费", "小批量工艺费"],
        "rmb_to_krw": rmb_to_krw,
        "total_krw": total_krw,
        "mold_fee": 0,
        "quantity": pcb_qty,
        "total": round(total_rmb),
        "breakdown": breakdown,
    }


def _find_base_item(tables, item_no):
    for row in (tables or {}).get("base_pricing") or []:
        if _int(row.get("no")) == _int(item_no):
            return row
    return None


def calc_pcb(inputs, params, tables=None):
    """PCB 开发成本：清单 A/B + 服务费 + 权重 + 广告折扣 + 简化配送费。"""
    from apps.simplequote.shipping import calc_pcb_shipping_simple

    base_no = inputs.get("base_item_no")
    if base_no is None:
        raise PcbQuoteError("请选择开发类型")

    base_item = _find_base_item(tables, base_no)
    if not base_item:
        raise PcbQuoteError("无效的开发类型编号")

    group = str(base_item.get("group", "A")).upper()
    if group not in ("A", "B"):
        raise PcbQuoteError("开发类型分组无效")

    alt_group = inputs.get("alt_group")
    if alt_group and str(alt_group).upper() != group:
        raise PcbQuoteError("A/B 类开发类型不可同时选择")

    weight_keys = inputs.get("weight_keys") or ["mass_production", "pcb_fr4", "qty_2", "size_100"]
    weight_map = {row.get("key"): row for row in (tables or {}).get("weights") or []}
    weight_sum = 0
    weight_details = []
    for key in weight_keys:
        row = weight_map.get(key)
        if not row:
            continue
        w = _to_number(row.get("weight"), 1)
        weight_sum += w
        weight_details.append({"key": key, "weight": w, "label": row.get("label_zh", key)})

    if weight_sum <= 0:
        weight_sum = 1

    base_fee = _to_number(base_item.get("base_fee_krw"), 0)
    dev_subtotal = round(base_fee * weight_sum)

    service_nos = inputs.get("service_nos") or []
    service_map = {_int(row.get("no")): row for row in (tables or {}).get("services") or []}
    service_total = 0
    service_items = []
    for no in service_nos:
        row = service_map.get(_int(no))
        if not row:
            continue
        fee = round(_to_number(row.get("fee_krw"), 0))
        service_total += fee
        service_items.append({"no": no, "label": row.get("label_zh", ""), "fee_krw": fee})

    dev_before_discount = dev_subtotal
    ad_consent = bool(inputs.get("ad_consent"))
    ad_discount = 0
    if ad_consent:
        rate = params.get("ad_discount_rate", 0.10)
        ad_discount = round(dev_before_discount * rate)
        dev_before_discount = dev_before_discount - ad_discount

    shipping_weight = _to_number(inputs.get("shipping_weight_kg"), 1)
    shipping = calc_pcb_shipping_simple(shipping_weight, params)
    shipping_fee = shipping.get("fee_krw", 0)

    total = dev_before_discount + service_total + shipping_fee

    breakdown = [
        {
            "label": f"开发费 / Dev ({base_item.get('label_zh', '')})",
            "amount": dev_subtotal,
        },
    ]
    for wd in weight_details:
        breakdown.append({"label": f"权重 / Weight {wd['label']}", "amount": wd["weight"]})
    if ad_discount:
        breakdown.append({"label": "广告折扣 / Ad discount -10%", "amount": -ad_discount})
    for svc in service_items:
        breakdown.append({"label": f"服务 / {svc['label']}", "amount": svc["fee_krw"]})
    breakdown.append({"label": "配送费 / Shipping (简化规则)", "amount": shipping_fee})

    return {
        "currency": "KRW",
        "base_item_no": _int(base_no),
        "base_item": base_item,
        "weight_sum": weight_sum,
        "weight_details": weight_details,
        "dev_subtotal": dev_subtotal,
        "ad_consent": ad_consent,
        "ad_discount": ad_discount,
        "dev_after_discount": dev_before_discount,
        "service_items": service_items,
        "service_total": service_total,
        "shipping": shipping,
        "shipping_fee": shipping_fee,
        "vat_included": False,
        "development_days": _int(base_item.get("days"), 0),
        "mold_fee": 0,
        "quantity": 1,
        "total": total,
        "breakdown": breakdown,
    }


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


CALCULATORS = {
    "injection": calc_injection,
    "print3d": calc_print3d,
    "pcba": calc_pcba,
    "pcb": calc_pcb,
    "software": calc_software,
    "ic": calc_ic,
    "paper_box": calc_paper_box,
}


def calculate(quote_type, inputs, param_overrides=None, table_overrides=None):
    if quote_type not in CALCULATORS:
        raise ValueError("unsupported quote type")
    params = build_param_map(quote_type, param_overrides)
    tables = table_overrides or {}
    calc_fn = CALCULATORS[quote_type]
    if quote_type in ("pcba", "pcb"):
        return calc_fn(inputs or {}, params, tables)
    return calc_fn(inputs or {}, params)
