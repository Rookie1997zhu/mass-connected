"""参数驱动的简单报价计算引擎。V1 覆盖注塑模具与 3D 打印，其余类型给出基础估算。

所有金额单位默认 KRW，参数可由后台 QuoteParam 覆盖默认值。

本包由原单文件 calculator.py 拆分而来，__init__ 保持向后兼容：所有历史可导入的
公共符号仍可从 apps.simplequote.calculator 直接导入。
"""

from apps.simplequote.calculator.injection import (
    _build_parts,
    _calc_part_unit_price,
    _color_factor,
    _estimate_injection_shipping,
    _shipping_tables,
    calc_injection,
    weight_from_volume,
)
from apps.simplequote.calculator.misc import calc_ic, calc_paper_box, calc_software
from apps.simplequote.calculator.pcb import (
    PCB_QUOTE_RANGE_RATE,
    _apply_pcb_process_model,
    _estimate_pcb_manufacturing,
    _estimate_pcb_manufacturing_by_model,
    _estimate_pcb_v9_material_model,
    _find_base_item,
    _find_pcb_manufacturing_row,
    _match_pcb_process_enabled_zone,
    _match_pcb_risk_zone,
    _median_number,
    _normalize_pcb_material_key,
    _pcb_acceptance_allows_auto_estimate,
    _pcb_manual_display_fields,
    _pcb_manufacturing_meta,
    _pcb_manufacturing_spec,
    _pcb_quantity_band,
    _pcb_quote_range,
    _pcb_v9_segment_key,
    _resolve_pcb_process_spec,
    _to_pcb_bool,
    calc_pcb,
)
from apps.simplequote.calculator.pcba import _calc_sum, _match_score, calc_pcba
from apps.simplequote.calculator.print3d import calc_print3d
from apps.simplequote.calculator.utils import (
    DEFAULT_PARAMS,
    InjectionQuoteError,
    PaperBoxQuoteError,
    PcbaQuoteError,
    PcbQuoteError,
    _int,
    _normalize_material,
    _round4,
    _to_number,
    build_param_map,
)

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
    if quote_type in ("pcba", "pcb", "injection", "print3d"):
        return calc_fn(inputs or {}, params, tables)
    return calc_fn(inputs or {}, params)


__all__ = [
    "DEFAULT_PARAMS",
    "CALCULATORS",
    "calculate",
    "build_param_map",
    "weight_from_volume",
    "calc_injection",
    "calc_print3d",
    "calc_pcba",
    "calc_pcb",
    "calc_software",
    "calc_ic",
    "calc_paper_box",
    "InjectionQuoteError",
    "PcbQuoteError",
    "PcbaQuoteError",
    "PaperBoxQuoteError",
    "_to_number",
    "_int",
    "_normalize_material",
    "_round4",
    "_build_parts",
    "_color_factor",
    "_calc_part_unit_price",
    "_shipping_tables",
    "_estimate_injection_shipping",
    "_calc_sum",
    "_match_score",
    "_find_base_item",
    "_normalize_pcb_material_key",
    "_to_pcb_bool",
    "_pcb_manufacturing_spec",
    "_find_pcb_manufacturing_row",
    "_pcb_manufacturing_meta",
    "_resolve_pcb_process_spec",
    "_apply_pcb_process_model",
    "_match_pcb_process_enabled_zone",
    "_pcb_acceptance_allows_auto_estimate",
    "_pcb_v9_segment_key",
    "_median_number",
    "_pcb_quantity_band",
    "_estimate_pcb_v9_material_model",
    "_estimate_pcb_manufacturing_by_model",
    "_match_pcb_risk_zone",
    "PCB_QUOTE_RANGE_RATE",
    "_pcb_quote_range",
    "_pcb_manual_display_fields",
    "_estimate_pcb_manufacturing",
]
