"""FEFCO 纸盒展开尺寸与面积计算（2D 参数化，权威后端公式）。

支持 P0 盒型：0201 / 0427 / 0713 / 0716。
"""

from decimal import Decimal

from apps.simplequote.board_allowances import resolve_board_allowances
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


def _board_allowances(thickness_mm, template=None):
    """瓦楞纸板制造↔内/外尺寸容差。"""
    flute_type = None
    material_type = None
    template_allowances = None
    if template:
        flute_type = template.get("flute_type")
        material_type = template.get("material_type")
        template_allowances = template.get("allowances")
    return resolve_board_allowances(
        thickness_mm,
        flute_type=flute_type,
        material_type=material_type,
        template_allowances=template_allowances,
    )


def manufacturing_dims(length_mm, width_mm, height_mm, thickness_mm, dimension_type, template=None):
    """将用户输入尺寸换算为制造尺寸（mm）。

    dimension_type: internal | external | manufacturing
    """
    l, w, h, t = (
        _to_float(length_mm),
        _to_float(width_mm),
        _to_float(height_mm),
        max(0.1, _to_float(thickness_mm, 1.5)),
    )
    allow = _board_allowances(t, template)
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


def size_triple_from_manufacturing(length_mm, width_mm, height_mm, thickness_mm, template=None):
    """由制造尺寸推算内/外尺寸。"""
    allow = _board_allowances(thickness_mm, template)
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


def _validate_template_limits(length_mm, width_mm, height_mm, template):
    if not template:
        return
    checks = [
        ("length", length_mm, "min_length_mm", "max_length_mm", "长"),
        ("width", width_mm, "min_width_mm", "max_width_mm", "宽"),
        ("height", height_mm, "min_height_mm", "max_height_mm", "高"),
    ]
    for _field, value, min_key, max_key, label in checks:
        vmin = template.get(min_key)
        vmax = template.get(max_key)
        if vmin is not None and _to_float(value) < _to_float(vmin):
            raise PaperBoxGeometryError(f"{label}不能小于模板允许的最小值 {vmin}mm")
        if vmax is not None and _to_float(value) > _to_float(vmax):
            raise PaperBoxGeometryError(f"{label}不能超过模板允许的最大值 {vmax}mm")


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


def unfold_size_0201(
    length_mm, width_mm, height_mm, thickness_mm=1.5, dimension_type="internal", glue_tab_mm=None, template=None
):
    """FEFCO 0201 展开 blank 尺寸与面积。

    标准 RSC 公式：
    - 展开宽 = 2(L + W) + 接头舌
    - 展开高 = H + W
    """
    l, w, h, t = manufacturing_dims(length_mm, width_mm, height_mm, thickness_mm, dimension_type, template)
    _validate_dims(l, w, h)

    glue_tab = _to_float(glue_tab_mm, DEFAULT_GLUE_TAB_MM)
    glue_tab = max(15.0, glue_tab)

    blank_width_mm = 2 * (l + w) + glue_tab
    blank_height_mm = h + w
    return _build_result("0201", l, w, h, t, glue_tab, blank_width_mm, blank_height_mm)


def unfold_size_0427(
    length_mm, width_mm, height_mm, thickness_mm=1.5, dimension_type="internal", glue_tab_mm=None, template=None
):
    """FEFCO 0427 翻盖自锁飞机盒（RETF / 文件夹式）。

    展开宽 = L + 2W（左右侧墙各 W）
    展开高 = 2H + 2W + 插舌高（≈ H - 厚度）
    """
    l, w, h, t = manufacturing_dims(length_mm, width_mm, height_mm, thickness_mm, dimension_type, template)
    _validate_dims(l, w, h)
    glue_tab = max(15.0, _to_float(glue_tab_mm, DEFAULT_GLUE_TAB_MM))
    tuck_height = max(h - t, h * 0.9, 12.0)
    blank_width_mm = l + 2 * w
    blank_height_mm = 2 * h + 2 * w + tuck_height
    return _build_result("0427", l, w, h, t, glue_tab, blank_width_mm, blank_height_mm)


def unfold_size_0713(
    length_mm, width_mm, height_mm, thickness_mm=1.5, dimension_type="internal", glue_tab_mm=None, template=None
):
    """FEFCO 0713 插舌盒（Tuck end carton）。

    展开宽 = 2(L + W) + 接头舌
    展开高 = 2H + W
    """
    l, w, h, t = manufacturing_dims(length_mm, width_mm, height_mm, thickness_mm, dimension_type, template)
    _validate_dims(l, w, h)
    glue_tab = max(15.0, _to_float(glue_tab_mm, DEFAULT_GLUE_TAB_MM))
    blank_width_mm = 2 * (l + w) + glue_tab
    blank_height_mm = 2 * h + w
    return _build_result("0713", l, w, h, t, glue_tab, blank_width_mm, blank_height_mm)


