"""One-shot scorer for v9 independent PCB acceptance samples."""

from __future__ import annotations

import copy
import hashlib
import json
import statistics
import sys
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from apps.simplequote.calculator import DEFAULT_PARAMS, calc_pcb  # noqa: E402
from apps.simplequote.table_data import (  # noqa: E402
    PCB_BASE_PRICING,
    PCB_MANUFACTURING_PRICE_LIST,
    PCB_MANUFACTURING_PRICE_META,
    PCB_SERVICES,
    PCB_WEIGHTS,
)

TARGETS_PATH = ROOT / "scripts" / "jlc-cn-pcb-v9-acceptance-targets.json"
SAMPLES_PATH = ROOT / "scripts" / "jlc-cn-pcb-v9-acceptance-samples.json"
SPLIT_PATH = ROOT / "scripts" / "jlc-cn-pcb-v9-assert-split-report.json"
FINGERPRINT_PATH = ROOT / "scripts" / "jlc-cn-pcb-v9-acceptance-fingerprint.json"
CONSUMPTION_PATH = ROOT / "scripts" / "jlc-cn-pcb-v9-acceptance-consumption.json"
CANDIDATE_PATH = ROOT / "scripts" / "jlc-cn-pcb-v9-candidate-price-list.json"
MODEL_FINGERPRINT_PATH = ROOT / "scripts" / "jlc-cn-pcb-v9-model-fingerprint.json"
JSON_OUT = ROOT / "scripts" / "jlc-cn-pcb-v9-acceptance-report.json"
SCORED_OUT = ROOT / "scripts" / "jlc-cn-pcb-v9-acceptance-scored.json"
MD_OUT = ROOT / "docs" / "pcb-quote-v9-accuracy-test-report.md"
MATERIALS = ("fr4", "fpc", "aluminum")


def load_json(path: Path, default):
    if not path.exists():
        return default
    return json.loads(path.read_text(encoding="utf-8"))


def atomic_write(path: Path, payload):
    temp = path.with_suffix(path.suffix + ".tmp")
    temp.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    temp.replace(path)


def is_fresh_dom(row: dict) -> bool:
    row_id = str(row.get("id") or row.get("baseSampleId") or "")
    notes = str(row.get("notes") or "")
    source = str((row.get("pageFingerprint") or {}).get("source") or "")
    return bool(
        row
        and not row.get("error")
        and row.get("priceSource") == "dom"
        and float(row.get("domPriceCny") or 0) > 0
        and row.get("quarantined") is not True
        and row.get("diagnosticOnly") is not True
        and row.get("sampleRole") != "diagnostic_only"
        and "V7-ACC" not in row_id
        and "V8-ACC" not in row_id
        and "bootstrapped" not in notes
        and source not in {"bootstrapped_from_v6_dom", "recovered_from_run_log"}
    )


def stable_triples(rows: list[dict]) -> tuple[list[dict], list[dict]]:
    groups = defaultdict(list)
    for row in rows:
        group_id = row.get("baseSampleId") or str(row.get("id") or "").rsplit("-R", 1)[0]
        groups[group_id].append(row)
    accepted, rejected = [], []
    for group_id, group in groups.items():
        fresh = [row for row in group if is_fresh_dom(row)]
        prices = [float(row["domPriceCny"]) for row in fresh]
        mean = statistics.fmean(prices) if prices else 0
        cv = statistics.pstdev(prices) / mean if len(prices) >= 2 and mean else None
        def selected_ok(row: dict, field: str, state: dict) -> bool:
            if state.get("selected") is True:
                return True
            return (
                field == "solderMaskCoverage"
                and state.get("requested") == "过孔盖油"
                and (
                    "过孔盖油已经免费升级为过孔塞油" in str(row.get("priceText") or "")
                    or (
                        (row.get("materialKey") or row.get("material_key")) == "fr4"
                        and int(row.get("layers") or 0) == 4
                    )
                )
            )

        process_ok = all(
            all(
                selected_ok(row, field, state)
                for field, state in (row.get("selectedProcessOptions") or {}).items()
            )
            for row in fresh
        )
        if len(group) == 3 and len(fresh) == 3 and cv is not None and cv <= 0.02 and process_ok:
            representative = dict(fresh[0])
            representative["domPriceCny"] = statistics.median(prices)
            representative["stableRepeatCount"] = 3
            representative["repeatCv"] = cv
            accepted.append(representative)
        else:
            rejected.append(
                {
                    "baseSampleId": group_id,
                    "rows": len(group),
                    "freshRows": len(fresh),
                    "cv": cv,
                    "processOk": process_ok,
                }
            )
    return accepted, rejected


