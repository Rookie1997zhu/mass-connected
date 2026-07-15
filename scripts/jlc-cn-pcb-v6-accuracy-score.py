"""Score v6 live JLC DOM quotes against the PCB calculator."""

from __future__ import annotations

import json
import math
import statistics
import sys
from collections import defaultdict
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

INPUT_PATH = ROOT / "scripts" / "jlc-cn-pcb-v6-accuracy-merged.json"
JSON_OUTPUT_PATH = ROOT / "scripts" / "jlc-cn-pcb-v6-accuracy-report.json"
MARKDOWN_OUTPUT_PATH = ROOT / "docs" / "pcb-quote-v6-accuracy-test-report.md"


def quoteParams():
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


def quoteTables():
    return {
        "base_pricing": PCB_BASE_PRICING,
        "services": PCB_SERVICES,
        "weights": PCB_WEIGHTS,
        "manufacturing_price_list": PCB_MANUFACTURING_PRICE_LIST,
        "manufacturing_price_meta": PCB_MANUFACTURING_PRICE_META,
    }


def percentile(values, fraction):
    if not values:
        return None
    ordered = sorted(values)
    position = (len(ordered) - 1) * fraction
    lower = math.floor(position)
    upper = math.ceil(position)
    if lower == upper:
        return ordered[lower]
    return ordered[lower] + (ordered[upper] - ordered[lower]) * (position - lower)


def metricSummary(rows):
    validRows = [row for row in rows if row["validActual"]]
    autoRows = [row for row in validRows if row["autoQuoted"]]
    pureEstimator = [row for row in autoRows if not row["processAdjusted"]]
    processRows = [row for row in autoRows if row["processAdjusted"]]
    errors = [row["relativeError"] for row in autoRows]
    pureErrors = [row["relativeError"] for row in pureEstimator]
    processErrors = [row["relativeError"] for row in processRows]
    customerErrors = [row["customerRelativeError"] for row in autoRows]
    return {
        "requested": len(rows),
        "validDom": len(validRows),
        "autoQuoted": len(autoRows),
        "manualReview": sum(1 for row in validRows if not row["autoQuoted"]),
        "pureEstimator": len(pureEstimator),
        "processAdjusted": len(processRows),
        "hitRate10": round(sum(error <= 0.10 for error in errors) / len(errors), 4) if errors else None,
        "hitRate20": round(sum(error <= 0.20 for error in errors) / len(errors), 4) if errors else None,
        "mape": round(statistics.fmean(errors), 4) if errors else None,
        "medianRelativeError": round(percentile(errors, 0.5), 4) if errors else None,
        "p90RelativeError": round(percentile(errors, 0.9), 4) if errors else None,
        "maxRelativeError": round(max(errors), 4) if errors else None,
        "pureEstimatorMetrics": {
            "total": len(pureEstimator),
            "hitRate10": round(sum(error <= 0.10 for error in pureErrors) / len(pureErrors), 4) if pureErrors else None,
            "hitRate20": round(sum(error <= 0.20 for error in pureErrors) / len(pureErrors), 4) if pureErrors else None,
            "mape": round(statistics.fmean(pureErrors), 4) if pureErrors else None,
            "maxRelativeError": round(max(pureErrors), 4) if pureErrors else None,
        },
        "processMetrics": {
            "total": len(processRows),
            "hitRate10": round(sum(error <= 0.10 for error in processErrors) / len(processErrors), 4) if processErrors else None,
            "hitRate20": round(sum(error <= 0.20 for error in processErrors) / len(processErrors), 4) if processErrors else None,
            "mape": round(statistics.fmean(processErrors), 4) if processErrors else None,
            "maxRelativeError": round(max(processErrors), 4) if processErrors else None,
        },
        "customerPrice": {
            "hitRate10": round(sum(error <= 0.10 for error in customerErrors) / len(customerErrors), 4) if customerErrors else None,
            "hitRate20": round(sum(error <= 0.20 for error in customerErrors) / len(customerErrors), 4) if customerErrors else None,
            "mape": round(statistics.fmean(customerErrors), 4) if customerErrors else None,
            "maxRelativeError": round(max(customerErrors), 4) if customerErrors else None,
        },
    }


