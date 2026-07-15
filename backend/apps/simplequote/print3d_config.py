"""Build and validate print3d pricing/slicing config from QuoteParam + QuoteTable."""
from __future__ import annotations

from copy import deepcopy
from typing import Any

from apps.simplequote.calculator import _to_number, build_param_map
from apps.simplequote.models import QuoteParam, QuoteTable

DEFAULT_MATERIALS = [
    {
        "key": "PLA",
        "name": "PLA",
        "enabled": True,
        "density_g_cm3": 1.24,
        "price_per_kg": 60000,
        "per_gram_price": 60,
        "bed_temp": 55,
        "extruder_temp": 215,
        "perimeter_speed": 100,
        "infill_speed": 180,
        "solid_infill_speed": 160,
    },
    {
        "key": "ABS",
        "name": "ABS",
        "enabled": True,
        "density_g_cm3": 1.04,
        "price_per_kg": 70000,
        "per_gram_price": 70,
        "bed_temp": 90,
        "extruder_temp": 245,
        "perimeter_speed": 80,
        "infill_speed": 160,
        "solid_infill_speed": 140,
    },
    {
        "key": "PETG",
        "name": "PETG",
        "enabled": True,
        "density_g_cm3": 1.27,
        "price_per_kg": 80000,
        "per_gram_price": 80,
        "bed_temp": 70,
        "extruder_temp": 240,
        "perimeter_speed": 70,
        "infill_speed": 150,
        "solid_infill_speed": 120,
    },
    {
        "key": "TPU",
        "name": "TPU",
        "enabled": True,
        "density_g_cm3": 1.21,
        "price_per_kg": 160000,
        "per_gram_price": 160,
        "bed_temp": 60,
        "extruder_temp": 230,
        "perimeter_speed": 30,
        "infill_speed": 40,
        "solid_infill_speed": 35,
    },
    {
        "key": "Nylon",
        "name": "Nylon",
        "enabled": True,
        "density_g_cm3": 1.14,
        "price_per_kg": 180000,
        "per_gram_price": 180,
        "bed_temp": 80,
        "extruder_temp": 250,
        "perimeter_speed": 60,
        "infill_speed": 100,
        "solid_infill_speed": 80,
    },
    {
        "key": "Resin",
        "name": "Resin",
        "enabled": True,
        "density_g_cm3": 1.10,
        "price_per_kg": 150000,
        "per_gram_price": 150,
        "bed_temp": 0,
        "extruder_temp": 0,
        "perimeter_speed": 0,
        "infill_speed": 0,
        "solid_infill_speed": 0,
    },
]

DEFAULT_PRINTERS = [
    {
        "key": "prusa_mk3s",
        "name": "Prusa i3 MK3S+",
        "enabled": True,
        "is_default": True,
        "bed_size_mm": [250, 210, 210],
        "markup_multiplier": 1.3,
    },
    {
        "key": "ender3_v2",
        "name": "Creality Ender 3 V2",
        "enabled": True,
        "bed_size_mm": [220, 220, 250],
        "markup_multiplier": 1.25,
    },
    {
        "key": "bambu_x1",
        "name": "Bambu Lab X1 Carbon",
        "enabled": True,
        "bed_size_mm": [256, 256, 256],
        "markup_multiplier": 1.4,
    },
]

DEFAULT_QUALITIES = [
    {"key": "draft", "name": "Draft", "layer_height": 0.3, "enabled": True},
    {"key": "standard", "name": "Standard", "layer_height": 0.2, "enabled": True},
    {"key": "fine", "name": "Fine", "layer_height": 0.15, "enabled": True},
    {"key": "ultra_fine", "name": "Ultra Fine", "layer_height": 0.1, "enabled": True},
]

DEFAULT_POSTS = [
    {"key": "none", "name": "None", "price": 0, "enabled": True},
    {"key": "sanding", "name": "Sanding", "price": 3000, "enabled": True},
    {"key": "paint", "name": "Paint", "price": 8000, "enabled": True},
    {"key": "polishing", "name": "Polishing", "price": 5000, "enabled": False},
]

