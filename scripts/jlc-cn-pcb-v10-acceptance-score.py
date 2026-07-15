"""One-shot scorer for v10 independent PCB acceptance samples."""

from __future__ import annotations

import copy
import hashlib
import importlib.util
import json
import sys
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from apps.simplequote.table_data import (  # noqa: E402
    PCB_BASE_PRICING,
    PCB_MANUFACTURING_PRICE_META,
    PCB_SERVICES,
    PCB_WEIGHTS,
)

V9_SCORER_PATH = ROOT / "scripts" / "jlc-cn-pcb-v9-acceptance-score.py"
spec = importlib.util.spec_from_file_location("pcb_v9_scorer", V9_SCORER_PATH)
v9 = importlib.util.module_from_spec(spec)
spec.loader.exec_module(v9)

TARGETS_PATH = ROOT / "scripts" / "jlc-cn-pcb-v10-acceptance-targets.json"
SAMPLES_PATH = ROOT / "scripts" / "jlc-cn-pcb-v10-acceptance-samples.json"
SPLIT_PATH = ROOT / "scripts" / "jlc-cn-pcb-v10-assert-split-report.json"
FINGERPRINT_PATH = ROOT / "scripts" / "jlc-cn-pcb-v10-acceptance-fingerprint.json"
CONSUMPTION_PATH = ROOT / "scripts" / "jlc-cn-pcb-v10-acceptance-consumption.json"
CANDIDATE_PATH = ROOT / "scripts" / "jlc-cn-pcb-v10-candidate-price-list.json"
MODEL_FINGERPRINT_PATH = ROOT / "scripts" / "jlc-cn-pcb-v10-model-fingerprint.json"
JSON_OUT = ROOT / "scripts" / "jlc-cn-pcb-v10-acceptance-report.json"
SCORED_OUT = ROOT / "scripts" / "jlc-cn-pcb-v10-acceptance-scored.json"
MD_OUT = ROOT / "docs" / "pcb-quote-v10-accuracy-test-report.md"
MATERIALS = ("fr4", "fpc", "aluminum")


def load_json(path: Path, default):
    if not path.exists():
        return default
    return json.loads(path.read_text(encoding="utf-8"))


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
    meta["validation_status"] = candidate.get("validationStatus", "pending_live_sampling")
    normalized = []
    for row in candidate.get("rows") or []:
        normalized_row = {
            "material_key": row.get("materialKey") or row.get("material_key"),
            "material_label": row.get("materialLabel") or row.get("material_label"),
            "layers": int(row.get("layers") or 0),
            "width_mm": float(row.get("widthMm") or row.get("width_mm") or 0),
            "height_mm": float(row.get("heightMm") or row.get("height_mm") or 0),
            "quantity": int(row.get("quantity") or 0),
            "jlc_price_cny": float(row.get("jlcPriceCny") or row.get("jlc_price_cny") or 0),
            "enabled": row.get("enabled", True),
        }
        if (
            normalized_row["material_key"] not in MATERIALS
            or normalized_row["layers"] <= 0
            or normalized_row["width_mm"] <= 0
            or normalized_row["height_mm"] <= 0
            or normalized_row["quantity"] <= 0
            or normalized_row["jlc_price_cny"] <= 0
        ):
            raise SystemExit("v10 candidate contains invalid or incomplete normalized rows")
        normalized.append(normalized_row)
    if not normalized:
        raise SystemExit("v10 candidate has no runnable normalized price rows")
    return {
        "base_pricing": PCB_BASE_PRICING,
        "services": PCB_SERVICES,
        "weights": PCB_WEIGHTS,
        "manufacturing_price_list": normalized,
        "manufacturing_price_meta": [meta],
    }