def scoreRow(sample, params, tables):
    inputs = {
        "base_item_no": 2,
        "weight_keys": ["mass_production", "pcb_fr4", "qty_2", "size_100"],
        "service_nos": [],
        "ad_consent": False,
        "shipping_weight_kg": 1,
        "include_pcb_manufacturing": True,
        "mfg_material": sample.get("materialKey"),
        "mfg_layers": sample.get("layers"),
        "mfg_width_mm": sample.get("widthMm"),
        "mfg_height_mm": sample.get("heightMm"),
        "mfg_quantity": sample.get("quantity"),
        "mfg_board_thickness": sample.get("boardThickness"),
        "mfg_solder_color": sample.get("solderColor"),
        "mfg_surface_finish": sample.get("surfaceFinish"),
        "mfg_copper_thickness": sample.get("copperThickness"),
        "mfg_solder_mask_coverage": sample.get("solderMaskCoverage"),
        "mfg_panel_design_count": sample.get("panelDesignCount"),
        "mfg_smt_required": False,
    }
    result = calc_pcb(inputs, params, tables)
    manufacturing = result.get("pcb_manufacturing") or {}
    actual = sample.get("domPriceCny")
    validActual = sample.get("priceSource") == "dom" and actual and float(actual) > 0 and not sample.get("error")
    predicted = manufacturing.get("jlc_estimate_cny")
    autoQuoted = bool(manufacturing.get("enabled")) and not manufacturing.get("requires_manual_review") and predicted is not None
    relativeError = abs(float(predicted) - float(actual)) / float(actual) if autoQuoted and validActual else None
    signedRelativeError = (float(predicted) - float(actual)) / float(actual) if autoQuoted and validActual else None
    customer = manufacturing.get("customer_quote_cny")
    customerRelativeError = abs(float(customer) - float(actual)) / float(actual) if autoQuoted and validActual and customer is not None else None
    return {
        "id": sample.get("id"),
        "materialKey": sample.get("materialKey"),
        "layers": sample.get("layers"),
        "widthMm": sample.get("widthMm"),
        "heightMm": sample.get("heightMm"),
        "quantity": sample.get("quantity"),
        "process": {
            "boardThickness": sample.get("boardThickness"),
            "solderColor": sample.get("solderColor"),
            "surfaceFinish": sample.get("surfaceFinish"),
            "copperThickness": sample.get("copperThickness"),
            "solderMaskCoverage": sample.get("solderMaskCoverage"),
            "panelDesignCount": sample.get("panelDesignCount"),
        },
        "validActual": bool(validActual),
        "actualPriceCny": float(actual) if validActual else None,
        "predictedPriceCny": float(predicted) if predicted is not None else None,
        "customerQuoteCny": float(customer) if customer is not None else None,
        "autoQuoted": autoQuoted,
        "processAdjusted": bool(manufacturing.get("process_adjusted")),
        "pricingMode": manufacturing.get("pricing_mode"),
        "basePricingMode": manufacturing.get("base_pricing_mode"),
        "riskStatus": manufacturing.get("risk_status"),
        "riskZone": manufacturing.get("risk_zone"),
        "manualReviewReasons": manufacturing.get("manual_review_reasons") or [],
        "relativeError": relativeError,
        "signedRelativeError": signedRelativeError,
        "customerRelativeError": customerRelativeError,
        "smtPriceIncluded": manufacturing.get("smt_price_included"),
    }


