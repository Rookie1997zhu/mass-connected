"""运输费计算：空运阶梯 + 海运 LCL（无电池/含电池）。"""

import math


class ShippingError(ValueError):
    pass


def _to_number(value, default=0):
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _ceil_rt(value, step=0.1):
    return math.ceil(value / step) * step


def _lookup_tier(rows, chargeable_kg):
    """按计费重量查空运阶梯。"""
    for row in rows:
        w_min = _to_number(row.get("weight_min"), 0)
        w_max = _to_number(row.get("weight_max"), 999)
        if w_min <= chargeable_kg <= w_max:
            return row
    if rows:
        return rows[-1]
    return None


def _lookup_cbm(rows, cbm):
    for row in rows:
        c_min = _to_number(row.get("cbm_min"), 0)
        c_max = _to_number(row.get("cbm_max"), 999)
        if c_min <= cbm <= c_max:
            return row
    if rows:
        return rows[-1]
    return None


def calc_air(weight_kg, length_cm, width_cm, height_cm, params, tables):
    """空运阶梯计费，返回韩元。"""
    actual = max(0, _to_number(weight_kg))
    l, w, h = _to_number(length_cm), _to_number(width_cm), _to_number(height_cm)
    volume_weight = (l * w * h) / 6000 if l and w and h else 0
    chargeable = max(actual, volume_weight)

    tiers = tables.get("air_freight_tiers") or []
    tier = _lookup_tier(tiers, chargeable)
    if not tier:
        raise ShippingError("空运费率表未配置")

    fee = round(_to_number(tier.get("fee_krw")))
    return {
        "mode": "air",
        "actual_weight_kg": round(actual, 3),
        "volume_weight_kg": round(volume_weight, 3),
        "chargeable_weight_kg": round(chargeable, 3),
        "fee_krw": fee,
        "breakdown": [
            {"label": "实重 / Actual", "amount": round(actual, 3), "unit": "kg"},
            {"label": "体积重 / Volume", "amount": round(volume_weight, 3), "unit": "kg"},
            {"label": "计费重 / Chargeable", "amount": round(chargeable, 3), "unit": "kg"},
            {"label": "空运运费 / Air freight", "amount": fee, "unit": "KRW"},
        ],
    }


def calc_pcb_shipping_simple(weight_kg, params):
    """PCB 开发报价配送费简化规则。"""
    weight = max(0, _to_number(weight_kg))
    under_1 = _to_number(params.get("pcb_shipping_under_1kg", 24000))
    per_kg = _to_number(params.get("pcb_shipping_per_kg", 11600))
    if weight <= 1:
        fee = round(under_1)
        rule = "≤1kg fixed"
    else:
        billable = max(2, weight) if weight < 2 else weight
        fee = round(billable * per_kg)
        rule = "≥2kg × rate"
    return {
        "mode": "pcb_simple",
        "weight_kg": round(weight, 3),
        "fee_krw": fee,
        "rule": rule,
        "breakdown": [
            {"label": "配送重量 / Weight", "amount": round(weight, 3), "unit": "kg"},
            {"label": "配送费 / Shipping", "amount": fee, "unit": "KRW"},
        ],
    }


def calc_lcl(
    cbm,
    weight_kg,
    has_battery=False,
    service_days=4,
    has_pickup=False,
    pickup_fee_cny=800,
    has_co=False,
    co_fee_cny=200,
    params=None,
    tables=None,
):
    """海运 LCL 双方案。"""
    params = params or {}
    tables = tables or {}
    cbm_val = max(0, _to_number(cbm))
    weight = max(0, _to_number(weight_kg))
    days = 4 if int(service_days) == 4 else 5

    if has_battery:
        return _calc_lcl_battery(cbm_val, weight, days, params)
    return _calc_lcl_general(
        cbm_val, weight, days, has_pickup, pickup_fee_cny, has_co, co_fee_cny, params, tables
    )


