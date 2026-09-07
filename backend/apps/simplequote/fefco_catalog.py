"""FEFCO 标准盒型库（分类 + 盒型模板元数据，DB 驱动）。"""

from core.media_urls import absolute_file_url


def _float_or_none(value):
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _serialize_db_category(category):
    code = category.code
    return {
        "id": category.id,
        "code": code,
        "name_key": f"fefcoCat{code}",
        "desc_key": f"fefcoCat{code}Desc",
        "name_i18n": category.name_i18n or {},
        "desc_i18n": category.desc_i18n or {},
        "sort_order": category.sort_order,
        "is_active": category.is_active,
    }


def _serialize_db_template(template, request=None):
    thumbnail_url = absolute_file_url(request, template.thumbnail) if template.thumbnail else ""
    production_asset_url = (
        absolute_file_url(request, template.production_asset) if template.production_asset else ""
    )
    code = template.code
    mfg_l = _float_or_none(template.default_manufacturing_length_mm) or _float_or_none(
        template.default_length_mm
    )
    mfg_w = _float_or_none(template.default_manufacturing_width_mm) or _float_or_none(
        template.default_width_mm
    )
    mfg_h = _float_or_none(template.default_manufacturing_height_mm) or _float_or_none(
        template.default_height_mm
    )
    active_asset = template.assets.filter(is_active=True, mapping_status="mapped").first()
    active_asset_payload = None
    if active_asset:
        source_file_url = (
            absolute_file_url(request, active_asset.source_file)
            if active_asset.source_file
            else ""
        )
        active_asset_payload = {
            "id": active_asset.id,
            "source_format": active_asset.source_format,
            "source_file_url": source_file_url or None,
            "parsed_geometry": active_asset.parsed_geometry or {},
            "mapping_schema": active_asset.mapping_schema or {},
            "base_dimensions": active_asset.base_dimensions or {},
            "calibrated_width_mm": _float_or_none(active_asset.calibrated_width_mm),
            "calibrated_height_mm": _float_or_none(active_asset.calibrated_height_mm),
            "version": active_asset.version,
            "mapping_status": active_asset.mapping_status,
        }
    elif template.assets.exists():
        active_asset_payload = None
    return {
        "id": template.id,
        "code": code,
        "category_code": template.category_code,
        "name_key": f"fefcoBox{code}",
        "desc_key": f"fefcoBox{code}Desc",
        "name_i18n": template.name_i18n or {},
        "desc_i18n": template.desc_i18n or {},
        "engine_key": template.engine_key,
        "algorithm_key": template.engine_key,
        "geometry_mode": template.resolve_geometry_mode(),
        "points_cost": int(template.points_cost or 0),
        "priority": template.priority,
        "purchase_enabled": template.purchase_enabled,
        "quote_enabled": template.purchase_enabled,  # backward-compatible alias
        "preview_enabled": template.preview_enabled,
        "inputs": ["length_mm", "width_mm", "height_mm", "thickness_mm"],
        "sort_order": template.sort_order,
        "default_length_mm": mfg_l,
        "default_width_mm": mfg_w,
        "default_height_mm": mfg_h,
        "default_manufacturing_length_mm": mfg_l,
        "default_manufacturing_width_mm": mfg_w,
        "default_manufacturing_height_mm": mfg_h,
        "default_internal_length_mm": _float_or_none(template.default_internal_length_mm),
        "default_internal_width_mm": _float_or_none(template.default_internal_width_mm),
        "default_internal_height_mm": _float_or_none(template.default_internal_height_mm),
        "default_external_length_mm": _float_or_none(template.default_external_length_mm),
        "default_external_width_mm": _float_or_none(template.default_external_width_mm),
        "default_external_height_mm": _float_or_none(template.default_external_height_mm),
        "default_thickness_mm": _float_or_none(template.default_thickness_mm),
        "default_glue_tab_mm": _float_or_none(template.default_glue_tab_mm),
        "flute_type": template.flute_type,
        "material_type": template.material_type,
        "default_dimension_type": template.default_dimension_type,
        "min_length_mm": _float_or_none(template.min_length_mm),
        "max_length_mm": _float_or_none(template.max_length_mm),
        "min_width_mm": _float_or_none(template.min_width_mm),
        "max_width_mm": _float_or_none(template.max_width_mm),
        "min_height_mm": _float_or_none(template.min_height_mm),
        "max_height_mm": _float_or_none(template.max_height_mm),
        "slot_gap_mm": _float_or_none(template.slot_gap_mm),
        "crease_gap_mm": _float_or_none(template.crease_gap_mm),
        "flap_gap_mm": _float_or_none(template.flap_gap_mm),
        "structure_params": template.structure_params or {},
        "allowances": template.allowances or {},
        "production_asset_url": production_asset_url or None,
        "parametric_asset_status": active_asset.mapping_status if active_asset else ("draft" if template.assets.exists() else "none"),
        "active_parametric_asset": active_asset_payload,
        "thumbnail_url": thumbnail_url or None,
        "is_active": template.is_active,
    }


def get_box_template(box_code, *, active_only=True):
    code = str(box_code or "").strip()
    if not code:
        return None
    try:
        from apps.simplequote.models import DielineTemplate

        qs = DielineTemplate.objects.filter(code=code)
        if active_only:
            qs = qs.filter(is_active=True)
        obj = qs.first()
        if obj:
            return _serialize_db_template(obj)
    except Exception:
        pass
    return None


def build_fefco_catalog(request=None, *, include_inactive=False):
    from apps.simplequote.models import DielineCategory, DielineTemplate

    cat_qs = DielineCategory.objects.all()
    if not include_inactive:
        cat_qs = cat_qs.filter(is_active=True)
    cat_qs = cat_qs.order_by("sort_order", "code")
    categories = [_serialize_db_category(item) for item in cat_qs]

    tpl_qs = DielineTemplate.objects.all()
    if not include_inactive:
        tpl_qs = tpl_qs.filter(is_active=True)
    # Formula templates need no mapped asset; fixed_asset still requires mapped active asset.
    from django.db.models import Q

    tpl_qs = tpl_qs.filter(
        Q(geometry_mode="formula")
        | Q(assets__is_active=True, assets__mapping_status="mapped")
    ).distinct()
    tpl_qs = tpl_qs.order_by("sort_order", "code")
    templates = [_serialize_db_template(item, request) for item in tpl_qs]

    by_category = {}
    for template in templates:
        by_category.setdefault(template["category_code"], []).append(template)

    visible_categories = [
        category
        for category in categories
        if by_category.get(category["code"])
    ]

    return {
        "categories": visible_categories,
        "templates": templates,
        "by_category": by_category,
    }