def main():
    now = datetime.now(timezone.utc).isoformat()
    targets = load_json(TARGETS_PATH, [])
    target_ids = {row.get("id") for row in targets}
    samples = load_json(SAMPLES_PATH, [])
    extras = [row.get("id") for row in samples if row.get("id") not in target_ids]
    if extras:
        raise SystemExit(f"v10 samples contain {len(extras)} rows outside frozen targets")
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
        and (model_fingerprint.get("runtimePreflight") or {}).get("ok") is True
    )
    consumption = load_json(CONSUMPTION_PATH, {})
    if (
        consumption.get("consumed")
        and not consumption.get("invalidatedAt")
        and consumption.get("fingerprint") == fingerprint.get("hash")
    ):
        raise SystemExit(f"v10 fingerprint already consumed: {fingerprint.get('hash')}")

    stable, rejected = v9.stable_triples(samples)
    counts = Counter(row.get("materialKey") or row.get("material_key") for row in stable)
    complete = all(counts[material] >= 40 for material in MATERIALS)
    tables = candidate_tables() if complete else None
    scored = [v9.score_row(row, tables) for row in stable] if complete else []
    auto = [row for row in scored if row["relativeError"] is not None]
    auto_counts = Counter(row["materialKey"] for row in auto)
    coverage = round(len(auto) / len(stable), 4) if stable else 0
    coverage_by_material = {
        material: round(auto_counts[material] / counts[material], 4) if counts[material] else 0
        for material in MATERIALS
    }
    model_runnable = all(auto_counts[material] > 0 for material in MATERIALS)
    by_material_errors = defaultdict(list)
    for row in auto:
        by_material_errors[row["materialKey"]].append(row["relativeError"])
    overall = v9.metrics([row["relativeError"] for row in auto])
    by_material = {
        material: v9.metrics(by_material_errors[material]) for material in MATERIALS
    }
    segmented = defaultdict(lambda: {"total": 0, "autoQuoted": 0, "errors": []})
    for row in scored:
        segment = segmented[v9.segment_key(row)]
        segment["total"] += 1
        if row["relativeError"] is not None:
            segment["autoQuoted"] += 1
            segment["errors"].append(row["relativeError"])
    manual_reasons = Counter(
        reason
        for row in scored
        if row["requiresManualReview"]
        for reason in row.get("manualReviewReasons") or ["unknown"]
    )
    gates = {
        "independenceOk": bool(split.get("ok")),
        "runtimePreflightOk": bool(split.get("readyForFinalAcceptance")),
        "fingerprintOk": bool((split.get("fingerprintCheck") or {}).get("ok")),
        "modelFingerprintOk": model_fingerprint_ok,
        "modelRunnable": model_runnable,
        "freshPerMaterialAtLeast40": complete,
        "overallCoverageAtLeast90": coverage >= 0.90,
        "materialsCoverageAtLeast90": all(
            coverage_by_material[material] >= 0.90 for material in MATERIALS
        ),
        "overallHit10AtLeast90": (overall.get("hitRate10") or 0) >= 0.90,
        "overallHit20AtLeast95": (overall.get("hitRate20") or 0) >= 0.95,
        "overallMapeAtMost8": (overall.get("mape") or 1) <= 0.08,
        "overallMaxErrAtMost20": (overall.get("maxRelativeError") or 1) <= 0.20,
        "materialsHit20Ok": all(
            (by_material[material].get("hitRate20") or 0) >= 0.95 for material in MATERIALS
        ),
        "materialsMaxErrOk": all(
            (by_material[material].get("maxRelativeError") or 1) <= 0.20
            for material in MATERIALS
        ),
    }
    status = "pending_live_acceptance"
    if complete and not model_runnable:
        status = "invalid_scoring_pipeline"
    elif complete:
        status = "passed" if all(gates.values()) else "failed"
    report = {
        "generatedAt": now,
        "priceVersion": "jlc-cn-pcb-v10-candidate",
        "status": status,
        "pass": status == "passed",
        "fingerprint": fingerprint,
        "modelFingerprint": model_fingerprint,
        "fingerprintConsumed": complete and model_runnable,
        "gates": gates,
        "materialCounts": dict(counts),
        "targets": len(targets),
        "sampleRows": len(samples),
        "freshUnique": len(stable),
        "rejectedRepeatGroups": rejected,
        "autoQuoted": len(auto),
        "manualReview": sum(row["requiresManualReview"] for row in scored),
        "autoQuoteCoverage": coverage,
        "autoQuoteCoverageByMaterial": coverage_by_material,
        "manualReviewReasonCounts": dict(manual_reasons),
        "segmentedDiagnostics": {
            key: {
                "total": value["total"],
                "autoQuoted": value["autoQuoted"],
                "coverage": round(value["autoQuoted"] / value["total"], 4),
                "metrics": v9.metrics(value["errors"]),
            }
            for key, value in sorted(segmented.items())
        },
        "overall": overall,
        "byMaterial": by_material,
        "fallbackVersionIfFailed": "jlc-cn-pcb-v6-20260712",
    }
    v9.atomic_write(JSON_OUT, report)
    v9.atomic_write(SCORED_OUT, {"generatedAt": now, "rows": scored})
    if complete and model_runnable:
        v9.atomic_write(
            CONSUMPTION_PATH,
            {
                "fingerprint": fingerprint.get("hash"),
                "consumed": True,
                "consumedAt": now,
                "decision": status,
                "published": False,
                "report": str(JSON_OUT.relative_to(ROOT)).replace("\\", "/"),
            },
        )
    lines = [
        "# PCB 报价第十版准确度测试报告",
        "",
        f"- 生成时间：{now}",
        f"- 验收状态：**{status}**",
        f"- 冻结指纹：`{fingerprint.get('hash', '—')}`",
        f"- 稳定规格：FR-4 {counts['fr4']} / FPC {counts['fpc']} / 铝基 {counts['aluminum']}",
        f"- 自动报价覆盖率：总体 {v9.pct(coverage)}；FR-4 {v9.pct(coverage_by_material['fr4'])}；"
        f"FPC {v9.pct(coverage_by_material['fpc'])}；铝基 {v9.pct(coverage_by_material['aluminum'])}",
        "",
        "## 总体指标",
        "",
        f"- Hit@10：{v9.pct(overall['hitRate10'])}",
        f"- Hit@20：{v9.pct(overall['hitRate20'])}",
        f"- MAPE：{v9.pct(overall['mape'])}",
        f"- 最大相对误差：{v9.pct(overall['maxRelativeError'])}",
        "",
        "## 发布结论",
        "",
        "- 全部门禁通过，可进入原子发布。" if status == "passed"
        else "- 保持活动版本 `jlc-cn-pcb-v6-20260712`，不得发布 v10。",
        "",
    ]
    MD_OUT.write_text("\n".join(lines), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
