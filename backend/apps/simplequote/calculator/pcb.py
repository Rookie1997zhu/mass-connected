"""PCB 开发与样板制造费报价计算。"""

import math

from apps.simplequote.calculator.utils import PcbQuoteError, _int, _to_number


def _find_base_item(tables, item_no):
    for row in (tables or {}).get("base_pricing") or []:
        if _int(row.get("no")) == _int(item_no):
            return row
    return None


def _normalize_pcb_material_key(material):
    raw = str(material or "fr4").strip().lower().replace("-", "").replace("_", "")
    if raw in ("fr4", "fr", "fr四"):
        return "fr4"
    if raw in ("fpc", "flex", "flexible"):
        return "fpc"
    if raw in ("aluminum", "alu", "aluminium"):
        return "aluminum"
    return raw or "fr4"


def _to_pcb_bool(value):
    """将 PCB 字段值规范化为 bool，兼容 True/False/"true"/"false"/1/0/None。"""
    if value is None:
        return False
    if isinstance(value, bool):
        return value
    return str(value).lower() in ("true", "1", "yes")


def _pcb_manufacturing_spec(inputs):
    manufacturing = inputs.get("manufacturing") or {}
    return {
        "material_key": _normalize_pcb_material_key(
            manufacturing.get("material") or inputs.get("mfg_material") or inputs.get("manufacturing_material")
        ),
        "layers": _int(manufacturing.get("layers") or inputs.get("mfg_layers") or inputs.get("manufacturing_layers"), 0),
        "width_mm": _int(manufacturing.get("width_mm") or inputs.get("mfg_width_mm") or inputs.get("manufacturing_width_mm"), 0),
        "height_mm": _int(manufacturing.get("height_mm") or inputs.get("mfg_height_mm") or inputs.get("manufacturing_height_mm"), 0),
        "quantity": _int(manufacturing.get("quantity") or inputs.get("mfg_quantity") or inputs.get("manufacturing_quantity"), 0),
        "board_thickness": str(
            manufacturing.get("board_thickness")
            or inputs.get("mfg_board_thickness")
            or inputs.get("manufacturing_board_thickness")
            or ""
        ).strip(),
        "solder_color": str(
            manufacturing.get("solder_color")
            or inputs.get("mfg_solder_color")
            or inputs.get("manufacturing_solder_color")
            or ""
        ).strip(),
        "surface_finish": str(
            manufacturing.get("surface_finish")
            or inputs.get("mfg_surface_finish")
            or inputs.get("manufacturing_surface_finish")
            or ""
        ).strip(),
        "copper_thickness": str(
            manufacturing.get("copper_thickness")
            or inputs.get("mfg_copper_thickness")
            or inputs.get("manufacturing_copper_thickness")
            or ""
        ).strip(),
        "solder_mask_coverage": str(
            manufacturing.get("solder_mask_coverage")
            or inputs.get("mfg_solder_mask_coverage")
            or inputs.get("manufacturing_solder_mask_coverage")
            or ""
        ).strip(),
        "panel_design_count": str(
            manufacturing.get("panel_design_count")
            or inputs.get("mfg_panel_design_count")
            or inputs.get("manufacturing_panel_design_count")
            or ""
        ).strip(),
        "confirm_production_file": str(
            manufacturing.get("confirm_production_file")
            or inputs.get("mfg_confirm_production_file")
            or inputs.get("manufacturing_confirm_production_file")
            or "none"
        ).strip()
        or "none",
        "smt_required": _to_pcb_bool(
            manufacturing.get("smt_required")
            or inputs.get("mfg_smt_required")
            or inputs.get("manufacturing_smt_required")
        ),
    }


def _find_pcb_manufacturing_row(tables, spec):
    for row in (tables or {}).get("manufacturing_price_list") or []:
        if not row.get("enabled", True):
            continue
        if _normalize_pcb_material_key(row.get("material_key")) != spec["material_key"]:
            continue
        if _int(row.get("layers")) != spec["layers"]:
            continue
        if _int(row.get("width_mm")) != spec["width_mm"]:
            continue
        if _int(row.get("height_mm")) != spec["height_mm"]:
            continue
        if _int(row.get("quantity")) != spec["quantity"]:
            continue
        return row
    return None


def _pcb_manufacturing_meta(tables):
    rows = (tables or {}).get("manufacturing_price_meta") or []
    return rows[0] if rows else {}


def _resolve_pcb_process_spec(spec, meta):
    process_options = (meta.get("process_options") or {}).get(spec["material_key"]) or {}
    defaults = process_options.get("defaults") or {}
    resolved = {
        "board_thickness": spec.get("board_thickness") or str(defaults.get("boardThickness") or ""),
        "solder_color": spec.get("solder_color") or str(defaults.get("solderColor") or ""),
        "surface_finish": spec.get("surface_finish") or str(defaults.get("surfaceFinish") or ""),
        "copper_thickness": spec.get("copper_thickness") or str(defaults.get("copperThickness") or ""),
        "solder_mask_coverage": spec.get("solder_mask_coverage") or str(defaults.get("solderMaskCoverage") or ""),
        "panel_design_count": spec.get("panel_design_count") or str(defaults.get("panelDesignCount") or ""),
    }
    field_map = {
        "board_thickness": "boardThickness",
        "solder_color": "solderColor",
        "surface_finish": "surfaceFinish",
        "copper_thickness": "copperThickness",
        "solder_mask_coverage": "solderMaskCoverage",
        "panel_design_count": "panelDesignCount",
    }
    invalid = []
    is_standard = True
    for output_field, model_field in field_map.items():
        allowed = [str(value) for value in (process_options.get("options") or {}).get(model_field) or []]
        value = str(resolved[output_field])
        default_value = str(defaults.get(model_field) or "")
        if allowed and value not in allowed:
            invalid.append(output_field)
        if value != default_value:
            is_standard = False
    return resolved, invalid, is_standard