def quote_params():
    params = dict(DEFAULT_PARAMS["pcb"])
    params.update(
        {
            "pcb_shipping_under_1kg": 24000,
            "pcb_shipping_per_kg": 11600,
            "cny_to_krw": 232.4,
            "pcb_manufacturing_margin_rate": 0.10,
        }
    )
    return params


def candidate_tables():
    candidate = load_json(CANDIDATE_PATH, {})
    meta = copy.deepcopy((PCB_MANUFACTURING_PRICE_META or [{}])[0])
    for source_key, target_key in (
        ("estimator", "estimator"),
        ("estimatorGuards", "estimator_guards"),
        ("estimatorEnabledMaterials", "estimator_enabled_materials"),
        ("riskZones", "risk_zones"),
        ("processModel", "process_model"),
        ("processEnabledMaterials", "process_enabled_materials"),
        ("processEnabledZones", "process_enabled_zones"),
    ):
        if source_key in candidate:
            meta[target_key] = candidate[source_key]
    meta["acceptance_status"] = "passed"
    meta["validation_status"] = candidate.get("validationStatus", "passed")
    normalized_rows = [
        {
            "material_key": row.get("materialKey") or row.get("material_key"),
            "material_label": row.get("materialLabel") or row.get("material_label"),
            "layers": row.get("layers"),
            "width_mm": row.get("widthMm") or row.get("width_mm"),
            "height_mm": row.get("heightMm") or row.get("height_mm"),
            "quantity": row.get("quantity"),
            "jlc_price_cny": row.get("jlcPriceCny") or row.get("jlc_price_cny"),
            "enabled": row.get("enabled", True),
        }
        for row in (candidate.get("rows") or PCB_MANUFACTURING_PRICE_LIST)
    ]
    return {
        "base_pricing": PCB_BASE_PRICING,
        "services": PCB_SERVICES,
        "weights": PCB_WEIGHTS,
        "manufacturing_price_list": normalized_rows,
        "manufacturing_price_meta": [meta],
    }


def metrics(errors: list[float]) -> dict:
    if not errors:
        return {
            "n": 0,
            "hitRate10": None,
            "hitRate20": None,
            "mape": None,
            "maxRelativeError": None,
        }
    return {
        "n": len(errors),
        "hitRate10": round(sum(error <= 0.10 for error in errors) / len(errors), 4),
        "hitRate20": round(sum(error <= 0.20 for error in errors) / len(errors), 4),
        "mape": round(statistics.fmean(errors), 4),
        "maxRelativeError": round(max(errors), 4),
    }


def segment_key(row: dict) -> str:
    area = float(row.get("widthMm") or 0) * float(row.get("heightMm") or 0)
    quantity = int(row.get("quantity") or 0)
    area_segment = "small" if area <= 6000 else ("medium" if area <= 16000 else "large")
    quantity_segment = "low" if quantity <= 20 else ("medium" if quantity <= 75 else "high")
    return f"{row.get('materialKey')}|L{row.get('layers')}|{area_segment}|{quantity_segment}"


