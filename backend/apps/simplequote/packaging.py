"""FEFCO 纸盒展开尺寸与面积计算（2D 参数化，权威后端公式）。

支持 P0 盒型：0201 / 0427 / 0713 / 0716。
"""

from decimal import Decimal

from apps.simplequote.fefco_catalog import get_box_template

MM_TO_M = 0.001
DEFAULT_GLUE_TAB_MM = 25.0
MIN_DIM_MM = 10.0
MAX_DIM_MM = 2000.0


class PaperBoxGeometryError(ValueError):
    """纸盒几何输入错误。"""


def _to_float(value, default=0.0):
    try:
        if isinstance(value, Decimal):
            return float(value)
        return float(value)
    except (TypeError, ValueError):
        return default


def _board_allowances(thickness_mm):
    """瓦楞纸板制造↔内/外尺寸容差（B 楞 3mm 参考：内 -4/-4/-8，外 +2/+2/+4）。"""
    t = max(0.1, _to_float(thickness_mm, 1.5))
    return {
        "internal_lw": (4.0 / 3.0) * t,
        "internal_h": (8.0 / 3.0) * t,
        "external_lw": (2.0 / 3.0) * t,
        "external_h": (4.0 / 3.0) * t,
    }


def manufacturing_dims(length_mm, width_mm, height_mm, thickness_mm, dimension_type):
    """将用户输入尺寸换算为制造尺寸（mm）。

    dimension_type: internal | external | manufacturing
    """
    l, w, h, t = (
        _to_float(length_mm),
        _to_float(width_mm),
        _to_float(height_mm),
        max(0.1, _to_float(thickness_mm, 1.5)),
    )
    allow = _board_allowances(t)
    dim_type = str(dimension_type or "internal").lower()
    if dim_type == "manufacturing":
        return l, w, h, t
    if dim_type == "internal":
        return (
            l + allow["internal_lw"],
            w + allow["internal_lw"],
            h + allow["internal_h"],
            t,
        )
    if dim_type == "external":
        return (
            max(MIN_DIM_MM, l - allow["external_lw"]),
            max(MIN_DIM_MM, w - allow["external_lw"]),
            max(MIN_DIM_MM, h - allow["external_h"]),
            t,
        )
    return l, w, h, t


def size_triple_from_manufacturing(length_mm, width_mm, height_mm, thickness_mm):
    """由制造尺寸推算内/外尺寸。"""
    allow = _board_allowances(thickness_mm)
    return {
        "internal": {
            "length_mm": round(length_mm - allow["internal_lw"], 2),
            "width_mm": round(width_mm - allow["internal_lw"], 2),
            "height_mm": round(height_mm - allow["internal_h"], 2),
        },
        "external": {
            "length_mm": round(length_mm + allow["external_lw"], 2),
            "width_mm": round(width_mm + allow["external_lw"], 2),
            "height_mm": round(height_mm + allow["external_h"], 2),
        },
    }


def _validate_dims(l, w, h):
    if l < MIN_DIM_MM or w < MIN_DIM_MM or h < MIN_DIM_MM:
        raise PaperBoxGeometryError("长宽高不能小于 10mm")
    if l > MAX_DIM_MM or w > MAX_DIM_MM or h > MAX_DIM_MM:
        raise PaperBoxGeometryError("长宽高不能超过 2000mm")


def _build_result(box_code, l, w, h, t, glue_tab, blank_width_mm, blank_height_mm):
    unfold_area_m2 = (blank_width_mm * MM_TO_M) * (blank_height_mm * MM_TO_M)
    return {
        "box_code": box_code,
        "manufacturing_length_mm": round(l, 2),
        "manufacturing_width_mm": round(w, 2),
        "manufacturing_height_mm": round(h, 2),
        "thickness_mm": round(t, 2),
        "glue_tab_mm": round(glue_tab, 2),
        "blank_width_mm": round(blank_width_mm, 2),
        "blank_height_mm": round(blank_height_mm, 2),
        "unfold_area_m2": round(unfold_area_m2, 6),
    }


