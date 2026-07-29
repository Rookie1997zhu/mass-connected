"""3D 打印报价计算。"""

from apps.simplequote.calculator.utils import _int, _to_number


def calc_print3d(inputs, params, tables=None):
    """3D 打印报价：支持兼容机时模式与切片成本累加/按克模式。

    inputs 可带 config_snapshot（切片任务冻结配置）以优先取材料单价与加价系数。
    """
    material = inputs.get("material", "PLA")
    weight = _to_number(inputs.get("model_weight_g"), 0)
    print_hours = _to_number(inputs.get("print_hours"), 0)
    quantity = max(1, _int(inputs.get("quantity"), 1))
    post = inputs.get("post_process", "none")
    rush = bool(inputs.get("rush"))
    snapshot = inputs.get("config_snapshot") or {}
    snap_params = snapshot.get("params") or {}
    merged = dict(params or {})
    for key, value in snap_params.items():
        merged[key] = _to_number(value, merged.get(key, 0))

    pricing_mode = snapshot.get("pricing_mode") or merged.get("pricing_mode", 0)
    if pricing_mode == 1 or pricing_mode == "1" or pricing_mode == "per_gram":
        pricing_mode = "per_gram"
    elif pricing_mode in (0, "0", "custom"):
        # Prefer advanced formula when snapshot present; else legacy machine_hour
        pricing_mode = "custom" if snapshot else "legacy"
    else:
        pricing_mode = "legacy" if not snapshot else "custom"

    material_cfg = snapshot.get("material") or {}
    printer_cfg = snapshot.get("printer") or {}
    post_cfg = snapshot.get("post_processing") or {}
    loss = _to_number(merged.get("loss_factor"), 1.1)
    gst_rate = _to_number(merged.get("gst_rate"), 0)
    rush_factor = _to_number(merged.get("rush_factor"), 1.3)

    if post_cfg:
        post_cost = _to_number(post_cfg.get("price"), 0)
    else:
        post_cost = _to_number(merged.get(f"post_{post}"), 0)

    if pricing_mode == "per_gram":
        per_gram = _to_number(
            material_cfg.get("per_gram_price"),
            merged.get(f"material_price_{material}", merged.get("material_price_PLA", 60)),
        )
        material_cost = weight * per_gram * loss
        unit_before_tax = material_cost + post_cost
        if rush:
            unit_before_tax *= rush_factor
        gst_amount = unit_before_tax * gst_rate
        unit_price = round(unit_before_tax + gst_amount)
        total = unit_price * quantity
        breakdown = [
            {"label": "材料费", "amount": round(material_cost)},
            {"label": "后处理费", "amount": round(post_cost)},
        ]
        if gst_amount:
            breakdown.append({"label": "税费", "amount": round(gst_amount)})
        return {
            "unit_price": unit_price,
            "mold_fee": 0,
            "quantity": quantity,
            "total": total,
            "breakdown": breakdown,
            "pricing_mode": "per_gram",
            "filament_weight_g": weight,
            "print_hours": print_hours,
        }

    if pricing_mode == "custom":
        price_per_kg = _to_number(
            material_cfg.get("price_per_kg"),
            _to_number(merged.get(f"material_price_{material}"), 60) * 1000,
        )
        material_cost = (weight / 1000.0) * price_per_kg * loss
        power_kw = _to_number(merged.get("printer_power_watts"), 1000) / 1000.0
        electricity = power_kw * print_hours * _to_number(merged.get("electricity_rate_per_kwh"), 150)
        depreciation = _to_number(merged.get("depreciation_per_hour"), 5000) * print_hours
        other = _to_number(merged.get("other_costs_per_print"), 0)
        base = _to_number(merged.get("base_cost"), 0)
        cost_before_markup = material_cost + electricity + depreciation + other + base
        markup = _to_number(printer_cfg.get("markup_multiplier"), 1.3)
        subtotal = cost_before_markup * markup + post_cost
        if rush:
            subtotal *= rush_factor
        gst_amount = subtotal * gst_rate
        unit_price = round(subtotal + gst_amount)
        total = unit_price * quantity
        breakdown = [
            {"label": "材料费", "amount": round(material_cost)},
            {"label": "电费", "amount": round(electricity)},
            {"label": "设备折旧", "amount": round(depreciation)},
            {"label": "基础/其他", "amount": round(base + other)},
            {"label": "后处理费", "amount": round(post_cost)},
        ]
        if markup != 1:
            breakdown.append({"label": "加价后小计", "amount": round(cost_before_markup * markup)})
        if gst_amount:
            breakdown.append({"label": "税费", "amount": round(gst_amount)})
        return {
            "unit_price": unit_price,
            "mold_fee": 0,
            "quantity": quantity,
            "total": total,
            "breakdown": breakdown,
            "pricing_mode": "custom",
            "markup_multiplier": markup,
            "filament_weight_g": weight,
            "print_hours": print_hours,
        }

    # legacy: weight × per-gram + machine hours
    material_unit = merged.get(
        f"material_price_{material}", merged.get("material_price_PLA", 60)
    )
    material_cost = weight * material_unit * loss
    machine_cost = print_hours * merged.get("machine_hour_rate", 5000)
    unit_price = material_cost + machine_cost + post_cost
    if rush:
        unit_price *= rush_factor
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
        "pricing_mode": "legacy",
        "filament_weight_g": weight,
        "print_hours": print_hours,
    }
