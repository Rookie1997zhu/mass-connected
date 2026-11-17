"""SMT 工艺费参数默认值（对齐 exports/jlc_smt_calc/rates/rates.json）。"""

SMT_PARAM_META = {
    "pad_fee_per_joint": ("贴片焊点单价", "RMB/焊点"),
    "manual_pad_fee_per_joint": ("手工焊点单价", "RMB/焊点"),
    "manual_project_fee_if_plugin": ("有插件时手工工程费", "RMB"),
    "package_base": ("标准型包装费基数", "RMB"),
    "package_area_qty_rate": ("标准型包装面积数量系数", "RMB/(cm²·pcs)"),
    "plate_change_per_type": ("计入合计的换料费/种类", "RMB"),
    "change_materiel_per_type_economic": ("经济型换料展示单价/种类", "RMB"),
    "change_materiel_per_type_standard": ("标准型换料展示单价/种类", "RMB"),
    "project_fee_economic_T": ("经济型工程费(单面)", "RMB"),
    "project_fee_standard_T": ("标准型工程费(单面)", "RMB"),
    "project_fee_standard_TB": ("标准型工程费(双面)", "RMB"),
    "steel_fee_economic": ("经济型钢网费", "RMB"),
    "steel_fee_standard_T": ("标准型钢网费(单面)", "RMB"),
    "steel_fee_standard_TB": ("标准型钢网费(双面)", "RMB"),
    "min_single_piece_processing_fee": ("单片加工费下限(保留)", "RMB"),
    "rmb_to_krw": ("RMB→KRW 展示汇率", "KRW/RMB"),
}

SMT_PARAM_DEFAULTS = {
    "pad_fee_per_joint": 0.01,
    "manual_pad_fee_per_joint": 0.1,
    "manual_project_fee_if_plugin": 20.0,
    "package_base": 3.0,
    "package_area_qty_rate": 0.0002,
    "plate_change_per_type": 5.0,
    "change_materiel_per_type_economic": 20.0,
    "change_materiel_per_type_standard": 8.0,
    "project_fee_economic_T": 50.0,
    "project_fee_standard_T": 150.0,
    "project_fee_standard_TB": 300.0,
    "steel_fee_economic": 0.0,
    "steel_fee_standard_T": 50.0,
    "steel_fee_standard_TB": 100.0,
    "min_single_piece_processing_fee": 2.9,
    "rmb_to_krw": 226,
}