def _apply_pcb_process_model(base_price, spec, meta):
    from apps.simplequote.calculator.pcb_jlc_closed_addons import lead_free_hasl_fee_cny

    process_model = meta.get("process_model") or {}
    material = (process_model.get("materials") or {}).get(spec["material_key"]) or {}
    factors = material.get("factors") or {}
    field_map = {
        "board_thickness": "boardThickness",
        "solder_color": "solderColor",
        "surface_finish": "surfaceFinish",
        "copper_thickness": "copperThickness",
        "solder_mask_coverage": "solderMaskCoverage",
        "panel_design_count": "panelDesignCount",
    }
    area = spec.get("width_mm", 0) * spec.get("height_mm", 0)
    if area <= 5000:
        area_band = "small"
    elif area <= 15000:
        area_band = "mid"
    else:
        area_band = "large"
    price = _to_number(base_price, 0)
    adjustments = []
    for output_field, model_field in field_map.items():
        value = str(spec.get(output_field) or "")
        field_factors = factors.get(model_field)
        if field_factors is None:
            # 该字段在当前材料 process model 中未配置，视为中性跳过（向后兼容）
            continue
        factor = field_factors.get(value)
        if not factor:
            return None
        scale_segments = factor.get("scaleSegments") or {}
        if scale_segments:
            factor = scale_segments.get(area_band) or factor
        allowed_layers = [_int(layer) for layer in factor.get("layers") or []]
        if allowed_layers and spec["layers"] not in allowed_layers:
            return None
        before = price
        method = factor.get("method") or "multiplier"
        if method == "lead_free_hasl_area":
            price += lead_free_hasl_fee_cny(
                spec.get("width_mm"),
                spec.get("height_mm"),
                spec.get("quantity"),
            )
        elif method == "additive":
            price += _to_number(factor.get("additiveCny"), 0)
        else:
            price *= _to_number(factor.get("multiplier"), 1)
        adjustments.append(
            {
                "field": output_field,
                "value": value,
                "method": method,
                "amount_cny": round(price - before, 2),
                "area_band": area_band,
            }
        )
    # 应用交互修正：process_model.interactions[material_key]
    camel_to_snake = {v: k for k, v in field_map.items()}
    interactions = (process_model.get("interactions") or {}).get(spec["material_key"]) or []
    for interaction in interactions:
        interaction_fields = interaction.get("fields") or {}
        if not all(
            str(spec.get(camel_to_snake.get(mf, ""), "") or "") == str(expected)
            for mf, expected in interaction_fields.items()
        ):
            continue
        before = price
        if interaction.get("method") == "additive":
            price += _to_number(interaction.get("additiveCny"), 0)
        else:
            price *= _to_number(interaction.get("multiplier"), 1)
        adjustments.append(
            {
                "field": f"interaction:{interaction.get('id', 'unknown')}",
                "value": str(interaction_fields),
                "method": interaction.get("method") or "multiplier",
                "amount_cny": round(price - before, 2),
            }
        )
    return {"jlc_price_cny": round(max(0, price), 2), "adjustments": adjustments}


def _match_pcb_process_enabled_zone(spec, meta):
    """非标工艺在材料未整体启用时，按 process_enabled_zones 局部放行。

    仅当每一个相对 defaults 的偏离字段都能被某个同材料 zone 覆盖时才放行，
    避免「单字段 zone」误放行多工艺组合。
    """
    zones = meta.get("process_enabled_zones") or (meta.get("process_model") or {}).get("enabledZones") or []
    field_aliases = {
        "boardThickness": "board_thickness",
        "solderColor": "solder_color",
        "surfaceFinish": "surface_finish",
        "copperThickness": "copper_thickness",
        "solderMaskCoverage": "solder_mask_coverage",
        "panelDesignCount": "panel_design_count",
    }
    process_options = (meta.get("process_options") or {}).get(spec.get("material_key")) or {}
    defaults = process_options.get("defaults") or {}
    deviations = {}
    for camel, snake in field_aliases.items():
        default_value = str(defaults.get(camel) or "")
        actual = str(spec.get(snake) or "")
        if actual and actual != default_value:
            deviations[camel] = actual
    if not deviations:
        return None

    remaining = dict(deviations)
    matched_zone = None
    for zone in zones:
        if zone.get("action") not in (None, "auto_quote"):
            continue
        if zone.get("material_key") and zone["material_key"] != spec.get("material_key"):
            continue
        process_fields = zone.get("process_fields") or {}
        if not process_fields:
            continue
        covers = True
        for raw_key, expected in process_fields.items():
            field = field_aliases.get(raw_key, raw_key)
            actual = str(spec.get(field) or "")
            expected_values = expected if isinstance(expected, (list, tuple)) else [expected]
            if actual not in [str(item) for item in expected_values]:
                covers = False
                break
        if not covers:
            continue
        for raw_key, expected in process_fields.items():
            expected_values = expected if isinstance(expected, (list, tuple)) else [expected]
            if raw_key in remaining and remaining[raw_key] in [str(item) for item in expected_values]:
                remaining.pop(raw_key, None)
        if matched_zone is None:
            matched_zone = zone
    if remaining:
        return None
    return matched_zone