def unfold_size_0716(
    length_mm, width_mm, height_mm, thickness_mm=1.5, dimension_type="internal", glue_tab_mm=None, template=None
):
    """FEFCO 0716 自动锁底盒。

    展开宽 = 2(L + W) + 接头舌
    展开高 = 2H + 1.25W（含锁底结构余量）
    """
    l, w, h, t = manufacturing_dims(length_mm, width_mm, height_mm, thickness_mm, dimension_type, template)
    _validate_dims(l, w, h)
    glue_tab = max(15.0, _to_float(glue_tab_mm, DEFAULT_GLUE_TAB_MM))
    blank_width_mm = 2 * (l + w) + glue_tab
    blank_height_mm = 2 * h + 1.25 * w
    return _build_result("0716", l, w, h, t, glue_tab, blank_width_mm, blank_height_mm)


def unfold_size_folding_shipping(
    length_mm, width_mm, height_mm, thickness_mm=1.5, dimension_type="internal", glue_tab_mm=None, template=None
):
    """折叠运输箱：展开尺寸与 0201 RSC 相同，底盖为互锁结构。"""
    l, w, h, t = manufacturing_dims(length_mm, width_mm, height_mm, thickness_mm, dimension_type, template)
    _validate_dims(l, w, h)
    glue_tab = max(15.0, _to_float(glue_tab_mm, DEFAULT_GLUE_TAB_MM))
    blank_width_mm = 2 * (l + w) + glue_tab
    blank_height_mm = h + w
    return _build_result("0210", l, w, h, t, glue_tab, blank_width_mm, blank_height_mm)


UNFOLD_HANDLERS = {
    "slotted_rsc": unfold_size_0201,
    "folding_shipping": unfold_size_folding_shipping,
    "mailer_folder": unfold_size_0427,
    "tuck_end": unfold_size_0713,
    "auto_lock_bottom": unfold_size_0716,
}


def unfold_by_code(box_code, length_mm, width_mm, height_mm, thickness_mm=1.5, dimension_type="internal", glue_tab_mm=None):
    """按 FEFCO 盒型编码计算展开尺寸（权威入口）。"""
    code = str(box_code or "0201").strip()
    template = get_box_template(code)
    if not template:
        raise PaperBoxGeometryError(f"不支持的 FEFCO 盒型: {code}")
    purchase_ok = template.get("purchase_enabled", template.get("quote_enabled"))
    if not purchase_ok and not template.get("preview_enabled"):
        raise PaperBoxGeometryError(f"FEFCO {code} 尚未开放，敬请期待")
    _validate_template_limits(length_mm, width_mm, height_mm, template)

    resolved_glue = glue_tab_mm
    if resolved_glue is None:
        resolved_glue = template.get("default_glue_tab_mm", DEFAULT_GLUE_TAB_MM)
    resolved_glue = max(15.0, _to_float(resolved_glue, DEFAULT_GLUE_TAB_MM))

    l, w, h, t = manufacturing_dims(length_mm, width_mm, height_mm, thickness_mm, dimension_type, template)
    _validate_dims(l, w, h)

    geometry_mode = template.get("geometry_mode") or (
        "formula"
        if (template.get("engine_key") or template.get("algorithm_key")) in UNFOLD_HANDLERS
        else "fixed_asset"
    )
    engine_key = template.get("engine_key") or template.get("algorithm_key")

    if geometry_mode == "formula":
        handler = UNFOLD_HANDLERS.get(engine_key)
        if not handler:
            raise PaperBoxGeometryError(f"引擎 {engine_key} 不支持公式展开")
        result = handler(length_mm, width_mm, height_mm, thickness_mm, dimension_type, resolved_glue, template)
        result["box_code"] = code
        result["engine_key"] = engine_key
        result["geometry_mode"] = "formula"
        return result

    if geometry_mode == "fixed_asset":
        from apps.simplequote.dieline_export import calibrate_fixed_segments, effective_bbox
        from apps.simplequote.models import DielineTemplateAsset

        active_asset_payload = template.get("active_parametric_asset") or {}
        asset_id = active_asset_payload.get("id")
        asset = None
        if asset_id:
            asset = DielineTemplateAsset.objects.filter(
                id=asset_id, is_active=True
            ).first()
        if not asset:
            raise PaperBoxGeometryError("固定图纸模板未配置可用资产")

        entities = (asset.parsed_geometry or {}).get("entities") or []
        cal_w = _to_float(asset.calibrated_width_mm, 0)
        cal_h = _to_float(asset.calibrated_height_mm, 0)
        if cal_w <= 0 or cal_h <= 0:
            # Fall back to effective bbox excluding ignore/bleed if not calibrated.
            from apps.simplequote.dieline_export import entities_to_raw_segments

            raw = entities_to_raw_segments(entities)
            try:
                min_x, min_y, max_x, max_y = effective_bbox(raw, exclude_kinds=("bleed", "ignore"))
            except ValueError as exc:
                raise PaperBoxGeometryError(str(exc)) from exc
            blank_width_mm = max_x - min_x
            blank_height_mm = max_y - min_y
        else:
            segs = calibrate_fixed_segments(entities, cal_w, cal_h)
            blank_width_mm = cal_w
            blank_height_mm = cal_h
            _ = segs  # size from calibration

        result = _build_result(code, l, w, h, t, resolved_glue, blank_width_mm, blank_height_mm)
        result["engine_key"] = engine_key
        result["geometry_mode"] = "fixed_asset"
        return result

    raise PaperBoxGeometryError(f"不支持的几何模式: {geometry_mode}")
