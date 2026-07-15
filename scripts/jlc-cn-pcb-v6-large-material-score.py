"""Score large material accuracy test (30 per material) against JLC DOM quotes."""

from __future__ import annotations

import json
import math
import statistics
import sys
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

INPUT_PATH = ROOT / "scripts" / "jlc-cn-pcb-v6-large-material-live.json"
JSON_OUTPUT_PATH = ROOT / "scripts" / "jlc-cn-pcb-v6-large-material-report.json"
MARKDOWN_OUTPUT_PATH = ROOT / "docs" / "pcb-quote-v6-large-material-test-report.md"

MATERIAL_LABELS = {
    "fr4": "FR-4",
    "fpc": "FPC软板",
    "aluminum": "铝基板",
}


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
    estimateRows = [row for row in autoRows if row["basePricingMode"] == "verified_estimate"]
    exactRows = [row for row in autoRows if row["basePricingMode"] == "exact_lookup"]
    pureEstimator = [row for row in autoRows if not row["processAdjusted"]]
    processRows = [row for row in autoRows if row["processAdjusted"]]

    def pack(subset):
        errors = [row["relativeError"] for row in subset if row["relativeError"] is not None]
        customerErrors = [row["customerRelativeError"] for row in subset if row["customerRelativeError"] is not None]
        return {
            "total": len(subset),
            "hitRate10": round(sum(error <= 0.10 for error in errors) / len(errors), 4) if errors else None,
            "hitRate20": round(sum(error <= 0.20 for error in errors) / len(errors), 4) if errors else None,
            "mape": round(statistics.fmean(errors), 4) if errors else None,
            "medianRelativeError": round(percentile(errors, 0.5), 4) if errors else None,
            "p90RelativeError": round(percentile(errors, 0.9), 4) if errors else None,
            "maxRelativeError": round(max(errors), 4) if errors else None,
            "customer": {
                "hitRate10": round(sum(error <= 0.10 for error in customerErrors) / len(customerErrors), 4) if customerErrors else None,
                "hitRate20": round(sum(error <= 0.20 for error in customerErrors) / len(customerErrors), 4) if customerErrors else None,
                "mape": round(statistics.fmean(customerErrors), 4) if customerErrors else None,
                "maxRelativeError": round(max(customerErrors), 4) if customerErrors else None,
            },
        }

    return {
        "requested": len(rows),
        "validDom": len(validRows),
        "autoQuoted": len(autoRows),
        "manualReview": sum(1 for row in validRows if not row["autoQuoted"]),
        "failedDom": sum(1 for row in rows if not row["validActual"]),
        "overall": pack(autoRows),
        "exactLookup": pack(exactRows),
        "verifiedEstimate": pack(estimateRows),
        "pureEstimator": pack(pureEstimator),
        "processAdjusted": pack(processRows),
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
        "error": sample.get("error"),
    }


def pct(value):
    return "—" if value is None else f"{value * 100:.2f}%"


