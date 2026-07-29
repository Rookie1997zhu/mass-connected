"""注塑模具与制品报价计算。"""

from apps.simplequote.calculator.utils import (
    InjectionQuoteError,
    _int,
    _normalize_material,
    _round4,
    _to_number,
)


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

    # 图示：1g 及以下仅用基本报价，不计重量材料费
    if weight <= 1:
        material_cost = 0.0
    else:
        material_cost = unit_price_kg * (weight * loss) / 1000

    base_sum = unit_base + material_cost
    after_color = base_sum * _color_factor(color, params)
    after_packaging = after_color * (1 + packaging_rate)
    unit_price = after_packaging * (1 + profit_rate)
    color_surcharge = after_color - base_sum
    packaging_fee = after_packaging - after_color

    return {
        "material": part.get("material", "ABS"),
        "color": color,
        "weight_g": weight,
        "quantity": max(1, _int(part.get("quantity"), 1)),
        "unit_base": _round4(unit_base),
        "material_cost": _round4(material_cost),
        "base_sum": _round4(base_sum),
        "after_color": _round4(after_color),
        "after_packaging": _round4(after_packaging),
        "color_surcharge": _round4(color_surcharge),
        "packaging_fee": _round4(packaging_fee),
        "unit_price": _round4(unit_price),
        "breakdown": [
            {"label": "재료비 / 材料费", "amount": _round4(material_cost)},
            {"label": "기본견적 / 基础费用", "amount": _round4(unit_base)},
            {"label": "생산비용 / 生产成本", "amount": _round4(after_color)},
            {"label": "특수비용 / 特殊费用", "amount": _round4(color_surcharge)},
            {"label": "포장 / 包装费", "amount": _round4(packaging_fee)},
            {"label": "이윤 / 利润后单价", "amount": _round4(unit_price)},
        ],
    }


def _shipping_tables(tables):
    from apps.simplequote.table_data import AIR_FREIGHT_TIERS

    tiers = (tables or {}).get("air_freight_tiers")
    if not tiers:
        tiers = AIR_FREIGHT_TIERS
    return {"air_freight_tiers": tiers}


def _estimate_injection_shipping(inputs, parts, params, tables):
    """注塑整单运输费：默认空运阶梯，KRW 换算为 CNY。"""
    from apps.simplequote.shipping import ShippingError, estimate_shipping

    total_weight_g = sum(
        _to_number(p.get("weight_g"), 0) * max(1, _int(p.get("quantity"), 1)) for p in parts
    )
    if total_weight_g <= 0:
        return None

    weight_kg = total_weight_g / 1000
    bbox = inputs.get("bbox_mm")
    length_cm = width_cm = height_cm = 0
    if bbox and len(bbox) >= 3:
        length_cm = _to_number(bbox[0]) / 10
        width_cm = _to_number(bbox[1]) / 10
        height_cm = _to_number(bbox[2]) / 10

    try:
        ship_result = estimate_shipping(
            {
                "mode": inputs.get("shipping_mode", "air"),
                "weight_kg": weight_kg,
                "length_cm": length_cm,
                "width_cm": width_cm,
                "height_cm": height_cm,
            },
            {},
            _shipping_tables(tables),
        )
    except ShippingError:
        return None

    rmb_to_krw = _to_number(params.get("rmb_to_krw"), 190)
    fee_krw = _to_number(ship_result.get("fee_krw"), 0)
    fee_cny = round(fee_krw / rmb_to_krw, 2) if rmb_to_krw else None

    return {
        "mode": ship_result.get("mode"),
        "fee_krw": round(fee_krw),
        "fee_cny": fee_cny,
        "actual_weight_kg": ship_result.get("actual_weight_kg"),
        "volume_weight_kg": ship_result.get("volume_weight_kg"),
        "chargeable_weight_kg": ship_result.get("chargeable_weight_kg"),
        "breakdown": ship_result.get("breakdown", []),
    }


def calc_injection(inputs, params, shipping_tables=None):
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

    shipping = _estimate_injection_shipping(inputs, parts, params, shipping_tables)
    shipping_fee = shipping.get("fee_cny") if shipping else None
    production_fee = part_results[0]["after_color"] if part_results else None

    total = round(mold_fee + product_total + (shipping_fee or 0))
    rmb_to_krw = params.get("rmb_to_krw", 0)
    total_krw = round(total * rmb_to_krw) if rmb_to_krw else None

    breakdown = [
        {"label": "금형비 / 模具费", "amount": mold_fee},
        {"label": "제품단가 합계 / 制品单价合计", "amount": product_total},
    ]
    if shipping_fee is not None:
        breakdown.append({"label": "운송비용 / 运输费用", "amount": shipping_fee})

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
        "production_fee": production_fee,
        "production_fee_note": "per_unit_before_packaging",
        "shipping_fee": shipping_fee,
        "shipping": shipping,
        "vat": None,
        "moq_kg": params.get("moq_kg", 25),
        "rmb_to_krw": rmb_to_krw,
        "total_krw": total_krw,
        "quantity": sum(r["quantity"] for r in part_results),
        "total": total,
        "breakdown": breakdown,
    }