PRINT3D_PARAM_DEFAULTS = {
    "pricing_mode": 0,  # 0=custom cost+, 1=per_gram (stored as Decimal-friendly)
    "base_cost": 0,
    "electricity_rate_per_kwh": 150,
    "printer_power_watts": 1000,
    "depreciation_per_hour": 5000,
    "other_costs_per_print": 0,
    "gst_rate": 0,
    "loss_factor": 1.1,
    "rush_factor": 1.3,
    "machine_hour_rate": 5000,
    "default_infill": 20,
    "slicer_timeout_seconds": 300,
    "max_file_size_mb": 30,
    "material_price_PLA": 60,
    "material_price_ABS": 70,
    "material_price_PETG": 80,
    "material_price_Resin": 150,
    "material_price_Nylon": 180,
    "material_price_TPU": 160,
    "post_none": 0,
    "post_sanding": 3000,
    "post_paint": 8000,
}

PRINT3D_PARAM_META = {
    "pricing_mode": ("计价模式(0=成本累加,1=按克)", ""),
    "base_cost": ("基础费用", "KRW"),
    "electricity_rate_per_kwh": ("电费单价", "KRW/kWh"),
    "printer_power_watts": ("打印机功率", "W"),
    "depreciation_per_hour": ("设备折旧/时", "KRW/h"),
    "other_costs_per_print": ("其他成本/件", "KRW"),
    "gst_rate": ("税率(小数)", ""),
    "loss_factor": ("材料损耗系数", ""),
    "rush_factor": ("加急系数", ""),
    "machine_hour_rate": ("机时费率(兼容)", "KRW/h"),
    "default_infill": ("默认填充率", "%"),
    "slicer_timeout_seconds": ("切片超时", "s"),
    "max_file_size_mb": ("上传大小上限", "MB"),
    "material_price_PLA": ("PLA 单价(兼容)", "KRW/g"),
    "material_price_ABS": ("ABS 单价(兼容)", "KRW/g"),
    "material_price_PETG": ("PETG 单价(兼容)", "KRW/g"),
    "material_price_Resin": ("Resin 单价(兼容)", "KRW/g"),
    "material_price_Nylon": ("Nylon 单价(兼容)", "KRW/g"),
    "material_price_TPU": ("TPU 单价(兼容)", "KRW/g"),
    "post_none": ("后处理:无", "KRW"),
    "post_sanding": ("后处理:打磨", "KRW"),
    "post_paint": ("后处理:喷漆", "KRW"),
}


def _param_overrides() -> dict[str, Any]:
    overrides = {}
    for param in QuoteParam.objects.filter(quote_type="print3d", is_active=True):
        overrides[param.param_key] = param.value
    return overrides


def _table_rows(table_key: str, defaults: list[dict]) -> list[dict]:
    table = QuoteTable.objects.filter(
        quote_type="print3d", table_key=table_key, is_active=True
    ).first()
    if table and isinstance(table.rows, list) and table.rows:
        return deepcopy(table.rows)
    return deepcopy(defaults)


def pricing_mode_name(params: dict[str, Any]) -> str:
    mode = params.get("pricing_mode", 0)
    if mode == 1 or mode == "1" or mode == "per_gram":
        return "per_gram"
    return "custom"


def build_print3d_config() -> dict[str, Any]:
    params = build_param_map("print3d", _param_overrides())
    # Merge scalar defaults not in DEFAULT_PARAMS print3d key set
    for key, value in PRINT3D_PARAM_DEFAULTS.items():
        params.setdefault(key, value)
    materials = [m for m in _table_rows("materials", DEFAULT_MATERIALS) if m.get("enabled", True)]
    printers = [p for p in _table_rows("printers", DEFAULT_PRINTERS) if p.get("enabled", True)]
    qualities = [q for q in _table_rows("print_qualities", DEFAULT_QUALITIES) if q.get("enabled", True)]
    posts = [p for p in _table_rows("post_processing", DEFAULT_POSTS) if p.get("enabled", True)]
    return {
        "params": params,
        "materials": materials,
        "printers": printers,
        "qualities": qualities,
        "post_processing": posts,
        "pricing_mode": pricing_mode_name(params),
        "infill": {
            "min": 5,
            "max": 100,
            "default": int(_to_number(params.get("default_infill"), 20)),
        },
        "max_file_size_mb": int(_to_number(params.get("max_file_size_mb"), 30)),
        "slicer_timeout_seconds": int(_to_number(params.get("slicer_timeout_seconds"), 300)),
    }


def find_by_key(items: list[dict], key: str) -> dict | None:
    key_norm = str(key or "").strip()
    for item in items:
        if str(item.get("key", "")).strip() == key_norm:
            return item
    # case-insensitive fallback
    key_lower = key_norm.lower()
    for item in items:
        if str(item.get("key", "")).strip().lower() == key_lower:
            return item
    return None