def _pcb_acceptance_allows_auto_estimate(meta):
    """独立验收未通过时，禁止 estimator/process 自动报价；缺失字段视为旧版兼容通过。"""
    acceptance_status = meta.get("acceptance_status")
    if acceptance_status in (None, ""):
        # v6 及更早 meta 无该字段，保持兼容
        return True
    return acceptance_status == "passed"


def _pcb_v9_segment_key(row):
    width = _to_number(row.get("width_mm", row.get("widthMm")), 0)
    height = _to_number(row.get("height_mm", row.get("heightMm")), 0)
    area = width * height
    quantity = _int(row.get("quantity"))
    area_segment = "small" if area <= 6000 else ("medium" if area <= 16000 else "large")
    quantity_segment = "low" if quantity <= 20 else ("medium" if quantity <= 75 else "high")
    return f"{_int(row.get('layers'))}|{area_segment}|{quantity_segment}"


def _median_number(values):
    ordered = sorted(_to_number(value, 0) for value in values)
    if not ordered:
        return 0
    middle = len(ordered) // 2
    if len(ordered) % 2:
        return ordered[middle]
    return (ordered[middle - 1] + ordered[middle]) / 2


def _pcb_quantity_band(quantity):
    if _int(quantity) <= 20:
        return "low"
    if _int(quantity) <= 75:
        return "medium"
    return "high"


def _estimate_pcb_v9_material_model(candidates, spec, estimator, material_config):
    model_type = material_config.get("modelType")
    guards = material_config.get("guards") or {}
    area_weight = _to_number(guards.get("areaWeight"), 1)
    quantity_weight = _to_number(guards.get("quantityWeight"), 0.8)
    max_distance = _to_number(guards.get("maxNeighborDistance"), 0.7)
    min_neighbors = max(1, _int(guards.get("minLocalNeighbors"), 2))
    target_area = spec["width_mm"] * spec["height_mm"]
    fpc_formula = None

    if model_type == "fpc_layered_floor_area_quantity" or model_type == "fr4_layered_floor_area_quantity":
        quantity_band = _pcb_quantity_band(spec["quantity"])
        layer_bands = (material_config.get("layerQuantityBands") or {}).get(
            str(spec["layers"]),
            {},
        )
        fpc_formula = layer_bands.get(quantity_band)
        if not fpc_formula:
            return None
        candidates = [
            row
            for row in candidates
            if _pcb_quantity_band(row.get("quantity")) == quantity_band
        ]
        max_distance = _to_number(
            fpc_formula.get("maxNeighborDistance"),
            max_distance,
        )
        min_neighbors = max(
            1,
            _int(fpc_formula.get("minLocalNeighbors"), min_neighbors),
        )

    if model_type == "fr4_segmented" and material_config.get("useSegments", True):
        target_segment = _pcb_v9_segment_key(
            {
                "layers": spec["layers"],
                "width_mm": spec["width_mm"],
                "height_mm": spec["height_mm"],
                "quantity": spec["quantity"],
            }
        )
        segmented = [row for row in candidates if _pcb_v9_segment_key(row) == target_segment]
        if len(segmented) >= min_neighbors:
            candidates = segmented

    distances = []
    for row in candidates:
        row_area = _int(row.get("width_mm")) * _int(row.get("height_mm"))
        row_quantity = _int(row.get("quantity"))
        if row_area <= 0 or row_quantity <= 0:
            continue
        distance = math.sqrt(
            (math.log(target_area / row_area) * area_weight) ** 2
            + (math.log(spec["quantity"] / row_quantity) * quantity_weight) ** 2
        )
        distances.append((distance, row))
    distances.sort(key=lambda item: item[0])
    neighbor_count = max(
        min_neighbors,
        _int(
            (fpc_formula or {}).get("neighbors", material_config.get("neighbors")),
            _int(estimator.get("neighbors"), 6),
        ),
    )
    local = [item for item in distances[:neighbor_count] if item[0] <= max_distance]
    if len(local) < min_neighbors:
        return None

    if (
        model_type == "aluminum_floor_area_quantity"
        or material_config.get("formula") == "floor_area_quantity"
        or model_type == "fpc_layered_floor_area_quantity"
        or model_type == "fr4_layered_floor_area_quantity"
    ):
        formula = fpc_formula or material_config
        floor_price = _to_number(formula.get("floorPriceCny"), 0)
        area_exponent = _to_number(
            formula.get("areaExponent", guards.get("areaExponent")),
            0.92,
        )
        quantity_exponent = _to_number(
            formula.get("quantityExponent", guards.get("quantityExponent")),
            0.72,
        )
        rates = []
        for _distance, row in local:
            row_area = _int(row.get("width_mm")) * _int(row.get("height_mm"))
            variable_price = max(_to_number(row.get("jlc_price_cny"), 0) - floor_price, 0.01)
            rates.append(
                variable_price
                / (row_area ** area_exponent)
                / (_int(row.get("quantity")) ** quantity_exponent)
            )
        if formula.get("rateAggregation") == "distance_weighted_rate":
            rate_weights = [1 / ((distance**2) + 0.005) for distance, _row in local]
            selected_rate = sum(
                rate * weight for rate, weight in zip(rates, rate_weights)
            ) / sum(rate_weights)
        else:
            selected_rate = _median_number(rates)
        predicted = (
            floor_price
            + selected_rate
            * (target_area ** area_exponent)
            * (spec["quantity"] ** quantity_exponent)
        )
    else:
        weighted_log_price = 0
        total_weight = 0
        for distance, row in local:
            weight = 1 / ((distance ** 2) + 0.005)
            weighted_log_price += math.log(_to_number(row.get("jlc_price_cny"), 0)) * weight
            total_weight += weight
        predicted = math.exp(weighted_log_price / total_weight)

    basis_median = _median_number([row.get("jlc_price_cny") for _distance, row in local])
    multiplier = predicted / basis_median if basis_median else 1
    min_multiplier = _to_number((fpc_formula or {}).get("minPredictionMultiplier"), 0.25)
    max_multiplier = _to_number((fpc_formula or {}).get("maxPredictionMultiplier"), 4)
    if multiplier < min_multiplier or multiplier > max_multiplier:
        return None
    if fpc_formula:
        local_residuals = []
        for _distance, row in local:
            row_area = _int(row.get("width_mm")) * _int(row.get("height_mm"))
            fitted = (
                floor_price
                + selected_rate
                * (row_area ** area_exponent)
                * (_int(row.get("quantity")) ** quantity_exponent)
            )
            row_price = _to_number(row.get("jlc_price_cny"), 0)
            if row_price > 0:
                local_residuals.append(abs(fitted - row_price) / row_price)
        max_local_residual = _to_number(
            fpc_formula.get("maxLocalResidualRatio"),
            0.35,
        )
        if _median_number(local_residuals) > max_local_residual:
            return None
    average_distance = sum(distance for distance, _row in local) / len(local)
    basis = [
        {
            "layers": _int(row.get("layers")),
            "width_mm": _int(row.get("width_mm")),
            "height_mm": _int(row.get("height_mm")),
            "quantity": _int(row.get("quantity")),
            "jlc_price_cny": _to_number(row.get("jlc_price_cny"), 0),
        }
        for _distance, row in local
    ]
    return {
        "jlc_price_cny": round(predicted, 2),
        "confidence": round(max(0.2, min(0.99, 1 / (1 + average_distance))), 4),
        "basis": basis,
        "average_distance": round(average_distance, 4),
        "local_coverage": len(local),
        "extrapolation": False,
        "model_type": model_type,
    }