def score_row(row: dict, tables: dict) -> dict:
    result = calc_pcb(
        {
            "base_item_no": 2,
            "weight_keys": ["mass_production", "pcb_fr4", "qty_2", "size_100"],
            "service_nos": [],
            "ad_consent": False,
            "shipping_weight_kg": 1,
            "include_pcb_manufacturing": True,
            "mfg_material": row.get("materialKey") or row.get("material_key"),
            "mfg_layers": row.get("layers"),
            "mfg_width_mm": row.get("widthMm") or row.get("width_mm"),
            "mfg_height_mm": row.get("heightMm") or row.get("height_mm"),
            "mfg_quantity": row.get("quantity"),
            "mfg_board_thickness": row.get("boardThickness"),
            "mfg_solder_color": row.get("solderColor"),
            "mfg_surface_finish": row.get("surfaceFinish"),
            "mfg_copper_thickness": row.get("copperThickness"),
            "mfg_solder_mask_coverage": row.get("solderMaskCoverage"),
            "mfg_panel_design_count": row.get("panelDesignCount"),
        },
        quote_params(),
        tables,
    )
    estimate = result["pcb_manufacturing"]
    actual = float(row["domPriceCny"])
    predicted = None if estimate.get("requires_manual_review") else float(estimate.get("jlc_estimate_cny") or 0)
    relative_error = None if predicted is None else abs(predicted - actual) / actual
    return {
        "id": row.get("id"),
        "baseSampleId": row.get("baseSampleId"),
        "materialKey": row.get("materialKey") or row.get("material_key"),
        "layers": row.get("layers"),
        "widthMm": row.get("widthMm") or row.get("width_mm"),
        "heightMm": row.get("heightMm") or row.get("height_mm"),
        "quantity": row.get("quantity"),
        "actualCny": actual,
        "predictedCny": predicted,
        "relativeError": relative_error,
        "requiresManualReview": bool(estimate.get("requires_manual_review")),
        "manualReviewReasons": estimate.get("manual_review_reasons") or [],
        "pricingMode": estimate.get("pricing_mode"),
        "confidence": estimate.get("confidence"),
        "averageDistance": estimate.get("estimator_average_distance"),
        "localCoverage": estimate.get("estimator_local_coverage"),
        "extrapolation": estimate.get("estimator_extrapolation"),
        "estimatorBasis": estimate.get("estimator_basis") or [],
        "selectedProcessOptions": row.get("selectedProcessOptions"),
        "pageFingerprint": row.get("pageFingerprint"),
    }


def pct(value):
    return "—" if value is None else f"{value * 100:.2f}%"


