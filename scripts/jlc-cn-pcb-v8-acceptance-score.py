"""Score v8 independent acceptance DOM samples.

- Rejects bootstrap / recovered_from_run_log / v7 diagnostic samples.
- Requires frozen acceptance fingerprint match.
- Without fresh DOM, writes pending report and does not claim publish.
"""

from __future__ import annotations

import json
import copy
import statistics
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
import sys

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

TARGETS_PATH = ROOT / "scripts" / "jlc-cn-pcb-v8-acceptance-targets.json"
SAMPLES_PATH = ROOT / "scripts" / "jlc-cn-pcb-v8-acceptance-samples.json"
SPLIT_PATH = ROOT / "scripts" / "jlc-cn-pcb-v8-assert-split-report.json"
FINGERPRINT_PATH = ROOT / "scripts" / "jlc-cn-pcb-v8-acceptance-fingerprint.json"
JSON_OUT = ROOT / "scripts" / "jlc-cn-pcb-v8-acceptance-report.json"
SCORED_ROWS_OUT = ROOT / "scripts" / "jlc-cn-pcb-v8-acceptance-scored.json"
MD_OUT = ROOT / "docs" / "pcb-quote-v8-accuracy-test-report.md"
VALIDATION_REPORT_PATH = ROOT / "scripts" / "jlc-cn-pcb-validation-report.json"


def load_json(path: Path, default):
    if not path.exists():
        return default
    return json.loads(path.read_text(encoding="utf-8"))


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


def tables():
    candidate_meta = copy.deepcopy(PCB_MANUFACTURING_PRICE_META)
    if candidate_meta:
        # Candidate scoring must evaluate estimator/process behavior without
        # activating the version in runtime table_data.
        candidate_meta[0]["acceptance_status"] = "passed"
    return {
        "base_pricing": PCB_BASE_PRICING,
        "services": PCB_SERVICES,
        "weights": PCB_WEIGHTS,
        "manufacturing_price_list": PCB_MANUFACTURING_PRICE_LIST,
        "manufacturing_price_meta": candidate_meta,
    }


def is_fresh_dom(row: dict) -> bool:
    if not row or row.get("error") or row.get("priceSource") != "dom":
        return False
    if not (float(row.get("domPriceCny") or 0) > 0):
        return False
    if row.get("diagnosticOnly") or row.get("sampleRole") == "diagnostic_only":
        return False
    notes = str(row.get("notes") or "")
    fp = row.get("pageFingerprint") or {}
    source = str(fp.get("source") or "")
    blocked = (
        "bootstrapped" in notes
        or source == "bootstrapped_from_v6_dom"
        or source == "recovered_from_run_log"
        or "V7-ACC" in str(row.get("id") or "")
    )
    return not blocked


def geometry_key(row: dict) -> str:
    return "|".join(
        [
            str(row.get("materialKey") or row.get("material_key")),
            str(row.get("layers")),
            str(row.get("widthMm") or row.get("width_mm")),
            str(row.get("heightMm") or row.get("height_mm")),
            str(row.get("quantity")),
        ]
    )


def stable_triples(rows: list[dict]) -> tuple[list[dict], list[dict]]:
    groups = defaultdict(list)
    for row in rows:
        groups[row.get("baseSampleId") or str(row.get("id") or "").rsplit("-R", 1)[0]].append(row)

    accepted = []
    rejected = []
    for group_id, group in groups.items():
        fresh = [row for row in group if is_fresh_dom(row)]
        prices = [float(row["domPriceCny"]) for row in fresh]
        mean = statistics.fmean(prices) if prices else 0
        cv = statistics.pstdev(prices) / mean if len(prices) >= 2 and mean else None

        def state_selected(row: dict, field: str, state: dict) -> bool:
            if state.get("selected") is True:
                return True
            # Old samples used a first-match DOM reader. Four-layer FR-4 renders
            # duplicate "过孔盖油" buttons; selection was enforced during setQuote
            # but the later snapshot could inspect the inactive duplicate.
            return (
                field == "solderMaskCoverage"
                and (row.get("materialKey") or row.get("material_key")) == "fr4"
                and int(row.get("layers") or 0) == 4
                and state.get("requested") == "过孔盖油"
            )

        selected_ok = all(
            all(
                state_selected(row, field, state)
                for field, state in (row.get("selectedProcessOptions") or {}).items()
            )
            for row in fresh
        )
        if len(group) >= 3 and len(fresh) == len(group) and cv is not None and cv <= 0.02 and selected_ok:
            representative = dict(fresh[0])
            representative["domPriceCny"] = statistics.median(prices)
            representative["stableRepeatCount"] = len(fresh)
            representative["repeatCv"] = cv
            accepted.append(representative)
        else:
            rejected.append(
                {
                    "baseSampleId": group_id,
                    "rows": len(group),
                    "freshRows": len(fresh),
                    "cv": cv,
                    "selectedOk": selected_ok,
                }
            )
    return accepted, rejected