def _estimate_pcb_manufacturing_by_model(tables, spec, meta):
    estimator = meta.get("estimator") or {}
    material_config = (estimator.get("materials") or {}).get(spec["material_key"]) or {}
    allowed_layers = [_int(value) for value in material_config.get("layers") or []]
    if spec["layers"] not in allowed_layers:
        return None
    if (
        spec["width_mm"] < _int(material_config.get("minWidthMm"), 1)
        or spec["height_mm"] < _int(material_config.get("minHeightMm"), 1)
        or spec["quantity"] < _int(material_config.get("minQuantity"), 1)
        or spec["width_mm"] > _int(material_config.get("maxWidthMm"), 0)
        or spec["height_mm"] > _int(material_config.get("maxHeightMm"), 0)
        or spec["quantity"] > _int(material_config.get("maxQuantity"), 0)
    ):
        return None

    candidates = [
        row
        for row in (tables or {}).get("manufacturing_price_list") or []
        if row.get("enabled", True)
        and _normalize_pcb_material_key(row.get("material_key")) == spec["material_key"]
        and _int(row.get("layers")) == spec["layers"]
        and _to_number(row.get("jlc_price_cny"), 0) > 0
    ]
    if not candidates:
        return None

    area = spec["width_mm"] * spec["height_mm"]
    aspect = max(spec["width_mm"], spec["height_mm"]) / min(spec["width_mm"], spec["height_mm"])
    area_weight = _to_number(estimator.get("areaWeight"), 1)
    aspect_weight = _to_number(estimator.get("aspectWeight"), 0.35)
    # v8：局部覆盖密度阈值，稀疏邻域直接拒绝外推
    max_neighbor_distance = _to_number(
        estimator.get("maxNeighborDistance"),
        _to_number((meta.get("estimator_guards") or {}).get("maxNeighborDistance"), 0.85),
    )
    min_local_neighbors = max(
        1,
        _int(
            estimator.get("minLocalNeighbors"),
            _int((meta.get("estimator_guards") or {}).get("minLocalNeighbors"), 2),
        ),
    )
    exact = next(
        (
            row
            for row in candidates
            if _int(row.get("width_mm")) == spec["width_mm"]
            and _int(row.get("height_mm")) == spec["height_mm"]
            and _int(row.get("quantity")) == spec["quantity"]
        ),
        None,
    )
    if exact:
        return {
            "jlc_price_cny": _to_number(exact.get("jlc_price_cny"), 0),
            "confidence": 1,
            "basis": [exact],
            "average_distance": 0,
            "local_coverage": 1,
            "extrapolation": False,
        }

    if material_config.get("modelType") in {
        "fr4_segmented",
        "fr4_layered_floor_area_quantity",
        "aluminum_floor_area_quantity",
        "fpc_local",
        "fpc_layered_floor_area_quantity",
    }:
        return _estimate_pcb_v9_material_model(
            candidates,
            spec,
            estimator,
            material_config,
        )

    rows_by_size = {}
    for row in candidates:
        size_key = (_int(row.get("width_mm")), _int(row.get("height_mm")))
        rows_by_size.setdefault(size_key, []).append(row)

    size_estimates = []
    for (row_width, row_height), size_rows in rows_by_size.items():
        size_rows.sort(key=lambda row: _int(row.get("quantity")))
        exact_quantity = next(
            (row for row in size_rows if _int(row.get("quantity")) == spec["quantity"]),
            None,
        )
        quantity_extrapolated = False
        if exact_quantity:
            estimated_price = _to_number(exact_quantity.get("jlc_price_cny"), 0)
            basis_rows = [exact_quantity]
        else:
            lower_rows = [row for row in size_rows if _int(row.get("quantity")) < spec["quantity"]]
            upper_rows = [row for row in size_rows if _int(row.get("quantity")) > spec["quantity"]]
            if not lower_rows or not upper_rows:
                # 数量阶梯外侧：拒绝远距离外推
                quantity_extrapolated = True
                continue
            lower = lower_rows[-1]
            upper = upper_rows[0]
            lower_quantity = _int(lower.get("quantity"))
            upper_quantity = _int(upper.get("quantity"))
            quantity_ratio = math.log(spec["quantity"] / lower_quantity) / math.log(
                upper_quantity / lower_quantity
            )
            estimated_price = math.exp(
                math.log(_to_number(lower.get("jlc_price_cny"), 0))
                + quantity_ratio
                * (
                    math.log(_to_number(upper.get("jlc_price_cny"), 0))
                    - math.log(_to_number(lower.get("jlc_price_cny"), 0))
                )
            )
            basis_rows = [lower, upper]
        row_area = row_width * row_height
        row_aspect = max(row_width, row_height) / min(row_width, row_height)
        area_diff = math.log(area / row_area) * area_weight
        aspect_diff = math.log(aspect / row_aspect) * aspect_weight
        distance = math.sqrt((area_diff ** 2) + (aspect_diff ** 2))
        size_estimates.append((distance, estimated_price, basis_rows, quantity_extrapolated))
    if not size_estimates:
        return None
    size_estimates.sort(key=lambda item: item[0])
    neighbor_count = max(1, _int(estimator.get("neighbors"), 4))
    nearest = size_estimates[:neighbor_count]
    average_distance = sum(distance for distance, _price, _basis_rows, _ext in nearest) / len(nearest)
    local_coverage = sum(1 for distance, _price, _basis_rows, _ext in nearest if distance <= max_neighbor_distance)
    if nearest[0][0] > max_neighbor_distance or local_coverage < min_local_neighbors:
        return None
    if nearest[0][0] < 1e-9:
        return {
            "jlc_price_cny": round(nearest[0][1], 2),
            "confidence": 0.95,
            "basis": nearest[0][2],
            "average_distance": 0,
            "local_coverage": local_coverage,
            "extrapolation": False,
        }

    weighted_log_price = 0
    total_weight = 0
    for distance, estimated_price, _basis_rows, _ext in nearest:
        weight = 1 / ((distance ** 2) + 0.005)
        weighted_log_price += math.log(estimated_price) * weight
        total_weight += weight
    basis = []
    basis_keys = set()
    for _distance, _price, basis_rows, _ext in nearest:
        for row in basis_rows:
            row_key = (
                _int(row.get("layers")),
                _int(row.get("width_mm")),
                _int(row.get("height_mm")),
                _int(row.get("quantity")),
            )
            if row_key in basis_keys:
                continue
            basis_keys.add(row_key)
            basis.append(
                {
                    "layers": row_key[0],
                    "width_mm": row_key[1],
                    "height_mm": row_key[2],
                    "quantity": row_key[3],
                    "jlc_price_cny": _to_number(row.get("jlc_price_cny"), 0),
                }
            )
    return {
        "jlc_price_cny": round(math.exp(weighted_log_price / total_weight), 2),
        "confidence": round(max(0.2, min(0.99, 1 / (1 + average_distance))), 4),
        "basis": basis,
        "average_distance": round(average_distance, 4),
        "local_coverage": local_coverage,
        "extrapolation": average_distance > (max_neighbor_distance * 0.6),
    }


