"""QuoteTable 默认 seed 数据（来自 project/new 文档），聚合各数据域。"""

from apps.simplequote.table_data.pcb import (
    PCB_BASE_PRICING,
    PCB_MANUFACTURING_PRICE_LIST,
    PCB_MANUFACTURING_PRICE_META,
    PCB_SERVICES,
    PCB_WEIGHTS,
)
from apps.simplequote.table_data.pcba import PCBA_COMPONENT_SCORES
from apps.simplequote.table_data.shipping import AIR_FREIGHT_TIERS, LCL_CBM_FEES

QUOTE_TABLE_SEED = [
    ("shipping", "air_freight_tiers", AIR_FREIGHT_TIERS),
    ("shipping", "lcl_cbm_fees", LCL_CBM_FEES),
    ("pcba", "component_scores", PCBA_COMPONENT_SCORES),
    ("pcb", "base_pricing", PCB_BASE_PRICING),
    ("pcb", "services", PCB_SERVICES),
    ("pcb", "weights", PCB_WEIGHTS),
    ("pcb", "manufacturing_price_list", PCB_MANUFACTURING_PRICE_LIST),
    ("pcb", "manufacturing_price_meta", PCB_MANUFACTURING_PRICE_META),
]