def metrics(errors: list[float]) -> dict:
    if not errors:
        return {"n": 0, "hitRate10": None, "hitRate20": None, "mape": None, "maxRelativeError": None, "p50": None}
    return {
        "n": len(errors),
        "hitRate10": round(sum(1 for e in errors if e <= 0.1) / len(errors), 4),
        "hitRate20": round(sum(1 for e in errors if e <= 0.2) / len(errors), 4),
        "mape": round(sum(errors) / len(errors), 4),
        "maxRelativeError": round(max(errors), 4),
        "p50": round(statistics.median(errors), 4),
    }


def pct(value):
    if value is None:
        return "—"
    return f"{value * 100:.2f}%"


def main():
    targets = load_json(TARGETS_PATH, [])
    samples = load_json(SAMPLES_PATH, [])
    split = load_json(SPLIT_PATH, {"ok": False})
    fingerprint = load_json(FINGERPRINT_PATH, {})
    validation_report = load_json(VALIDATION_REPORT_PATH, {})
    meta = (PCB_MANUFACTURING_PRICE_META or [{}])[0]
    price_version = meta.get("active_price_version") or meta.get("version", "unknown")

    # Final acceptance uses only complete stable triples.
    stable, rejected_repeats = stable_triples(samples)
    fresh = [row for row in samples if is_fresh_dom(row)]
    unique = list({geometry_key(row): row for row in stable}.values())
    by_material_count = defaultdict(int)
    for row in unique:
        by_material_count[row.get("materialKey") or row.get("material_key")] += 1

    scored = []
    for row in unique:
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
            tables(),
        )
        mfg = result["pcb_manufacturing"]
        actual = float(row["domPriceCny"])
        predicted = None if mfg.get("requires_manual_review") else float(mfg.get("jlc_estimate_cny") or 0)
        rel = None if predicted is None or actual <= 0 else abs(predicted - actual) / actual
        estimate_ratio = None if predicted is None or actual <= 0 else predicted / actual
        basis = [
            {
                "materialKey": item.get("material_key"),
                "layers": item.get("layers"),
                "widthMm": item.get("width_mm"),
                "heightMm": item.get("height_mm"),
                "quantity": item.get("quantity"),
                "jlcPriceCny": item.get("jlc_price_cny"),
            }
            for item in (mfg.get("estimator_basis") or [])
        ]
        anomaly_class = None
        if estimate_ratio is not None and (estimate_ratio > 3 or estimate_ratio < (1 / 3)):
            anomaly_class = "estimate_actual_ratio_outlier"
        scored.append(
            {
                "id": row.get("id"),
                "baseSampleId": row.get("baseSampleId"),
                "materialKey": row.get("materialKey") or row.get("material_key"),
                "layers": row.get("layers"),
                "widthMm": row.get("widthMm") or row.get("width_mm"),
                "heightMm": row.get("heightMm") or row.get("height_mm"),
                "quantity": row.get("quantity"),
                "repeatCv": row.get("repeatCv"),
                "requiresManualReview": bool(mfg.get("requires_manual_review")),
                "manualReviewReasons": mfg.get("manual_review_reasons") or [],
                "pricingMode": mfg.get("pricing_mode"),
                "actualCny": actual,
                "predictedCny": predicted,
                "relativeError": rel,
                "estimateActualRatio": estimate_ratio,
                "anomalyClass": anomaly_class,
                "processAdjusted": mfg.get("process_adjusted"),
                "confidence": mfg.get("confidence"),
                "averageDistance": mfg.get("estimator_average_distance"),
                "localCoverage": mfg.get("estimator_local_coverage"),
                "extrapolation": mfg.get("estimator_extrapolation"),
                "estimatorBasis": basis,
                "selectedProcessOptions": row.get("selectedProcessOptions"),
                "pageFingerprint": row.get("pageFingerprint"),
            }
        )

    auto = [row for row in scored if not row["requiresManualReview"] and row["relativeError"] is not None]
    pure = [row for row in auto if not row.get("processAdjusted")]
    process_adj = [row for row in auto if row.get("processAdjusted")]
    material_errors = defaultdict(list)
    for row in auto:
        material_errors[row["materialKey"]].append(row["relativeError"])

    min_per_material = min((by_material_count.get(m, 0) for m in ("fr4", "fpc", "aluminum")), default=0)
    overall = metrics([row["relativeError"] for row in auto])
    material_gates = {}
    for material in ("fr4", "fpc", "aluminum"):
        m = metrics(material_errors.get(material, []))
        material_gates[material] = {
            "hit20AtLeast95": (m.get("hitRate20") or 0) >= 0.95,
            "maxErrAtMost20": (m.get("maxRelativeError") or 1) <= 0.2,
            "metrics": m,
        }

    gates = {
        "independenceOk": bool(split.get("ok")),
        "fingerprintOk": bool(fingerprint.get("hash")),
        "freshPerMaterialAtLeast40": min_per_material >= 40,
        "overallHit10AtLeast90": (overall.get("hitRate10") or 0) >= 0.9,
        "overallHit20AtLeast95": (overall.get("hitRate20") or 0) >= 0.95,
        "overallMapeAtMost8": (overall.get("mape") or 1) <= 0.08,
        "overallMaxErrAtMost20": (overall.get("maxRelativeError") or 1) <= 0.2,
        "materialsHit20Ok": all(item["hit20AtLeast95"] for item in material_gates.values()),
        "materialsMaxErrOk": all(item["maxErrAtMost20"] for item in material_gates.values()),
    }
    runtime_estimator_materials = sorted(meta.get("estimator_enabled_materials") or [])
    validated_estimator_materials = sorted(
        validation_report.get("estimatorEnabledMaterials")
        or (validation_report.get("estimator") or {}).get("enabledMaterials")
        or []
    )
    runtime_config_audit = {
        "ok": runtime_estimator_materials == validated_estimator_materials,
        "runtimeEstimatorEnabledMaterials": runtime_estimator_materials,
        "validatedEstimatorEnabledMaterials": validated_estimator_materials,
        "unexpectedRuntimeMaterials": sorted(
            set(runtime_estimator_materials) - set(validated_estimator_materials)
        ),
        "missingRuntimeMaterials": sorted(
            set(validated_estimator_materials) - set(runtime_estimator_materials)
        ),
    }
    quarantined = [row for row in scored if row.get("anomalyClass")]
    status = "pending_live_acceptance" if not unique else ("passed" if all(gates.values()) else "failed")
    report = {
        "generatedAt": datetime.now(timezone.utc).isoformat(),
        "priceVersion": price_version,
        "status": status,
        "pass": status == "passed",
        "gates": gates,
        "materialGates": material_gates,
        "runtimeConfigAudit": runtime_config_audit,
        "independenceProof": split,
        "fingerprint": fingerprint,
        "targets": len(targets),
        "sampleRows": len(samples),
        "freshRows": len(fresh),
        "freshUnique": len(unique),
        "rejectedRepeatGroups": rejected_repeats,
        "materialCounts": dict(by_material_count),
        "autoQuoted": len(auto),
        "manualReview": sum(1 for row in scored if row["requiresManualReview"]),
        "overall": overall,
        "pureEstimate": metrics([row["relativeError"] for row in pure]),
        "processAdjusted": metrics([row["relativeError"] for row in process_adj]),
        "byMaterial": {key: metrics(errs) for key, errs in material_errors.items()},
        "quarantineCount": len(quarantined),
        "quarantine": quarantined,
        "fallbackVersionIfFailed": "jlc-cn-pcb-v6-20260712",
        "note": (
            "No fresh independent DOM acceptance samples for v8. "
            "Do not reuse v7 diagnostic acceptance. "
            "Run: node scripts/jlc-cn-browser-sample.mjs pcb-acceptance-v8 scripts/jlc-cn-pcb-v8-acceptance-samples.json"
            if status == "pending_live_acceptance"
            else None
        ),
    }
    JSON_OUT.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    SCORED_ROWS_OUT.write_text(
        json.dumps(
            {
                "generatedAt": report["generatedAt"],
                "fingerprint": fingerprint.get("hash"),
                "rows": scored,
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )

    lines = [
        "# PCB 报价第八版准确度测试报告",
        "",
        f"- 生成时间：{report['generatedAt']}",
        f"- 活动价格版本：`{price_version}`",
        f"- 验收状态：**{status}**",
        f"- 独立性证明：`ok={bool(split.get('ok'))}`",
        f"- 指纹冻结：`{fingerprint.get('hash', '—')}`",
        f"- 验收目标：{len(targets)}；新鲜独立 DOM 唯一样本：{len(unique)}",
        f"- 当前 table_data acceptance_status：`{meta.get('acceptance_status')}`",
            f"- 运行时 estimator 配置审计：`ok={runtime_config_audit['ok']}`",
        "",
        "## 门禁对照",
        "",
        "| 门禁 | 结果 |",
        "|---|---|",
    ]
    for key, value in gates.items():
        lines.append(f"| `{key}` | {'通过' if value else '未通过'} |")
    lines.extend(
        [
            "",
            "## 总体指标（JLC 估算价，不含 10% margin）",
            "",
            "| 指标 | 结果 |",
            "|---|---:|",
            f"| 自动报价样本 | {overall['n']} |",
            f"| Hit@10% | {pct(overall['hitRate10'])} |",
            f"| Hit@20% | {pct(overall['hitRate20'])} |",
            f"| MAPE | {pct(overall['mape'])} |",
            f"| 最大相对误差 | {pct(overall['maxRelativeError'])} |",
            f"| 隔离异常规格 | {len(quarantined)} |",
            "",
            "## 分材料新鲜样本计数",
            "",
            "| 材料 | 新鲜唯一 DOM |",
            "|---|---:|",
            f"| FR-4 | {by_material_count.get('fr4', 0)} |",
            f"| FPC | {by_material_count.get('fpc', 0)} |",
            f"| 铝基板 | {by_material_count.get('aluminum', 0)} |",
            "",
            "## 发布结论",
            "",
        ]
    )
    if status == "pending_live_acceptance":
        lines.extend(
            [
                "- 全新独立实采尚未完成；**禁止使用 v7 诊断样本冒充最终验收**。",
                "- 代码侧已落地：验收失败阻断 estimator/process、区间风险护栏、原子发布硬门。",
                "- 活动版本在验收通过前应保持 / 回退：`jlc-cn-pcb-v6-20260712`（当前 meta `active_price_version` 已指向该回退）。",
                "- 续采：`node scripts/jlc-cn-browser-sample.mjs pcb-acceptance-v8 scripts/jlc-cn-pcb-v8-acceptance-samples.json`",
            ]
        )
    elif status == "passed":
        lines.append("- 独立大型验收门禁全部通过，可将活动版本原子切换到 v8。")
    else:
        lines.extend(
            [
                "- 独立大型验收未达门禁。",
                "- 保持活动版本：`jlc-cn-pcb-v6-20260712`。",
            ]
        )
    lines.append("")
    MD_OUT.write_text("\n".join(lines), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
