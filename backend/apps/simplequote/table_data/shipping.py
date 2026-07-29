"""运输/物流相关默认数据表。"""

# 空运阶梯费率（韩元），weight_min/weight_max 单位 kg
AIR_FREIGHT_TIERS = [
    {"weight_min": 0, "weight_max": 1, "fee_krw": 21000},
    {"weight_min": 1.1, "weight_max": 1.5, "fee_krw": 30000},
    {"weight_min": 1.6, "weight_max": 2, "fee_krw": 30000},
    {"weight_min": 2.1, "weight_max": 2.5, "fee_krw": 35000},
    {"weight_min": 2.6, "weight_max": 3, "fee_krw": 39000},
    {"weight_min": 3.1, "weight_max": 3.5, "fee_krw": 44000},
    {"weight_min": 4.1, "weight_max": 4.5, "fee_krw": 53000},
    {"weight_min": 5.1, "weight_max": 5.5, "fee_krw": 62000},
    {"weight_min": 9.1, "weight_max": 9.5, "fee_krw": 98000},
    {"weight_min": 9.6, "weight_max": 10, "fee_krw": 102000},
    {"weight_min": 14.6, "weight_max": 15, "fee_krw": 147000},
    {"weight_min": 19.6, "weight_max": 20, "fee_krw": 191000},
    {"weight_min": 24.6, "weight_max": 25, "fee_krw": 236000},
    {"weight_min": 29.6, "weight_max": 30, "fee_krw": 281000},
    {"weight_min": 39.6, "weight_max": 40, "fee_krw": 363000},
    {"weight_min": 49.6, "weight_max": 50, "fee_krw": 453000},
]

# 海运 LCL 无电池 CBM 区间（国际综合物流）
LCL_CBM_FEES = [
    {"cbm_min": 0, "cbm_max": 0.50, "handling_krw": 10000, "bonded_krw": 8400, "port_krw": 12100, "line_sur_usd": 2.4},
    {"cbm_min": 0.51, "cbm_max": 0.75, "handling_krw": 10000, "bonded_krw": 10540, "port_krw": 16900, "line_sur_usd": 4.8},
    {"cbm_min": 0.76, "cbm_max": 0.90, "handling_krw": 10000, "bonded_krw": 12680, "port_krw": 21700, "line_sur_usd": 4.8},
    {"cbm_min": 0.91, "cbm_max": 1.10, "handling_krw": 12000, "bonded_krw": 14820, "port_krw": 26500, "line_sur_usd": 9.8},
    {"cbm_min": 1.11, "cbm_max": 1.30, "handling_krw": 14000, "bonded_krw": 15890, "port_krw": 28900, "line_sur_usd": 9.8},
    {"cbm_min": 1.31, "cbm_max": 1.50, "handling_krw": 20000, "bonded_krw": 19100, "port_krw": 36100, "line_sur_usd": 9.8},
    {"cbm_min": 1.51, "cbm_max": 1.75, "handling_krw": 20000, "bonded_krw": 22824, "port_krw": 40900, "line_sur_usd": 14.8},
    {"cbm_min": 1.76, "cbm_max": 2.00, "handling_krw": 20000, "bonded_krw": 26548, "port_krw": 45700, "line_sur_usd": 14.8},
    {"cbm_min": 2.01, "cbm_max": 2.40, "handling_krw": 24000, "bonded_krw": 30946, "port_krw": 52900, "line_sur_usd": 20.8},
    {"cbm_min": 2.41, "cbm_max": 3.00, "handling_krw": 30000, "bonded_krw": 37286, "port_krw": 64900, "line_sur_usd": 28.4},
    {"cbm_min": 3.01, "cbm_max": 5.00, "handling_krw": 36000, "bonded_krw": 71970, "port_krw": 130300, "line_sur_usd": 53.7},
    {"cbm_min": 5.01, "cbm_max": 7.00, "handling_krw": 36000, "bonded_krw": 94070, "port_krw": 194900, "line_sur_usd": 77.58},
    {"cbm_min": 7.01, "cbm_max": 999, "handling_krw": 36000, "bonded_krw": 144770, "port_krw": 343100, "line_sur_usd": 119.27},
]

SHIPPING_PARAM_META = {
    "usd_to_krw": ("USD→KRW 汇率", "KRW/USD"),
    "cny_to_krw": ("CNY→KRW 汇率", "KRW/CNY"),
    "usd_to_krw_battery": ("含电池 LCL USD→KRW", "KRW/USD"),
    "lcl_rate_4day": ("LCL 无电池 4日 $/R/T", "USD/R/T"),
    "lcl_rate_5day": ("LCL 无电池 5日 $/R/T", "USD/R/T"),
    "lcl_min_4day": ("LCL 无电池 4日最低运费", "USD"),
    "lcl_min_5day": ("LCL 无电池 5日最低运费", "USD"),
    "battery_rate_4day": ("LCL 含电池 4日 $/CBM", "USD/CBM"),
    "battery_rate_5day": ("LCL 含电池 5日 $/CBM", "USD/CBM"),
    "battery_min_cbm": ("含电池最低计费 CBM", "CBM"),
    "battery_overweight_4day": ("含电池超重 4日 ¥/kg", "CNY/kg"),
    "battery_overweight_5day": ("含电池超重 5日 ¥/kg", "CNY/kg"),
    "pcb_shipping_under_1kg": ("PCB 配送 ≤1kg 固定费", "KRW"),
    "pcb_shipping_per_kg": ("PCB 配送 ≥2kg 单价", "KRW/kg"),
}

SHIPPING_PARAM_DEFAULTS = {
    "usd_to_krw": 1580,
    "cny_to_krw": 232.4,
    "usd_to_krw_battery": 1500,
    "lcl_rate_4day": 55,
    "lcl_rate_5day": 50,
    "lcl_min_4day": 30,
    "lcl_min_5day": 25,
    "battery_rate_4day": 85,
    "battery_rate_5day": 75,
    "battery_min_cbm": 1,
    "battery_overweight_4day": 1.5,
    "battery_overweight_5day": 1.2,
    "pcb_shipping_under_1kg": 24000,
    "pcb_shipping_per_kg": 11600,
}