def _match_pcb_risk_zone(spec, meta):
    """检查规格是否命中 meta.risk_zones 中定义的风险分区，命中则返回 zone 字典，否则返回 None。

    zone 可含字段（均为可选）：
      material_key, layers(list), min_area_mm2, max_area_mm2,
      min_quantity, max_quantity, process_fields(dict→scalar or list), action, id
    """
    risk_zones = meta.get("risk_zones") or []
    area = spec.get("width_mm", 0) * spec.get("height_mm", 0)
    quantity = spec.get("quantity", 0)
    field_aliases = {
        "boardThickness": "board_thickness",
        "solderColor": "solder_color",
        "surfaceFinish": "surface_finish",
        "copperThickness": "copper_thickness",
        "solderMaskCoverage": "solder_mask_coverage",
        "panelDesignCount": "panel_design_count",
    }
    for zone in risk_zones:
        if zone.get("material_key") and zone["material_key"] != spec.get("material_key"):
            continue
        if zone.get("layers") and spec.get("layers") not in [_int(layer) for layer in zone["layers"]]:
            continue
        if zone.get("min_area_mm2") is not None and area < _to_number(zone["min_area_mm2"], 0):
            continue
        if zone.get("max_area_mm2") is not None and area > _to_number(zone["max_area_mm2"], 0):
            continue
        if zone.get("min_quantity") is not None and quantity < _int(zone["min_quantity"]):
            continue
        if zone.get("max_quantity") is not None and quantity > _int(zone["max_quantity"]):
            continue
        if zone.get("process_fields"):
            matched_fields = True
            for raw_key, expected in zone["process_fields"].items():
                spec_key = field_aliases.get(raw_key, raw_key)
                actual = str(spec.get(spec_key) or "")
                if isinstance(expected, (list, tuple, set)):
                    if actual not in {str(item) for item in expected}:
                        matched_fields = False
                        break
                elif actual != str(expected):
                    matched_fields = False
                    break
            if not matched_fields:
                continue
        return zone
    return None


