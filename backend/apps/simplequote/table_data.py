"""QuoteTable 默认 seed 数据（来自 project/new 文档）。"""

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

# PCBA 计分表（封装 → 计分，tech: smt|dip）
PCBA_COMPONENT_SCORES = [
    {"package": "0201", "tech": "smt", "score": 2, "category": "CHIP"},
    {"package": "0402", "tech": "smt", "score": 1, "category": "CHIP"},
    {"package": "0603", "tech": "smt", "score": 1, "category": "CHIP"},
    {"package": "0805", "tech": "smt", "score": 1, "category": "CHIP"},
    {"package": "1206", "tech": "smt", "score": 1, "category": "CHIP"},
    {"package": "2010", "tech": "smt", "score": 2, "category": "CHIP"},
    {"package": "1812", "tech": "smt", "score": 2, "category": "CHIP"},
    {"package": "2512", "tech": "smt", "score": 2, "category": "CHIP"},
    {"package": "2835", "tech": "smt", "score": 1, "category": "LED"},
    {"package": "5050", "tech": "smt", "score": 2, "category": "LED"},
    {"package": "SOT-23", "tech": "smt", "score": 1.5, "category": "TRANSISTOR"},
    {"package": "SOP-8", "tech": "smt", "score": 2, "category": "IC"},
    {"package": "SOP-16", "tech": "smt", "score": 4, "category": "IC"},
    {"package": "QFN-16", "tech": "smt", "score": 5, "category": "IC"},
    {"package": "QFN-24", "tech": "smt", "score": 8, "category": "IC"},
    {"package": "CONN-2-10", "tech": "smt", "score": 4, "category": "CONNECTOR"},
    {"package": "WIRE-2.5x3", "tech": "dip", "score": 1, "category": "WIRE"},
    {"package": "CAP-2PIN", "tech": "dip", "score": 1, "category": "CAP"},
    {"package": "TRANS-2PIN", "tech": "dip", "score": 4, "category": "TRANSISTOR"},
    {"package": "FUSE-2PIN", "tech": "dip", "score": 2, "category": "FUSE"},
    {"package": "DIP-CONN-2-10", "tech": "dip", "score": 4, "category": "CONNECTOR"},
]

# PCB 开发基础定价（A/B 类）
PCB_BASE_PRICING = [
    {"no": 1, "group": "A", "days": 7, "label_ko": "简单 PCB 开发", "label_zh": "简单 PCB 开发", "base_fee_krw": 250000},
    {"no": 2, "group": "A", "days": 14, "label_ko": "需元器件开发的 PCB", "label_zh": "需元器件开发的 PCB", "base_fee_krw": 335000},
    {"no": 3, "group": "A", "days": 16, "label_ko": "需分析的 PCB 开发(220V KC)", "label_zh": "需分析的 PCB 开发", "base_fee_krw": 500000},
    {"no": 4, "group": "A", "days": 14, "label_ko": "简单程序 PCB 开发", "label_zh": "简单程序 PCB 开发", "base_fee_krw": 335000},
    {"no": 5, "group": "A", "days": 16, "label_ko": "传感+程序 PCB", "label_zh": "传感+程序 PCB", "base_fee_krw": 400000},
    {"no": 6, "group": "A", "days": 16, "label_ko": "含遥控器程序 PCB", "label_zh": "含遥控器程序 PCB", "base_fee_krw": 555000},
    {"no": 7, "group": "A", "days": 45, "label_ko": "复杂 MCU 产品(中国)", "label_zh": "复杂 MCU 产品(中国)", "base_fee_krw": 2000000},
    {"no": 8, "group": "A", "days": 45, "label_ko": "复杂 MCU 产品+通信(中国)", "label_zh": "复杂 MCU 产品+通信", "base_fee_krw": 3000000},
    {"no": 9, "group": "B", "days": 90, "label_ko": "硬件+App(中国)", "label_zh": "硬件+App(中国)", "base_fee_krw": 3000000},
    {"no": 10, "group": "B", "days": 60, "label_ko": "硬件+App(韩国)", "label_zh": "硬件+App(韩国)", "base_fee_krw": 10000000},
]

