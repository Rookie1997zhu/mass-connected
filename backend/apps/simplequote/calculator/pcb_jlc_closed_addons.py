"""嘉立创 PCB 已闭合加价（exports/jlc_pcb_quote，2026-11 探针）。

用于校准断言与 process_model 中对应 method；不替换 manufacturing_price_list。
"""

from apps.simplequote.calculator.utils import _int, _to_number

# 阻焊色：基线 10×10cm / 5pcs 锚点相对绿色的固定加价
SOLDER_COLOR_ADDITIVE_CNY = {
    "绿色": 0.0,
    "哑黑色": 0.0,
    "哑黑": 0.0,
    "红色": 30.0,
    "黄色": 30.0,
    "蓝色": 30.0,
    "白色": 30.0,
    "嘉立创紫": 30.0,
}

# 确认生产稿
CONFIRM_FILE_FEE_CNY = {
    "none": 0.0,
    "confirm_none": 0.0,
    "0": 0.0,
    "twice": 3.0,
    "confirm_twice_3": 3.0,
    "1": 3.0,
    "multi": 10.0,
    "confirm_multi_10": 10.0,
    "2": 10.0,
}

# 无铅喷锡：adornputmoney ≈ 30 + 30 × 面积(㎡)
LEAD_FREE_HASL_BASE_CNY = 30.0
LEAD_FREE_HASL_RATE_PER_M2 = 30.0

# 免费表面处理
FREE_SURFACE_FINISH = {"OSP", "无铅OSP", "有铅喷锡"}


def area_m2_from_mm(width_mm, height_mm, quantity):
    w = _to_number(width_mm, 0)
    h = _to_number(height_mm, 0)
    qty = max(0, _int(quantity, 0))
    return (w * h * qty) / 1_000_000.0


def solder_color_delta_cny(color):
    key = str(color or "").strip()
    if key not in SOLDER_COLOR_ADDITIVE_CNY:
        return None
    return SOLDER_COLOR_ADDITIVE_CNY[key]


def confirm_file_fee_cny(value):
    key = str(value if value is not None else "none").strip()
    if key.lower() in ("false", ""):
        key = "none"
    if key.lower() in ("true",):
        key = "twice"
    return CONFIRM_FILE_FEE_CNY.get(key)


def lead_free_hasl_fee_cny(width_mm, height_mm, quantity):
    area = area_m2_from_mm(width_mm, height_mm, quantity)
    return LEAD_FREE_HASL_BASE_CNY + LEAD_FREE_HASL_RATE_PER_M2 * area


def surface_finish_delta_cny(finish, width_mm, height_mm, quantity):
    key = str(finish or "").strip()
    if key in FREE_SURFACE_FINISH:
        return 0.0
    if key == "无铅喷锡":
        return lead_free_hasl_fee_cny(width_mm, height_mm, quantity)
    return None