def default_printer(printers: list[dict]) -> dict | None:
    """管理端指定的默认打印机；未指定时取第一台启用的。"""
    if not printers:
        return None
    for item in printers:
        if item.get("is_default"):
            return item
    return printers[0]


def build_job_config_snapshot(inputs: dict[str, Any]) -> dict[str, Any]:
    """Freeze enabled catalogs + chosen option details for a slice job."""
    cfg = build_print3d_config()
    material = find_by_key(cfg["materials"], inputs.get("material", "PLA"))
    # 打印机不再由会员选择；仅管理端试算可显式指定，否则用默认打印机
    requested_printer = str(inputs.get("printer") or "").strip()
    printer = find_by_key(cfg["printers"], requested_printer) if requested_printer else None
    printer = printer or default_printer(cfg["printers"])
    quality = find_by_key(cfg["qualities"], inputs.get("quality", "standard"))
    post = find_by_key(cfg["post_processing"], inputs.get("post_process", "none"))
    if not material:
        raise ValueError("无效材料")
    if not printer:
        raise ValueError("无可用打印机，请联系管理员")
    if not quality:
        raise ValueError("无效打印质量")
    infill = int(_to_number(inputs.get("infill_density"), cfg["infill"]["default"]))
    if infill < 5 or infill > 100:
        raise ValueError("填充率须在 5–100 之间")
    return {
        "pricing_mode": cfg["pricing_mode"],
        "params": cfg["params"],
        "material": material,
        "printer": printer,
        "quality": quality,
        "post_processing": post or {"key": "none", "name": "None", "price": 0},
        "infill_density": infill,
        "support": bool(inputs.get("support")),
        "quantity": max(1, int(_to_number(inputs.get("quantity"), 1))),
        "rush": bool(inputs.get("rush")),
        "slicer_timeout_seconds": cfg["slicer_timeout_seconds"],
    }


def slice_params_from_snapshot(snapshot: dict[str, Any]) -> dict[str, Any]:
    material = snapshot.get("material") or {}
    quality = snapshot.get("quality") or {}
    return {
        "layer_height": _to_number(quality.get("layer_height"), 0.2),
        "infill_density": int(_to_number(snapshot.get("infill_density"), 20)),
        "bed_temp": int(_to_number(material.get("bed_temp"), 60)),
        "extruder_temp": int(_to_number(material.get("extruder_temp"), 210)),
        "perimeter_speed": int(_to_number(material.get("perimeter_speed"), 60)),
        "infill_speed": int(_to_number(material.get("infill_speed"), 80)),
        "solid_infill_speed": int(_to_number(material.get("solid_infill_speed"), 60)),
        "support": bool(snapshot.get("support")),
    }


def public_options_payload() -> dict[str, Any]:
    """会员端选项；打印机由管理端配置默认值，不再下发给会员选择。"""
    cfg = build_print3d_config()
    return {
        "materials": [
            {"key": m["key"], "name": m.get("name", m["key"])} for m in cfg["materials"]
        ],
        "qualities": [
            {
                "key": q["key"],
                "name": q.get("name", q["key"]),
                "layer_height": q.get("layer_height"),
            }
            for q in cfg["qualities"]
        ],
        "post_processing": [
            {"key": p["key"], "name": p.get("name", p["key"]), "price": p.get("price", 0)}
            for p in cfg["post_processing"]
        ],
        "infill": cfg["infill"],
        "pricing_mode": cfg["pricing_mode"],
        "max_file_size_mb": cfg["max_file_size_mb"],
    }


def admin_config_payload() -> dict[str, Any]:
    cfg = build_print3d_config()
    params = {
        key: cfg["params"].get(key, PRINT3D_PARAM_DEFAULTS.get(key))
        for key in PRINT3D_PARAM_DEFAULTS
    }
    # Coerce Decimal / string pricing_mode to int for admin select binding
    try:
        params["pricing_mode"] = int(float(params.get("pricing_mode") or 0))
    except (TypeError, ValueError):
        params["pricing_mode"] = 0
    return {
        "params": params,
        "param_meta": PRINT3D_PARAM_META,
        "materials": _table_rows("materials", DEFAULT_MATERIALS),
        "printers": _table_rows("printers", DEFAULT_PRINTERS),
        "qualities": _table_rows("print_qualities", DEFAULT_QUALITIES),
        "post_processing": _table_rows("post_processing", DEFAULT_POSTS),
        "pricing_mode": cfg["pricing_mode"],
    }
