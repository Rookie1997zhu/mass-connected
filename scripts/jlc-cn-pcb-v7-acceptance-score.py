"""Score v7 independent acceptance DOM samples against the PCB calculator.

Refuses historical assemble / bootstrapped samples. Without fresh DOM, writes pending report.
"""

from __future__ import annotations

import json
import statistics
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
import sys

sys.path.insert(0, str(ROOT / "backend"))

from apps.simplequote.calculator import DEFAULT_PARAMS, calc_pcb  # noqa: E402
from apps.simplequote.table_data import (  # noqa: E402
    PCB_BASE_PRICING,
    PCB_MANUFACTURING_PRICE_LIST,
    PCB_MANUFACTURING_PRICE_META,
    PCB_SERVICES,
    PCB_WEIGHTS,
)

TARGETS_PATH = ROOT / "scripts" / "jlc-cn-pcb-v7-acceptance-targets.json"
SAMPLES_PATH = ROOT / "scripts" / "jlc-cn-pcb-v7-acceptance-samples.json"
SPLIT_PATH = ROOT / "scripts" / "jlc-cn-pcb-v7-assert-split-report.json"
JSON_OUT = ROOT / "scripts" / "jlc-cn-pcb-v7-acceptance-report.json"
MD_OUT = ROOT / "docs" / "pcb-quote-v7-accuracy-test-report.md"


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
    return {
        "base_pricing": PCB_BASE_PRICING,
        "services": PCB_SERVICES,
        "weights": PCB_WEIGHTS,
        "manufacturing_price_list": PCB_MANUFACTURING_PRICE_LIST,
        "manufacturing_price_meta": PCB_MANUFACTURING_PRICE_META,
    }


def is_fresh_dom(row: dict) -> bool:
    if not row or row.get("error") or row.get("priceSource") != "dom":
        return False
    if not (float(row.get("domPriceCny") or 0) > 0):
        return False
    notes = str(row.get("notes") or "")
    fp = row.get("pageFingerprint") or {}
    if "bootstrapped" in notes or fp.get("source") == "bootstrapped_from_v6_dom":
        return False
    return True


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
    meta = (PCB_MANUFACTURING_PRICE_META or [{}])[0]
    price_version = meta.get("version", "unknown")
    process_zones = meta.get("process_enabled_zones") or []
    process_materials = meta.get("process_enabled_materials") or []

    fresh = [row for row in samples if is_fresh_dom(row)]
    unique = list({geometry_key(row): row for row in fresh}.values())
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
        scored.append(
            {
                "id": row.get("id"),
                "materialKey": row.get("materialKey") or row.get("material_key"),
                "requiresManualReview": bool(mfg.get("requires_manual_review")),
                "pricingMode": mfg.get("pricing_mode"),
                "actualCny": actual,
                "predictedCny": predicted,
                "relativeError": rel,
                "isStandardProcess": mfg.get("is_standard_process"),
                "processAdjusted": mfg.get("process_adjusted"),
                "pageFingerprint": row.get("pageFingerprint"),
                "sampleTime": row.get("sampleTime"),
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
    gates = {
        "independenceOk": bool(split.get("ok")),
        "freshPerMaterialAtLeast40": min_per_material >= 40,
        "overallHit10AtLeast90": (overall.get("hitRate10") or 0) >= 0.9,
        "overallHit20AtLeast95": (overall.get("hitRate20") or 0) >= 0.95,
        "overallMapeAtMost8": (overall.get("mape") or 1) <= 0.08,
        "overallMaxErrAtMost20": (overall.get("maxRelativeError") or 1) <= 0.2,
    }
    status = "pending_live_acceptance" if not unique else ("passed" if all(gates.values()) else "failed")
    report = {
        "generatedAt": datetime.now(timezone.utc).isoformat(),
        "priceVersion": price_version,
        "status": status,
        "pass": status == "passed",
        "gates": gates,
        "independenceProof": split,
        "targets": len(targets),
        "sampleRows": len(samples),
        "freshUnique": len(unique),
        "materialCounts": dict(by_material_count),
        "autoQuoted": len(auto),
        "manualReview": sum(1 for row in scored if row["requiresManualReview"]),
        "overall": overall,
        "pureEstimate": metrics([row["relativeError"] for row in pure]),
        "processAdjusted": metrics([row["relativeError"] for row in process_adj]),
        "byMaterial": {key: metrics(errs) for key, errs in material_errors.items()},
        "processEnabledMaterials": process_materials,
        "processEnabledZones": [zone.get("id") for zone in process_zones],
        "fallbackVersionIfFailed": "jlc-cn-pcb-v6-20260712",
        "note": (
            "No fresh independent DOM acceptance samples. "
            "Do not assemble fit/holdout history. "
            "Run: node scripts/jlc-cn-browser-sample.mjs pcb-acceptance-v7 scripts/jlc-cn-pcb-v7-acceptance-samples.json"
            if status == "pending_live_acceptance"
            else None
        ),
    }
    JSON_OUT.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    lines = [
        "# PCB 报价第七版准确度测试报告",
        "",
        f"- 生成时间：{report['generatedAt']}",
        f"- 价格版本：`{price_version}`",
        f"- 验收状态：**{status}**",
        f"- 独立性证明：`ok={bool(split.get('ok'))}`（拟合 / holdout / 最终验收规格键交集为 0）",
        f"- 验收目标：{len(targets)}；新鲜独立 DOM 唯一样本：{len(unique)}",
        f"- 工艺启用材料：{', '.join(process_materials) or '—'}",
        f"- 工艺启用分区：{', '.join(report['processEnabledZones']) or '—'}",
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
                "- 最终大型独立实采尚未完成；**不以历史拟合样本拼装验收**。",
                "- 代码与 `table_data` 已接入 v7 分段工艺系数、风险自动标定与 FR-4/FPC 分区放行。",
                "- 主 exact/estimator 门禁此前已通过；工艺模型为 `partial_pass`（aluminum 全开 + FR-4/FPC 局部 zone）。",
                "- 若最终独立验收失败，回滚版本：`jlc-cn-pcb-v6-20260712`。",
                "- 续采命令：`node scripts/jlc-cn-browser-sample.mjs pcb-acceptance-v7 scripts/jlc-cn-pcb-v7-acceptance-samples.json`",
            ]
        )
    elif status == "passed":
        lines.append("- 独立大型验收门禁全部通过，可维持 `jlc-cn-pcb-v7-*` 发布。")
    else:
        lines.extend(
            [
                "- 独立大型验收未达门禁。",
                "- 建议回滚/继续使用：`jlc-cn-pcb-v6-20260712`，直至补采达标。",
            ]
        )
    lines.append("")
    MD_OUT.write_text("\n".join(lines), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
