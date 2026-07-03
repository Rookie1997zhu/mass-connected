"""参数驱动的简单报价计算引擎。V1 覆盖注塑模具与 3D 打印，其余类型给出基础估算。

所有金额单位默认 KRW，参数可由后台 QuoteParam 覆盖默认值。
"""

from decimal import Decimal

DEFAULT_PARAMS = {
    "injection": {
        "material_price_ABS": 3,
        "material_price_PC": 5,
        "material_price_PMMA": 5,
        "material_price_PP": 2,
        "material_price_PA66": 6,
        "material_price_POM": 6,
        "material_price_TPE": 7,
        "material_price_TPU": 8,
        "loss_factor": 1.08,
        "process_fee_per_piece": 120,
        "mold_simple": 1500000,
        "mold_standard": 4000000,
        "mold_precision": 8000000,
        "mold_hotrunner": 12000000,
        "mold_slider": 10000000,
        "packaging_per_piece": 200,
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


def calc_injection(inputs, params):
    material = inputs.get("material", "ABS")
    weight = _to_number(inputs.get("product_weight_g"), 0)
    cavity = max(1, _int(inputs.get("cavity"), 1))
    quantity = max(1, _int(inputs.get("quantity"), 1))
    mold_type = inputs.get("mold_type", "standard")
    packaging = bool(inputs.get("packaging"))

    material_unit = params.get(f"material_price_{material}", params.get("material_price_ABS", 3))
    loss = params.get("loss_factor", 1.08)
    material_cost = weight * material_unit * loss
    process_fee = params.get("process_fee_per_piece", 120) / cavity
    packaging_fee = params.get("packaging_per_piece", 200) if packaging else 0
    mold_fee = params.get(f"mold_{mold_type}", params.get("mold_standard", 4000000))

    unit_price = round(material_cost + process_fee + packaging_fee)
    total = round(unit_price * quantity + mold_fee)
    breakdown = [
        {"label": "单件材料费", "amount": round(material_cost)},
        {"label": "单件加工费", "amount": round(process_fee)},
        {"label": "单件包装费", "amount": round(packaging_fee)},
        {"label": "模具费用", "amount": round(mold_fee)},
    ]
    return {
        "unit_price": unit_price,
        "mold_fee": round(mold_fee),
        "quantity": quantity,
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


def calc_pcb(inputs, params):
    layers = max(1, _int(inputs.get("layers"), 2))
    breakdown = [
        {"label": "原理图设计", "amount": round(params.get("schematic_fee", 0))},
        {"label": "PCB Layout", "amount": round(params.get("layout_fee_per_layer", 0) * layers)},
        {"label": "打样费", "amount": round(params.get("prototype_fee", 0))},
    ]
    if inputs.get("need_smt"):
        breakdown.append({"label": "SMT 费用", "amount": round(params.get("smt_fee", 0))})
    if inputs.get("need_bom"):
        breakdown.append({"label": "BOM 采购", "amount": round(params.get("bom_fee", 0))})
    if inputs.get("need_test"):
        breakdown.append({"label": "测试费用", "amount": round(params.get("test_fee", 0))})
    total = sum(item["amount"] for item in breakdown)
    return {"unit_price": total, "mold_fee": 0, "quantity": 1, "total": total, "breakdown": breakdown}


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


CALCULATORS = {
    "injection": calc_injection,
    "print3d": calc_print3d,
    "pcb": calc_pcb,
    "software": calc_software,
    "ic": calc_ic,
}


def calculate(quote_type, inputs, param_overrides=None):
    if quote_type not in CALCULATORS:
        raise ValueError("unsupported quote type")
    params = build_param_map(quote_type, param_overrides)
    return CALCULATORS[quote_type](inputs or {}, params)
