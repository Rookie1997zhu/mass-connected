"""楞型/材质容差表：制造尺寸 ↔ 内/外尺寸换算。"""

from decimal import Decimal

FLUTE_TABLE = {
    "e": {"ref_thickness": 1.5, "internal_lw": 2.0, "internal_h": 4.0, "external_lw": 1.0, "external_h": 2.0},
    "b": {"ref_thickness": 3.0, "internal_lw": 4.0, "internal_h": 8.0, "external_lw": 2.0, "external_h": 4.0},
    "c": {"ref_thickness": 4.0, "internal_lw": 5.0, "internal_h": 10.0, "external_lw": 3.0, "external_h": 5.0},
    "bc": {"ref_thickness": 7.0, "internal_lw": 8.0, "internal_h": 16.0, "external_lw": 4.0, "external_h": 8.0},
    "none": {"ref_thickness": 0.5, "internal_lw": 0.5, "internal_h": 1.0, "external_lw": 0.25, "external_h": 0.5},
}

MATERIAL_DEFAULT_FLUTE = {
    "corrugated": "b",
    "white_card": "none",
    "kraft": "none",
    "coated": "none",
}


def _to_float(value, default=0.0):
    try:
        if isinstance(value, Decimal):
            return float(value)
        return float(value)
    except (TypeError, ValueError):
        return default


def _scale_allowance(base, ref_thickness, actual_thickness):
    ref = max(0.1, _to_float(ref_thickness, 3.0))
    actual = max(0.1, _to_float(actual_thickness, ref))
    return base * (actual / ref)


def normalize_flute_type(flute_type=None, material_type=None):
    flute = str(flute_type or "").strip().lower()
    if flute in FLUTE_TABLE:
        return flute
    material = str(material_type or "").strip().lower()
    return MATERIAL_DEFAULT_FLUTE.get(material, "b")


def resolve_board_allowances(
    thickness_mm,
    *,
    flute_type=None,
    material_type=None,
    template_allowances=None,
):
    """返回 internal_lw/internal_h/external_lw/external_h（mm）。

    优先级：模板 allowances 覆盖 > 楞型表（按厚度比例缩放）> B 楞默认。
    """
    overrides = template_allowances if isinstance(template_allowances, dict) else {}
    if all(k in overrides for k in ("internal_lw", "internal_h", "external_lw", "external_h")):
        return {
            "internal_lw": _to_float(overrides["internal_lw"], 4.0),
            "internal_h": _to_float(overrides["internal_h"], 8.0),
            "external_lw": _to_float(overrides["external_lw"], 2.0),
            "external_h": _to_float(overrides["external_h"], 4.0),
        }

    flute = normalize_flute_type(flute_type, material_type)
    base = FLUTE_TABLE.get(flute, FLUTE_TABLE["b"])
    ref_t = base["ref_thickness"]
    t = max(0.1, _to_float(thickness_mm, ref_t))

    result = {
        "internal_lw": _scale_allowance(base["internal_lw"], ref_t, t),
        "internal_h": _scale_allowance(base["internal_h"], ref_t, t),
        "external_lw": _scale_allowance(base["external_lw"], ref_t, t),
        "external_h": _scale_allowance(base["external_h"], ref_t, t),
    }

    for key in result:
        if key in overrides and overrides[key] is not None:
            result[key] = _to_float(overrides[key], result[key])
    return result