PCB_QUOTE_RANGE_RATE = 0.20


def _pcb_quote_range(*, jlc_mid_cny, customer_mid_cny, customer_mid_krw, rate=None):
    """由中位价展开 ±rate 区间（默认 ±20%）。"""
    range_rate = PCB_QUOTE_RANGE_RATE if rate is None else _to_number(rate, PCB_QUOTE_RANGE_RATE)
    jlc_mid = _to_number(jlc_mid_cny, 0)
    customer_cny = _to_number(customer_mid_cny, 0)
    customer_krw = _to_number(customer_mid_krw, 0)
    return {
        "quote_range_rate": range_rate,
        "pricing_display_mode": "range",
        "jlc_estimate_cny_min": round(jlc_mid * (1 - range_rate), 2) if jlc_mid else 0,
        "jlc_estimate_cny_max": round(jlc_mid * (1 + range_rate), 2) if jlc_mid else 0,
        "customer_quote_cny_min": round(customer_cny * (1 - range_rate), 2) if customer_cny else 0,
        "customer_quote_cny_max": round(customer_cny * (1 + range_rate), 2) if customer_cny else 0,
        "customer_quote_krw_min": round(customer_krw * (1 - range_rate)) if customer_krw else 0,
        "customer_quote_krw_max": round(customer_krw * (1 + range_rate)) if customer_krw else 0,
    }


def _pcb_manual_display_fields():
    return {
        "quote_range_rate": None,
        "pricing_display_mode": "manual",
        "jlc_estimate_cny_min": None,
        "jlc_estimate_cny_max": None,
        "customer_quote_cny_min": None,
        "customer_quote_cny_max": None,
        "customer_quote_krw_min": None,
        "customer_quote_krw_max": None,
    }