def unfold_size_0201(length_mm, width_mm, height_mm, thickness_mm=1.5, dimension_type="internal", glue_tab_mm=None):
    """FEFCO 0201 展开 blank 尺寸与面积。

    标准 RSC 公式：
    - 展开宽 = 2(L + W) + 接头舌
    - 展开高 = H + W
    """
    l, w, h, t = manufacturing_dims(length_mm, width_mm, height_mm, thickness_mm, dimension_type)
    _validate_dims(l, w, h)

    glue_tab = _to_float(glue_tab_mm, DEFAULT_GLUE_TAB_MM)
    glue_tab = max(15.0, glue_tab)

    blank_width_mm = 2 * (l + w) + glue_tab
    blank_height_mm = h + w
    return _build_result("0201", l, w, h, t, glue_tab, blank_width_mm, blank_height_mm)


def unfold_size_0427(length_mm, width_mm, height_mm, thickness_mm=1.5, dimension_type="internal", glue_tab_mm=None):
    """FEFCO 0427 翻盖自锁飞机盒（RETF / 文件夹式）。

    展开宽 = L + 2W（左右侧墙各 W）
    展开高 = 2H + 2W + 插舌高（≈ H - 厚度）
    """
    l, w, h, t = manufacturing_dims(length_mm, width_mm, height_mm, thickness_mm, dimension_type)
    _validate_dims(l, w, h)
    glue_tab = max(15.0, _to_float(glue_tab_mm, DEFAULT_GLUE_TAB_MM))
    tuck_height = max(h - t, h * 0.9, 12.0)
    blank_width_mm = l + 2 * w
    blank_height_mm = 2 * h + 2 * w + tuck_height
    return _build_result("0427", l, w, h, t, glue_tab, blank_width_mm, blank_height_mm)


def unfold_size_0713(length_mm, width_mm, height_mm, thickness_mm=1.5, dimension_type="internal", glue_tab_mm=None):
    """FEFCO 0713 插舌盒（Tuck end carton）。

    展开宽 = 2(L + W) + 接头舌
    展开高 = 2H + W
    """
    l, w, h, t = manufacturing_dims(length_mm, width_mm, height_mm, thickness_mm, dimension_type)
    _validate_dims(l, w, h)
    glue_tab = max(15.0, _to_float(glue_tab_mm, DEFAULT_GLUE_TAB_MM))
    blank_width_mm = 2 * (l + w) + glue_tab
    blank_height_mm = 2 * h + w
    return _build_result("0713", l, w, h, t, glue_tab, blank_width_mm, blank_height_mm)


def unfold_size_0716(length_mm, width_mm, height_mm, thickness_mm=1.5, dimension_type="internal", glue_tab_mm=None):
    """FEFCO 0716 自动锁底盒。

    展开宽 = 2(L + W) + 接头舌
    展开高 = 2H + 1.25W（含锁底结构余量）
    """
    l, w, h, t = manufacturing_dims(length_mm, width_mm, height_mm, thickness_mm, dimension_type)
    _validate_dims(l, w, h)
    glue_tab = max(15.0, _to_float(glue_tab_mm, DEFAULT_GLUE_TAB_MM))
    blank_width_mm = 2 * (l + w) + glue_tab
    blank_height_mm = 2 * h + 1.25 * w
    return _build_result("0716", l, w, h, t, glue_tab, blank_width_mm, blank_height_mm)


UNFOLD_HANDLERS = {
    "0201": unfold_size_0201,
    "0427": unfold_size_0427,
    "0713": unfold_size_0713,
    "0716": unfold_size_0716,
}


def unfold_by_code(box_code, length_mm, width_mm, height_mm, thickness_mm=1.5, dimension_type="internal", glue_tab_mm=None):
    """按 FEFCO 盒型编码计算展开尺寸（权威入口）。"""
    code = str(box_code or "0201").strip()
    template = get_box_template(code)
    if not template:
        raise PaperBoxGeometryError(f"不支持的 FEFCO 盒型: {code}")
    if not template.get("quote_enabled"):
        raise PaperBoxGeometryError(f"FEFCO {code} 尚未开放报价，敬请期待")
    handler = UNFOLD_HANDLERS.get(code)
    if not handler:
        raise PaperBoxGeometryError(f"FEFCO {code} 展开公式尚未实现")
    return handler(
        length_mm,
        width_mm,
        height_mm,
        thickness_mm=thickness_mm,
        dimension_type=dimension_type,
        glue_tab_mm=glue_tab_mm,
    )
