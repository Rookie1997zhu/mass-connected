"""计算引擎共享工具：默认参数、数值转换、材料规范化与错误类。"""

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
        "pricing_mode": 0,
        "base_cost": 0,
        "electricity_rate_per_kwh": 150,
        "printer_power_watts": 1000,
        "depreciation_per_hour": 5000,
        "other_costs_per_print": 0,
        "gst_rate": 0,
        "default_infill": 20,
        "slicer_timeout_seconds": 300,
        "max_file_size_mb": 30,
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