def _estimate_pcb_manufacturing(inputs, params, tables):
    include = bool(inputs.get("include_pcb_manufacturing") or inputs.get("include_manufacturing"))
    meta = _pcb_manufacturing_meta(tables)
    validation_status = meta.get("validation_status")
    acceptance_status = meta.get("acceptance_status")
    enabled_materials = meta.get("enabled_materials") or []
    allow_auto_estimate = _pcb_acceptance_allows_auto_estimate(meta)
    range_rate = _to_number(meta.get("quote_range_rate"), PCB_QUOTE_RANGE_RATE)
    base_result = {
        "enabled": include,
        "requires_manual_review": False,
        "manual_review_reasons": [],
        "pricing_mode": "exact_lookup",
        "is_estimated": False,
        "price_version": meta.get("version"),
        "active_price_version": meta.get("active_price_version") or meta.get("version"),
        "fallback_version": meta.get("fallback_version") or "jlc-cn-pcb-v6-20260712",
        "valid_days": meta.get("valid_days"),
        "validation_status": validation_status,
        "acceptance_status": acceptance_status,
        "estimator_version": (meta.get("estimator") or {}).get("version"),
        "validation_metrics": (meta.get("estimator") or {}).get("validationMetrics"),
        "process_model_version": (meta.get("process_model") or {}).get("version"),
        "process_validation_status": (meta.get("process_model") or {}).get("validationStatus"),
        "process_adjusted": False,
        "process_adjustments": [],
        "smt_price_included": False,
        "risk_zone": None,
        "risk_status": None,
        **_pcb_manual_display_fields(),
    }
    if not include:
        return base_result

    spec = _pcb_manufacturing_spec(inputs)
    process_spec, invalid_process_fields, is_standard_process = _resolve_pcb_process_spec(spec, meta)
    spec.update(process_spec)
    base_result.update(spec)
    base_result["selected_process"] = process_spec
    base_result["is_standard_process"] = is_standard_process
    if spec["width_mm"] <= 0 or spec["height_mm"] <= 0 or spec["quantity"] <= 0 or spec["layers"] <= 0:
        return {
            **base_result,
            "requires_manual_review": True,
            "manual_review_reasons": ["PCB 样板制造规格不完整"],
        }

    if validation_status != "passed":
        return {
            **base_result,
            "requires_manual_review": True,
            "manual_review_reasons": ["PCB 样板制造费价格表尚未通过 live 验证，需人工复核"],
        }

    if spec["material_key"] not in ("fr4", "fpc", "aluminum"):
        return {
            **base_result,
            "requires_manual_review": True,
            "manual_review_reasons": ["该板材不在当前自动报价范围内"],
        }

    if enabled_materials and spec["material_key"] not in enabled_materials:
        return {
            **base_result,
            "requires_manual_review": True,
            "manual_review_reasons": ["该材料当前未启用自动报价"],
        }

    if invalid_process_fields:
        return {
            **base_result,
            "requires_manual_review": True,
            "manual_review_reasons": [
                f"所选 PCB 工艺不在当前已验证范围：{', '.join(invalid_process_fields)}"
            ],
        }

    row = _find_pcb_manufacturing_row(tables, spec)
    if not row:
        if not allow_auto_estimate:
            return {
                **base_result,
                "requires_manual_review": True,
                "manual_review_reasons": [
                    "独立验收未通过，非精确命中规格暂不自动估算，需人工复核"
                    f"（acceptance_status={acceptance_status or 'unknown'}）"
                ],
            }
        estimator_enabled_materials = meta.get("estimator_enabled_materials") or []
        estimator = meta.get("estimator") or {}
        if (
            spec["material_key"] not in estimator_enabled_materials
            or estimator.get("validationStatus") != "passed"
        ):
            return {
                **base_result,
                "requires_manual_review": True,
                "manual_review_reasons": ["规格未精确命中，且该材料估算报价尚未通过验证"],
            }
        estimated = _estimate_pcb_manufacturing_by_model(tables, spec, meta)
        if not estimated:
            return {
                **base_result,
                "requires_manual_review": True,
                "manual_review_reasons": ["规格超出 JLC 已确认支持范围或局部覆盖不足，需人工复核"],
            }
        row = {
            "material_label": {
                "fr4": "FR-4",
                "fpc": "FPC软板",
                "aluminum": "铝基板",
            }.get(spec["material_key"], spec["material_key"]),
            "jlc_price_cny": estimated["jlc_price_cny"],
        }
        base_result.update(
            {
                "pricing_mode": "verified_estimate",
                "base_pricing_mode": "verified_estimate",
                "is_estimated": True,
                "confidence": estimated["confidence"],
                "estimator_basis": estimated["basis"],
                "estimator_average_distance": estimated.get("average_distance"),
                "estimator_local_coverage": estimated.get("local_coverage"),
                "estimator_extrapolation": estimated.get("extrapolation"),
                "estimator_model_type": estimated.get("model_type"),
            }
        )
    else:
        base_result["base_pricing_mode"] = "exact_lookup"

    jlc_price_cny = _to_number(row.get("jlc_price_cny"), 0)
    if not is_standard_process:
        if not allow_auto_estimate:
            return {
                **base_result,
                "requires_manual_review": True,
                "manual_review_reasons": [
                    "独立验收未通过，非标准工艺暂不自动调整，需人工复核"
                    f"（acceptance_status={acceptance_status or 'unknown'}）"
                ],
            }
        process_enabled_materials = meta.get("process_enabled_materials") or []
        process_model = meta.get("process_model") or {}
        zone_match = _match_pcb_process_enabled_zone(spec, meta)
        if (
            spec["material_key"] not in process_enabled_materials
            and not zone_match
        ) or process_model.get("validationStatus") not in ("passed", "partial_pass"):
            return {
                **base_result,
                "requires_manual_review": True,
                "manual_review_reasons": ["该材料的工艺调整尚未通过 live 组合验证"],
            }
        process_result = _apply_pcb_process_model(jlc_price_cny, spec, meta)
        if not process_result:
            return {
                **base_result,
                "requires_manual_review": True,
                "manual_review_reasons": ["该工艺组合没有已验证的价格依据，需人工复核"],
            }
        jlc_price_cny = process_result["jlc_price_cny"]
        base_result.update(
            {
                "pricing_mode": "verified_estimate",
                "is_estimated": True,
                "process_adjusted": True,
                "process_adjustments": process_result["adjustments"],
            }
        )

    # 确认生产稿：jlc_pcb_quote 已闭合加价（不参与工艺 enabled zone）
    from apps.simplequote.calculator.pcb_jlc_closed_addons import confirm_file_fee_cny

    confirm_fee = confirm_file_fee_cny(spec.get("confirm_production_file"))
    if confirm_fee is None:
        return {
            **base_result,
            "requires_manual_review": True,
            "manual_review_reasons": ["确认生产稿选项不在已校准范围"],
        }
    if confirm_fee:
        before_confirm = jlc_price_cny
        jlc_price_cny = round(jlc_price_cny + confirm_fee, 2)
        adjustments = list(base_result.get("process_adjustments") or [])
        adjustments.append(
            {
                "field": "confirm_production_file",
                "value": str(spec.get("confirm_production_file") or "none"),
                "method": "additive",
                "amount_cny": round(jlc_price_cny - before_confirm, 2),
            }
        )
        base_result["process_adjustments"] = adjustments
        base_result["process_adjusted"] = True

    # 风险门禁：命中 risk_zone 则 manual_review + fee=0
    risk_zone = _match_pcb_risk_zone(spec, meta)
    if risk_zone:
        action = risk_zone.get("action", "manual_review")
        if action == "manual_review":
            return {
                **base_result,
                "requires_manual_review": True,
                "manual_review_reasons": [f"规格命中风险分区：{risk_zone.get('id', 'unknown')}"],
                "risk_zone": risk_zone.get("id"),
                "risk_status": "manual_review",
            }
    margin_rate = _to_number(params.get("pcb_manufacturing_margin_rate"), 0.10)
    cny_to_krw = _to_number(params.get("cny_to_krw"), 232.4)
    customer_quote_cny = round(jlc_price_cny * (1 + margin_rate), 2)
    customer_quote_krw = round(customer_quote_cny * cny_to_krw)
    quote_range = _pcb_quote_range(
        jlc_mid_cny=jlc_price_cny,
        customer_mid_cny=customer_quote_cny,
        customer_mid_krw=customer_quote_krw,
        rate=range_rate,
    )
    return {
        **base_result,
        "material_label": row.get("material_label"),
        "jlc_estimate_cny": jlc_price_cny,
        "margin_rate": margin_rate,
        "customer_quote_cny": customer_quote_cny,
        "cny_to_krw": cny_to_krw,
        "customer_quote_krw": customer_quote_krw,
        "source": meta.get("source"),
        "sampled_at": meta.get("sampled_at"),
        "requires_manual_review": False,
        "manual_review_reasons": [],
        "risk_zone": None,
        "risk_status": "ok",
        **quote_range,
    }


