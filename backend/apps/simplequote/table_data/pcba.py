"""PCBA 计分表与参数默认值。"""

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