# PCB 服务费用
PCB_SERVICES = [
    {"no": 1, "category": "doc", "days": 7, "label_zh": "PCB 元件布局及版图/基本测试报告", "fee_krw": 300000},
    {"no": 2, "category": "doc", "days": 14, "label_zh": "开发资料原件(Gerber/电路图/BOM/SMT坐标)", "fee_krw": 1000000},
    {"no": 3, "category": "doc", "days": 60, "label_zh": "H/W 程序原件(仅韩国开发)", "fee_krw": 3000000},
    {"no": 4, "category": "doc", "days": 60, "label_zh": "App 原件 1 种", "fee_krw": 3000000},
    {"no": 5, "category": "form", "days": 30, "label_zh": "多方协作开发", "fee_krw": 1000000},
    {"no": 6, "category": "form", "days": 14, "label_zh": "客户无法确定产品信息时", "fee_krw": 300000},
    {"no": 7, "category": "form", "days": 30, "label_zh": "提案书/技术文档参与", "fee_krw": 2000000},
    {"no": 8, "category": "form", "days": 90, "label_zh": "提案书撰写及发表参与", "fee_krw": 5000000},
    {"no": 9, "category": "cert", "days": 14, "label_zh": "KC 电磁兼容认证支持", "fee_krw": 1000000},
    {"no": 10, "category": "cert", "days": 90, "label_zh": "KC 安全认证支持", "fee_krw": 1000000},
    {"no": 11, "category": "cert", "days": 90, "label_zh": "UL 安全认证支持", "fee_krw": 1500000},
    {"no": 12, "category": "cert", "days": 90, "label_zh": "TUV/CE 安全认证支持", "fee_krw": 1500000},
]

# PCB 样品权重
PCB_WEIGHTS = [
    {"key": "sample_only", "weight": 2, "label_zh": "仅做样品(不生产)"},
    {"key": "mass_production", "weight": 1, "label_zh": "量产条件开发(默认)"},
    {"key": "pcb_fr4", "weight": 1, "label_zh": "FR-4 1~2层 / 0.8~1.6T"},
    {"key": "pcb_metal", "weight": 1.5, "label_zh": "METAL 1层 / 1~1.6T"},
    {"key": "qty_2", "weight": 1, "label_zh": "样品数量 2 个"},
    {"key": "size_100", "weight": 1, "label_zh": "尺寸 100×100mm 以下"},
    {"key": "size_large", "weight": 1.5, "label_zh": "更大尺寸/特殊 PCB"},
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

PCBA_PARAM_META = {
    "smt_score_price": ("SMT 每分单价", "RMB/分"),
    "dip_score_price": ("DIP 每分单价", "RMB/分"),
    "rmb_to_krw": ("RMB→KRW 展示汇率", "KRW/RMB"),
    "mask_fee": ("钢网费(量产)", "RMB"),
    "smt_test_fee": ("SMT 测试费/PCB", "RMB"),
    "packaging_fee": ("包装费/ARRAY", "RMB"),
    "default_smt_score": ("未知封装 SMT 默认计分", "分"),
    "default_dip_score": ("未知封装 DIP 默认计分", "分"),
}

PCBA_PARAM_DEFAULTS = {
    "smt_score_price": 0.01,
    "dip_score_price": 0.03,
    "rmb_to_krw": 226,
    "mask_fee": 150,
    "smt_test_fee": 0.3,
    "packaging_fee": 0.3,
    "default_smt_score": 2,
    "default_dip_score": 2,
}

PCB_PARAM_META = {
    "ad_discount_rate": ("广告同意折扣率", "rate"),
    "valid_days": ("报价有效期(天)", "day"),
}

PCB_PARAM_DEFAULTS = {
    "ad_discount_rate": 0.10,
    "valid_days": 30,
}

QUOTE_TABLE_SEED = [
    ("shipping", "air_freight_tiers", AIR_FREIGHT_TIERS),
    ("shipping", "lcl_cbm_fees", LCL_CBM_FEES),
    ("pcba", "component_scores", PCBA_COMPONENT_SCORES),
    ("pcb", "base_pricing", PCB_BASE_PRICING),
    ("pcb", "services", PCB_SERVICES),
    ("pcb", "weights", PCB_WEIGHTS),
]