def calc_pcb(inputs, params, tables=None):
    """PCB 开发成本：清单 A/B + 服务费 + 权重 + 广告折扣 + 简化配送费。"""
    from apps.simplequote.shipping import calc_pcb_shipping_simple

    base_no = inputs.get("base_item_no")
    if base_no is None:
        raise PcbQuoteError("请选择开发类型")

    base_item = _find_base_item(tables, base_no)
    if not base_item:
        raise PcbQuoteError("无效的开发类型编号")

    group = str(base_item.get("group", "A")).upper()
    if group not in ("A", "B"):
        raise PcbQuoteError("开发类型分组无效")

    alt_group = inputs.get("alt_group")
    if alt_group and str(alt_group).upper() != group:
        raise PcbQuoteError("A/B 类开发类型不可同时选择")

    weight_keys = inputs.get("weight_keys") or ["mass_production", "pcb_fr4", "qty_2", "size_100"]
    weight_map = {row.get("key"): row for row in (tables or {}).get("weights") or []}
    weight_sum = 0
    weight_details = []
    for key in weight_keys:
        row = weight_map.get(key)
        if not row:
            continue
        w = _to_number(row.get("weight"), 1)
        weight_sum += w
        weight_details.append({"key": key, "weight": w, "label": row.get("label_zh", key)})

    if weight_sum <= 0:
        weight_sum = 1

    base_fee = _to_number(base_item.get("base_fee_krw"), 0)
    dev_subtotal = round(base_fee * weight_sum)

    service_nos = inputs.get("service_nos") or []
    service_map = {_int(row.get("no")): row for row in (tables or {}).get("services") or []}
    service_total = 0
    service_items = []
    for no in service_nos:
        row = service_map.get(_int(no))
        if not row:
            continue
        fee = round(_to_number(row.get("fee_krw"), 0))
        service_total += fee
        service_items.append({"no": no, "label": row.get("label_zh", ""), "fee_krw": fee})

    dev_before_discount = dev_subtotal
    ad_consent = bool(inputs.get("ad_consent"))
    ad_discount = 0
    if ad_consent:
        rate = params.get("ad_discount_rate", 0.10)
        ad_discount = round(dev_before_discount * rate)
        dev_before_discount = dev_before_discount - ad_discount

    shipping_weight = _to_number(inputs.get("shipping_weight_kg"), 1)
    shipping = calc_pcb_shipping_simple(shipping_weight, params)
    shipping_fee = shipping.get("fee_krw", 0)
    manufacturing = _estimate_pcb_manufacturing(inputs, params, tables)
    manufacturing_fee = 0
    manufacturing_fee_min = 0
    manufacturing_fee_max = 0
    if manufacturing.get("enabled") and not manufacturing.get("requires_manual_review"):
        manufacturing_fee = round(_to_number(manufacturing.get("customer_quote_krw"), 0))
        manufacturing_fee_min = round(
            _to_number(manufacturing.get("customer_quote_krw_min"), manufacturing_fee)
        )
        manufacturing_fee_max = round(
            _to_number(manufacturing.get("customer_quote_krw_max"), manufacturing_fee)
        )

    fixed_total = dev_before_discount + service_total + shipping_fee
    total = fixed_total + manufacturing_fee
    total_min = fixed_total + manufacturing_fee_min
    total_max = fixed_total + manufacturing_fee_max

    breakdown = [
        {
            "label": f"开发费 / Dev ({base_item.get('label_zh', '')})",
            "amount": dev_subtotal,
        },
    ]
    for wd in weight_details:
        breakdown.append({"label": f"权重 / Weight {wd['label']}", "amount": wd["weight"]})
    if ad_discount:
        breakdown.append({"label": "广告折扣 / Ad discount -10%", "amount": -ad_discount})
    for svc in service_items:
        breakdown.append({"label": f"服务 / {svc['label']}", "amount": svc["fee_krw"]})
    if manufacturing_fee:
        breakdown.append(
            {
                "label": "PCB 样板制造费 / PCB sample fabrication",
                "amount": manufacturing_fee,
                "amount_min": manufacturing_fee_min,
                "amount_max": manufacturing_fee_max,
            }
        )
    breakdown.append({"label": "配送费 / Shipping (简化规则)", "amount": shipping_fee})

    return {
        "currency": "KRW",
        "base_item_no": _int(base_no),
        "base_item": base_item,
        "weight_sum": weight_sum,
        "weight_details": weight_details,
        "dev_subtotal": dev_subtotal,
        "ad_consent": ad_consent,
        "ad_discount": ad_discount,
        "dev_after_discount": dev_before_discount,
        "service_items": service_items,
        "service_total": service_total,
        "pcb_manufacturing": manufacturing,
        "pcb_manufacturing_fee": manufacturing_fee,
        "pcb_manufacturing_fee_min": manufacturing_fee_min,
        "pcb_manufacturing_fee_max": manufacturing_fee_max,
        "shipping": shipping,
        "shipping_fee": shipping_fee,
        "vat_included": False,
        "development_days": _int(base_item.get("days"), 0),
        "mold_fee": 0,
        "quantity": 1,
        "total": total,
        "total_min": total_min,
        "total_max": total_max,
        "breakdown": breakdown,
    }