def _calc_lcl_general(cbm, weight_kg, days, has_pickup, pickup_fee_cny, has_co, co_fee_cny, params, tables):
    usd_krw = _to_number(params.get("usd_to_krw", 1580))
    cny_krw = _to_number(params.get("cny_to_krw", 232.4))
    rate = _to_number(params.get("lcl_rate_4day" if days == 4 else "lcl_rate_5day", 55 if days == 4 else 50))
    min_fee = _to_number(params.get("lcl_min_4day" if days == 4 else "lcl_min_5day", 30 if days == 4 else 25))

    rt_raw = max(cbm, weight_kg / 250)
    rt = _ceil_rt(rt_raw, 0.1)
    ocean_usd = max(min_fee, rt * rate)

    cbm_row = _lookup_cbm(tables.get("lcl_cbm_fees") or [], cbm) or {}
    line_sur = _to_number(cbm_row.get("line_sur_usd"))
    handling = _to_number(cbm_row.get("handling_krw"))
    bonded = _to_number(cbm_row.get("bonded_krw"))
    port = _to_number(cbm_row.get("port_krw"))

    export_agent = max(3, math.ceil(cbm) * 3)
    fuel = 3 if cbm <= 0.5 else (6 if cbm <= 1 else math.ceil(cbm) * 6)
    do_fee = 19000

    pickup_krw = round(pickup_fee_cny * cny_krw) if has_pickup else 0
    co_krw = round(co_fee_cny * cny_krw) if has_co else 0

    usd_total = ocean_usd + line_sur + export_agent + fuel
    krw_items = handling + bonded + port + do_fee + pickup_krw + co_krw
    total_krw = round(usd_total * usd_krw + krw_items)

    breakdown = [
        {"label": f"计费 R/T ({days}日)", "amount": rt, "unit": "R/T"},
        {"label": "海运运费 / Ocean", "amount": round(ocean_usd * usd_krw), "unit": "KRW"},
        {"label": "LINE SUR", "amount": round(line_sur * usd_krw), "unit": "KRW"},
        {"label": "出口代理 / Export agent", "amount": round(export_agent * usd_krw), "unit": "KRW"},
        {"label": "燃油附加 / Fuel", "amount": round(fuel * usd_krw), "unit": "KRW"},
        {"label": "D/O", "amount": do_fee, "unit": "KRW"},
        {"label": "Handling", "amount": round(handling), "unit": "KRW"},
        {"label": "保税仓 / Bonded", "amount": round(bonded), "unit": "KRW"},
        {"label": "港口费 / Port", "amount": round(port), "unit": "KRW"},
    ]
    if pickup_krw:
        breakdown.append({"label": "提货 / Pickup", "amount": pickup_krw, "unit": "KRW"})
    if co_krw:
        breakdown.append({"label": "C/O", "amount": co_krw, "unit": "KRW"})

    return {
        "mode": "lcl_general",
        "service_days": days,
        "has_battery": False,
        "cbm": cbm,
        "weight_kg": weight_kg,
        "rt": rt,
        "fee_krw": total_krw,
        "breakdown": breakdown,
    }


def _calc_lcl_battery(cbm, weight_kg, days, params):
    usd_krw = _to_number(params.get("usd_to_krw_battery", 1500))
    cny_krw = _to_number(params.get("cny_to_krw", 232.4))
    min_cbm = _to_number(params.get("battery_min_cbm", 1))
    rate = _to_number(params.get("battery_rate_4day" if days == 4 else "battery_rate_5day", 85 if days == 4 else 75))
    over_rate = _to_number(
        params.get(
            "battery_overweight_4day" if days == 4 else "battery_overweight_5day",
            1.5 if days == 4 else 1.2,
        )
    )

    bill_cbm = max(min_cbm, cbm)
    ocean_krw = round(bill_cbm * rate * usd_krw)

    kg_per_cbm = 200
    overweight = max(0, weight_kg - bill_cbm * kg_per_cbm)
    overweight_krw = round(overweight * over_rate * cny_krw) if overweight else 0

    per_cbm_krw = 5500 + 7000 + 323 + 200 + 16000
    cfs_krw = round(bill_cbm * per_cbm_krw)
    do_krw = 19000
    handling_krw = round(30 * usd_krw)
    baf_krw = round(12 * bill_cbm * usd_krw)
    doc_krw = round(16 * usd_krw)

    total = ocean_krw + overweight_krw + cfs_krw + do_krw + handling_krw + baf_krw + doc_krw

    return {
        "mode": "lcl_battery",
        "service_days": days,
        "has_battery": True,
        "cbm": cbm,
        "bill_cbm": bill_cbm,
        "weight_kg": weight_kg,
        "fee_krw": total,
        "breakdown": [
            {"label": "海运费 / Ocean", "amount": ocean_krw, "unit": "KRW"},
            {"label": "超重附加 / Overweight", "amount": overweight_krw, "unit": "KRW"},
            {"label": "THC+CFS+仓库等", "amount": cfs_krw, "unit": "KRW"},
            {"label": "D/O", "amount": do_krw, "unit": "KRW"},
            {"label": "HANDLING", "amount": handling_krw, "unit": "KRW"},
            {"label": "BAF/CAF", "amount": baf_krw, "unit": "KRW"},
            {"label": "出口文件 / DOC", "amount": doc_krw, "unit": "KRW"},
        ],
    }


def estimate_shipping(inputs, params, tables):
    """统一入口：根据 mode 分发。"""
    mode = (inputs or {}).get("mode", "air")
    if mode == "air":
        return calc_air(
            inputs.get("weight_kg"),
            inputs.get("length_cm"),
            inputs.get("width_cm"),
            inputs.get("height_cm"),
            params,
            tables,
        )
    if mode == "lcl":
        return calc_lcl(
            cbm=inputs.get("cbm"),
            weight_kg=inputs.get("weight_kg"),
            has_battery=bool(inputs.get("has_battery")),
            service_days=inputs.get("service_days", 4),
            has_pickup=bool(inputs.get("has_pickup")),
            pickup_fee_cny=inputs.get("pickup_fee_cny", 800),
            has_co=bool(inputs.get("has_co")),
            co_fee_cny=inputs.get("co_fee_cny", 200),
            params=params,
            tables=tables,
        )
    if mode == "pcb_simple":
        return calc_pcb_shipping_simple(inputs.get("weight_kg"), params)
    if mode == "fcl":
        return {
            "mode": "fcl",
            "fee_krw": None,
            "message": "FCL 费率表待补充",
            "breakdown": [],
        }
    raise ShippingError("不支持的运输模式")
