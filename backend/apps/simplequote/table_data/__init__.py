"""QuoteTable 默认 seed 数据（来自 project/new 文档）。

本包由原单文件 table_data.py 拆分而来，__init__ 保持向后兼容：所有历史可导入的
数据表与参数默认值仍可从 apps.simplequote.table_data 直接导入。
"""

from apps.simplequote.table_data.pcb import (
    PCB_BASE_PRICING,
    PCB_MANUFACTURING_PRICE_LIST,
    PCB_MANUFACTURING_PRICE_META,
    PCB_PARAM_DEFAULTS,
    PCB_PARAM_META,
    PCB_SERVICES,
    PCB_WEIGHTS,
)
from apps.simplequote.table_data.pcba import (
    PCBA_COMPONENT_SCORES,
    PCBA_PARAM_DEFAULTS,
    PCBA_PARAM_META,
)
from apps.simplequote.table_data.seed import QUOTE_TABLE_SEED
from apps.simplequote.table_data.shipping import (
    AIR_FREIGHT_TIERS,
    LCL_CBM_FEES,
    SHIPPING_PARAM_DEFAULTS,
    SHIPPING_PARAM_META,
)

__all__ = [
    "AIR_FREIGHT_TIERS",
    "LCL_CBM_FEES",
    "SHIPPING_PARAM_META",
    "SHIPPING_PARAM_DEFAULTS",
    "PCBA_COMPONENT_SCORES",
    "PCBA_PARAM_META",
    "PCBA_PARAM_DEFAULTS",
    "PCB_BASE_PRICING",
    "PCB_SERVICES",
    "PCB_WEIGHTS",
    "PCB_MANUFACTURING_PRICE_LIST",
    "PCB_MANUFACTURING_PRICE_META",
    "PCB_PARAM_META",
    "PCB_PARAM_DEFAULTS",
    "QUOTE_TABLE_SEED",
]