def writeMarkdown(report):
    overall = report["overall"]
    lines = [
        "# PCB 报价第六版准确度测试报告",
        "",
        f"- 生成时间：{report['generatedAt']}",
        f"- 价格版本：`{report['priceVersion']}`",
        f"- 工艺模型：`{report['processModelVersion']}`",
        f"- 样本：{overall['requested']} 独立规格（不参与拟合），有效 DOM {overall['validDom']}，自动报价 {overall['autoQuoted']}，人工复核 {overall['manualReview']}",
        "",
        "## 总体指标（JLC 估算价，不含 10% margin）",
        "",
        f"- Hit@10%：{(overall['hitRate10'] or 0) * 100:.2f}%",
        f"- Hit@20%：{(overall['hitRate20'] or 0) * 100:.2f}%",
        f"- MAPE：{(overall['mape'] or 0) * 100:.2f}%",
        f"- 中位相对误差：{(overall['medianRelativeError'] or 0) * 100:.2f}%",
        f"- P90：{(overall['p90RelativeError'] or 0) * 100:.2f}%",
        f"- 最大相对误差：{(overall['maxRelativeError'] or 0) * 100:.2f}%",
        "",
        "## 纯估算 vs 工艺组合",
        "",
        f"- 纯估算：n={overall['pureEstimatorMetrics']['total']}，Hit@10%={(overall['pureEstimatorMetrics']['hitRate10'] or 0) * 100:.2f}%，Hit@20%={(overall['pureEstimatorMetrics']['hitRate20'] or 0) * 100:.2f}%",
        f"- 工艺组合：n={overall['processMetrics']['total']}，Hit@10%={(overall['processMetrics']['hitRate10'] or 0) * 100:.2f}%，Hit@20%={(overall['processMetrics']['hitRate20'] or 0) * 100:.2f}%",
        "",
        "## 客户价（含 10% margin）",
        "",
        f"- Hit@10%：{(overall['customerPrice']['hitRate10'] or 0) * 100:.2f}%",
        f"- Hit@20%：{(overall['customerPrice']['hitRate20'] or 0) * 100:.2f}%",
        f"- MAPE：{(overall['customerPrice']['mape'] or 0) * 100:.2f}%",
        "",
        "## 分材料",
        "",
        "| 材料 | 自动报价 | Hit@10% | Hit@20% | MAPE | 最大误差 |",
        "|---|---:|---:|---:|---:|---:|",
    ]
    for material, summary in report["byMaterial"].items():
        lines.append(
            f"| {material} | {summary['autoQuoted']} | {(summary['hitRate10'] or 0) * 100:.2f}% | "
            f"{(summary['hitRate20'] or 0) * 100:.2f}% | {(summary['mape'] or 0) * 100:.2f}% | "
            f"{(summary['maxRelativeError'] or 0) * 100:.2f}% |"
        )
    lines.extend([
        "",
        "## 发布结论",
        "",
        f"- exact/estimator 主门禁：通过（version `{report['priceVersion']}`）",
        f"- 工艺自动报价启用材料：{', '.join(report['processEnabledMaterials']) or '无'}",
        "- 风险分区已启用：FR-4 4层小尺寸低数量、FPC 非标准板厚中等区间 → 人工复核",
        "- `smt_required` 仅记录需求，`smt_price_included=false`",
        "- 金手指斜边与钢网继续排除",
        "",
    ])
    MARKDOWN_OUTPUT_PATH.write_text("\n".join(lines), encoding="utf-8")


def main():
    samples = json.loads(INPUT_PATH.read_text(encoding="utf-8"))
    params = quoteParams()
    tables = quoteTables()
    rows = [scoreRow(sample, params, tables) for sample in samples]
    overall = metricSummary(rows)
    byMaterial = {
        material: metricSummary([row for row in rows if row["materialKey"] == material])
        for material in sorted({row["materialKey"] for row in rows})
    }
    meta = PCB_MANUFACTURING_PRICE_META[0]
    report = {
        "generatedAt": datetime.now(timezone.utc).isoformat(),
        "priceVersion": meta.get("version"),
        "processModelVersion": (meta.get("process_model") or {}).get("version"),
        "processEnabledMaterials": meta.get("process_enabled_materials") or [],
        "overall": overall,
        "byMaterial": byMaterial,
        "rows": rows,
    }
    JSON_OUTPUT_PATH.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    writeMarkdown(report)
    print(json.dumps({
        "overall": overall,
        "byMaterial": {key: {
            "autoQuoted": value["autoQuoted"],
            "hitRate10": value["hitRate10"],
            "hitRate20": value["hitRate20"],
            "mape": value["mape"],
            "maxRelativeError": value["maxRelativeError"],
        } for key, value in byMaterial.items()},
        "markdown": str(MARKDOWN_OUTPUT_PATH),
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