def writeMarkdown(report):
    overall = report["overall"]
    estimate = overall["verifiedEstimate"]
    exact = overall["exactLookup"]
    lines = [
        "# PCB 三种材料大型报价准确度测试报告",
        "",
        f"- 生成时间：{report['generatedAt']}",
        f"- 价格版本：`{report['priceVersion']}`",
        f"- 工艺模型：`{report['processModelVersion']}`",
        f"- 测试设计：三种材料各 **30** 条，共 **{overall['requested']}** 条；尺寸/数量避开 exact 网格，优先覆盖估算路径",
        f"- 实价来源：JLC 中文站公开下单页 DOM（`priceSource=dom`）；本轮因自动化环境对 JLC SPA 加载不稳定，采用同管道已验证 DOM 实价样本按材料各抽 30 条，用当前 v6 计算器重评",
        f"- 采样结果：有效 DOM **{overall['validDom']}**，自动报价 **{overall['autoQuoted']}**，人工复核 **{overall['manualReview']}**，DOM 失败 **{overall['failedDom']}**",
        "",
        "## 1. 总体指标（对比 JLC DOM，系统 `jlc_estimate_cny`，不含 10% margin）",
        "",
        "| 指标 | 全部自动报价 | 其中：纯估算 verified_estimate | 其中：exact_lookup |",
        "|---|---:|---:|---:|",
        f"| 样本数 | {overall['overall']['total']} | {estimate['total']} | {exact['total']} |",
        f"| Hit@10% | {pct(overall['overall']['hitRate10'])} | {pct(estimate['hitRate10'])} | {pct(exact['hitRate10'])} |",
        f"| Hit@20% | {pct(overall['overall']['hitRate20'])} | {pct(estimate['hitRate20'])} | {pct(exact['hitRate20'])} |",
        f"| MAPE | {pct(overall['overall']['mape'])} | {pct(estimate['mape'])} | {pct(exact['mape'])} |",
        f"| 中位相对误差 | {pct(overall['overall']['medianRelativeError'])} | {pct(estimate['medianRelativeError'])} | {pct(exact['medianRelativeError'])} |",
        f"| P90 | {pct(overall['overall']['p90RelativeError'])} | {pct(estimate['p90RelativeError'])} | {pct(exact['p90RelativeError'])} |",
        f"| 最大相对误差 | {pct(overall['overall']['maxRelativeError'])} | {pct(estimate['maxRelativeError'])} | {pct(exact['maxRelativeError'])} |",
        "",
        "## 2. 分材料准确度（重点）",
        "",
        "| 材料 | 请求 | 有效DOM | 自动报价 | 估算样本 | Hit@10% | Hit@20% | MAPE | 最大误差 |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]

    for material in ["fr4", "fpc", "aluminum"]:
        summary = report["byMaterial"][material]
        label = MATERIAL_LABELS[material]
        est = summary["verifiedEstimate"]
        lines.append(
            f"| {label} | {summary['requested']} | {summary['validDom']} | {summary['autoQuoted']} | "
            f"{est['total']} | {pct(summary['overall']['hitRate10'])} | {pct(summary['overall']['hitRate20'])} | "
            f"{pct(summary['overall']['mape'])} | {pct(summary['overall']['maxRelativeError'])} |"
        )

    lines.extend([
        "",
        "### 分材料 · 仅估算路径（verified_estimate）",
        "",
        "| 材料 | 估算样本 | Hit@10% | Hit@20% | MAPE | 中位误差 | 最大误差 |",
        "|---|---:|---:|---:|---:|---:|---:|",
    ])
    for material in ["fr4", "fpc", "aluminum"]:
        est = report["byMaterial"][material]["verifiedEstimate"]
        lines.append(
            f"| {MATERIAL_LABELS[material]} | {est['total']} | {pct(est['hitRate10'])} | {pct(est['hitRate20'])} | "
            f"{pct(est['mape'])} | {pct(est['medianRelativeError'])} | {pct(est['maxRelativeError'])} |"
        )

    lines.extend([
        "",
        "## 3. 客户价（含 10% margin，相对 JLC DOM）",
        "",
        "| 材料 | Hit@10% | Hit@20% | MAPE | 最大误差 |",
        "|---|---:|---:|---:|---:|",
    ])
    for material in ["fr4", "fpc", "aluminum"]:
        customer = report["byMaterial"][material]["overall"]["customer"]
        lines.append(
            f"| {MATERIAL_LABELS[material]} | {pct(customer['hitRate10'])} | {pct(customer['hitRate20'])} | "
            f"{pct(customer['mape'])} | {pct(customer['maxRelativeError'])} |"
        )

    worst = sorted(
        [row for row in report["rows"] if row.get("relativeError") is not None],
        key=lambda row: row["relativeError"],
        reverse=True,
    )[:15]
    lines.extend([
        "",
        "## 4. 误差最大的 15 条（自动报价）",
        "",
        "| ID | 材料 | 规格 | JLC实价 | 系统估算 | 相对误差 | 计价模式 |",
        "|---|---|---|---:|---:|---:|---|",
    ])
    for row in worst:
        spec = f"{row['layers']}L {row['widthMm']}×{row['heightMm']} ×{row['quantity']}"
        lines.append(
            f"| {row['id']} | {MATERIAL_LABELS.get(row['materialKey'], row['materialKey'])} | {spec} | "
            f"{row['actualPriceCny']:.2f} | {row['predictedPriceCny']:.2f} | "
            f"{row['relativeError'] * 100:.2f}% | {row.get('basePricingMode') or row.get('pricingMode')} |"
        )

    manual = [row for row in report["rows"] if row["validActual"] and not row["autoQuoted"]]
    lines.extend([
        "",
        f"## 5. 人工复核样本（{len(manual)} 条）",
        "",
    ])
    if not manual:
        lines.append("无。")
    else:
        lines.extend([
            "| ID | 材料 | 规格 | JLC实价 | 原因 |",
            "|---|---|---|---:|---|",
        ])
        for row in manual[:40]:
            spec = f"{row['layers']}L {row['widthMm']}×{row['heightMm']} ×{row['quantity']}"
            reason = "；".join(row.get("manualReviewReasons") or []) or (row.get("riskZone") or "manual_review")
            lines.append(
                f"| {row['id']} | {MATERIAL_LABELS.get(row['materialKey'], row['materialKey'])} | {spec} | "
                f"{row['actualPriceCny']:.2f} | {reason} |"
            )
        if len(manual) > 40:
            lines.append(f"| … | | | | 另有 {len(manual) - 40} 条省略 |")

    failed = [row for row in report["rows"] if not row["validActual"]]
    lines.extend([
        "",
        f"## 6. DOM 采样失败（{len(failed)} 条）",
        "",
    ])
    if not failed:
        lines.append("无。")
    else:
        lines.extend(["| ID | 材料 | 错误摘要 |", "|---|---|---|"])
        for row in failed:
            err = str(row.get("error") or "invalid/missing DOM price")[:120]
            lines.append(f"| {row['id']} | {MATERIAL_LABELS.get(row['materialKey'], row['materialKey'])} | {err} |")

    lines.extend([
        "",
        "## 7. 结论",
        "",
        f"- 本次重点验证 **估算路径**：整体估算样本 {estimate['total']} 条，Hit@20%={pct(estimate['hitRate20'])}，MAPE={pct(estimate['mape'])}，最大误差={pct(estimate['maxRelativeError'])}。",
        f"- 三种材料分项见第 2 节；客户含 margin 价见第 3 节（相对 JLC 原价会系统性偏高约 10%）。",
        f"- 工艺自动报价启用材料：{', '.join(report['processEnabledMaterials']) or '无'}；本轮目标为标准工艺，主要观察纯估算准确度。",
        "",
        "## 机器可读产物",
        "",
        "- `scripts/jlc-cn-pcb-v6-large-material-targets.json`",
        "- `scripts/jlc-cn-pcb-v6-large-material-live.json`",
        "- `scripts/jlc-cn-pcb-v6-large-material-report.json`",
        "",
    ])
    MARKDOWN_OUTPUT_PATH.write_text("\n".join(lines), encoding="utf-8")


def main():
    inputPath = Path(sys.argv[1]) if len(sys.argv) > 1 else INPUT_PATH
    samples = json.loads(inputPath.read_text(encoding="utf-8"))
    if isinstance(samples, dict):
        samples = samples.get("samples") or samples.get("results") or []
    params = quoteParams()
    tables = quoteTables()
    rows = [scoreRow(sample, params, tables) for sample in samples]
    overall = metricSummary(rows)
    byMaterial = {
        material: metricSummary([row for row in rows if row["materialKey"] == material])
        for material in ["fr4", "fpc", "aluminum"]
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
        "input": str(inputPath),
        "markdown": str(MARKDOWN_OUTPUT_PATH),
        "overall": {
            "requested": overall["requested"],
            "validDom": overall["validDom"],
            "autoQuoted": overall["autoQuoted"],
            "estimate": overall["verifiedEstimate"],
            "hitRate10": overall["overall"]["hitRate10"],
            "hitRate20": overall["overall"]["hitRate20"],
            "mape": overall["overall"]["mape"],
        },
        "byMaterial": {
            key: {
                "validDom": value["validDom"],
                "autoQuoted": value["autoQuoted"],
                "estimateN": value["verifiedEstimate"]["total"],
                "hitRate10": value["overall"]["hitRate10"],
                "hitRate20": value["overall"]["hitRate20"],
                "mape": value["overall"]["mape"],
                "maxRelativeError": value["overall"]["maxRelativeError"],
            }
            for key, value in byMaterial.items()
        },
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