def main():
    now = datetime.now(timezone.utc).isoformat()
    targets = load_json(TARGETS_PATH, [])
    target_ids = {row.get("id") for row in targets}
    samples = load_json(SAMPLES_PATH, [])
    extras = [row.get("id") for row in samples if row.get("id") not in target_ids]
    if extras:
        raise SystemExit(f"v9 samples contain {len(extras)} rows outside frozen targets")
    split = load_json(SPLIT_PATH, {"ok": False})
    fingerprint = load_json(FINGERPRINT_PATH, {})
    model_fingerprint = load_json(MODEL_FINGERPRINT_PATH, {})
    candidate_hash = (
        f"sha256_{hashlib.sha256(CANDIDATE_PATH.read_bytes()).hexdigest()}"
        if CANDIDATE_PATH.exists()
        else None
    )
    model_fingerprint_ok = bool(
        candidate_hash
        and model_fingerprint.get("hash") == candidate_hash
        and model_fingerprint.get("acceptanceFingerprint") == fingerprint.get("hash")
    )
    consumption = load_json(CONSUMPTION_PATH, {})
    if (
        consumption.get("consumed")
        and not consumption.get("invalidatedAt")
        and consumption.get("fingerprint") == fingerprint.get("hash")
    ):
        raise SystemExit(f"v9 fingerprint already consumed: {fingerprint.get('hash')}")

    stable, rejected = stable_triples(samples)
    counts = defaultdict(int)
    for row in stable:
        counts[row.get("materialKey") or row.get("material_key")] += 1
    complete_for_decision = all(counts[material] >= 40 for material in MATERIALS)
    scored = [score_row(row, candidate_tables()) for row in stable] if complete_for_decision else []
    auto = [row for row in scored if row["relativeError"] is not None]
    auto_materials = {row["materialKey"] for row in auto}
    model_runnable = bool(auto) and all(material in auto_materials for material in MATERIALS)
    auto_counts = Counter(row["materialKey"] for row in auto)
    coverage_by_material = {
        material: round(auto_counts[material] / counts[material], 4) if counts[material] else 0
        for material in MATERIALS
    }
    overall_coverage = round(len(auto) / len(stable), 4) if stable else 0
    manual_reason_counts = Counter(
        reason
        for row in scored
        if row["requiresManualReview"]
        for reason in row.get("manualReviewReasons") or ["unknown"]
    )
    segmented = defaultdict(lambda: {"total": 0, "autoQuoted": 0, "errors": []})
    for row in scored:
        segment = segmented[segment_key(row)]
        segment["total"] += 1
        if row["relativeError"] is not None:
            segment["autoQuoted"] += 1
            segment["errors"].append(row["relativeError"])
    by_material_errors = defaultdict(list)
    for row in auto:
        by_material_errors[row["materialKey"]].append(row["relativeError"])
    overall = metrics([row["relativeError"] for row in auto])
    by_material = {material: metrics(by_material_errors[material]) for material in MATERIALS}
    gates = {
        "independenceOk": bool(split.get("ok")),
        "fingerprintOk": bool((split.get("fingerprintCheck") or {}).get("ok")),
        "modelFingerprintOk": model_fingerprint_ok,
        "modelRunnable": model_runnable,
        "freshPerMaterialAtLeast40": all(counts[material] >= 40 for material in MATERIALS),
        "overallHit10AtLeast90": (overall.get("hitRate10") or 0) >= 0.90,
        "overallHit20AtLeast95": (overall.get("hitRate20") or 0) >= 0.95,
        "overallMapeAtMost8": (overall.get("mape") or 1) <= 0.08,
        "overallMaxErrAtMost20": (overall.get("maxRelativeError") or 1) <= 0.20,
        "materialsHit20Ok": all((by_material[m].get("hitRate20") or 0) >= 0.95 for m in MATERIALS),
        "materialsMaxErrOk": all((by_material[m].get("maxRelativeError") or 1) <= 0.20 for m in MATERIALS),
    }
    status = "pending_live_acceptance"
    if complete_for_decision and not model_runnable:
        status = "invalid_scoring_pipeline"
    elif complete_for_decision:
        status = "passed" if all(gates.values()) else "failed"
    report = {
        "generatedAt": now,
        "priceVersion": "jlc-cn-pcb-v9-candidate",
        "status": status,
        "pass": status == "passed",
        "fingerprint": fingerprint,
        "modelFingerprint": model_fingerprint,
        "fingerprintConsumed": complete_for_decision and model_runnable,
        "gates": gates,
        "materialCounts": dict(counts),
        "targets": len(targets),
        "sampleRows": len(samples),
        "freshUnique": len(stable),
        "rejectedRepeatGroups": rejected,
        "autoQuoted": len(auto),
        "manualReview": sum(row["requiresManualReview"] for row in scored),
        "autoQuoteCoverage": overall_coverage,
        "autoQuoteCoverageByMaterial": coverage_by_material,
        "manualReviewReasonCounts": dict(manual_reason_counts),
        "segmentedDiagnostics": {
            key: {
                "total": value["total"],
                "autoQuoted": value["autoQuoted"],
                "coverage": round(value["autoQuoted"] / value["total"], 4) if value["total"] else 0,
                "metrics": metrics(value["errors"]),
            }
            for key, value in sorted(segmented.items())
        },
        "overall": overall,
        "byMaterial": by_material,
        "fallbackVersionIfFailed": "jlc-cn-pcb-v6-20260712",
    }
    atomic_write(JSON_OUT, report)
    atomic_write(SCORED_OUT, {"generatedAt": now, "rows": scored})
    if complete_for_decision and model_runnable:
        atomic_write(
            CONSUMPTION_PATH,
            {
                "fingerprint": fingerprint.get("hash"),
                "consumed": True,
                "consumedAt": now,
                "decision": status,
                "report": str(JSON_OUT.relative_to(ROOT)).replace("\\", "/"),
                "invalidatedAttempts": [
                    *(consumption.get("invalidatedAttempts") or []),
                    *(
                        [consumption]
                        if consumption.get("invalidatedAt")
                        else []
                    ),
                ],
            },
        )

    lines = [
        "# PCB 报价第九版准确度测试报告",
        "",
        f"- 生成时间：{now}",
        f"- 验收状态：**{status}**",
        f"- 冻结指纹：`{fingerprint.get('hash', '—')}`",
        f"- 指纹已消费：`{complete_for_decision}`",
        f"- 有效稳定规格：FR-4 {counts['fr4']} / FPC {counts['fpc']} / 铝基 {counts['aluminum']}",
        "",
        "## 总体指标",
        "",
        f"- Hit@10：{pct(overall['hitRate10'])}",
        f"- Hit@20：{pct(overall['hitRate20'])}",
        f"- MAPE：{pct(overall['mape'])}",
        f"- 最大相对误差：{pct(overall['maxRelativeError'])}",
        "",
        "## 发布结论",
        "",
        "- 三材料门禁全部通过，可进入原子发布。" if status == "passed"
        else "- 保持活动版本 `jlc-cn-pcb-v6-20260712`，不得发布 v9。",
        "",
    ]
    MD_OUT.write_text("\n".join(lines), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
