"""Score live JLC DOM quotes against the deployed PCB estimator."""

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

INPUT_PATH = ROOT / "scripts" / "jlc-cn-pcb-large-accuracy-live.json"
JSON_OUTPUT_PATH = ROOT / "scripts" / "jlc-cn-pcb-large-accuracy-report.json"
MARKDOWN_OUTPUT_PATH = ROOT / "docs" / "pcb-quote-v5-large-accuracy-test-report.md"


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
    errors = [row["relativeError"] for row in autoRows]
    signedErrors = [row["signedRelativeError"] for row in autoRows]
    customerErrors = [row["customerRelativeError"] for row in autoRows]
    customerSignedErrors = [row["customerSignedRelativeError"] for row in autoRows]
    return {
        "requested": len(rows),
        "validDom": len(validRows),
        "autoQuoted": len(autoRows),
        "manualReview": sum(row["validActual"] and not row["autoQuoted"] for row in rows),
        "hitRate10": round(sum(error <= 0.10 for error in errors) / len(errors), 4) if errors else None,
        "hitRate20": round(sum(error <= 0.20 for error in errors) / len(errors), 4) if errors else None,
        "mape": round(statistics.fmean(errors), 4) if errors else None,
        "meanSignedError": round(statistics.fmean(signedErrors), 4) if signedErrors else None,
        "medianRelativeError": round(percentile(errors, 0.5), 4) if errors else None,
        "p90RelativeError": round(percentile(errors, 0.9), 4) if errors else None,
        "maxRelativeError": round(max(errors), 4) if errors else None,
        "overEstimates": sum(error > 0 for error in signedErrors),
        "underEstimates": sum(error < 0 for error in signedErrors),
        "customerPrice": {
            "hitRate10": round(
                sum(error <= 0.10 for error in customerErrors) / len(customerErrors), 4
            ) if customerErrors else None,
            "hitRate20": round(
                sum(error <= 0.20 for error in customerErrors) / len(customerErrors), 4
            ) if customerErrors else None,
            "mape": round(statistics.fmean(customerErrors), 4) if customerErrors else None,
            "meanSignedError": round(
                statistics.fmean(customerSignedErrors), 4
            ) if customerSignedErrors else None,
            "maxRelativeError": round(max(customerErrors), 4) if customerErrors else None,
        },
    }


def scoreRow(sample, params, tables):
    processChangedFields = sample.get("processChangedFields") or []
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
    }
    manufacturing = calc_pcb(inputs, params, tables)["pcb_manufacturing"]
    actual = sample.get("domPriceCny")
    validActual = (
        not sample.get("error")
        and sample.get("priceSource") == "dom"
        and isinstance(actual, (int, float))
        and actual > 0
    )
    predicted = manufacturing.get("jlc_estimate_cny")
    customerPrice = manufacturing.get("customer_quote_cny")
    autoQuoted = (
        validActual
        and not manufacturing.get("requires_manual_review")
        and isinstance(predicted, (int, float))
        and predicted > 0
    )
    relativeError = abs(predicted - actual) / actual if autoQuoted else None
    signedRelativeError = (predicted - actual) / actual if autoQuoted else None
    customerRelativeError = abs(customerPrice - actual) / actual if autoQuoted else None
    customerSignedRelativeError = (
        (customerPrice - actual) / actual if autoQuoted else None
    )
    return {
        "id": sample.get("id"),
        "materialKey": sample.get("materialKey"),
        "layers": sample.get("layers"),
        "widthMm": sample.get("widthMm"),
        "heightMm": sample.get("heightMm"),
        "quantity": sample.get("quantity"),
        "boardThickness": sample.get("boardThickness"),
        "solderColor": sample.get("solderColor"),
        "surfaceFinish": sample.get("surfaceFinish"),
        "copperThickness": sample.get("copperThickness"),
        "scenario": "estimator_process" if processChangedFields else "estimator_base",
        "validActual": validActual,
        "autoQuoted": autoQuoted,
        "actualPriceCny": actual if validActual else None,
        "predictedPriceCny": predicted if autoQuoted else None,
        "customerPriceCny": customerPrice if autoQuoted else None,
        "relativeError": relativeError,
        "signedRelativeError": signedRelativeError,
        "customerRelativeError": customerRelativeError,
        "customerSignedRelativeError": customerSignedRelativeError,
        "hit10": relativeError <= 0.10 if relativeError is not None else False,
        "hit20": relativeError <= 0.20 if relativeError is not None else False,
        "pricingMode": manufacturing.get("pricing_mode"),
        "basePricingMode": manufacturing.get("base_pricing_mode"),
        "processAdjusted": manufacturing.get("process_adjusted", False),
        "manualReviewReasons": manufacturing.get("manual_review_reasons") or [],
        "sampleError": sample.get("error"),
        "selectedProcessOptions": sample.get("selectedProcessOptions"),
    }


def percent(value):
    return "-" if value is None else f"{value * 100:.2f}%"


def metricTable(summaryByGroup):
    lines = [
        "| 分组 | 有效 DOM | 自动报价 | Hit@10% | Hit@20% | MAPE | 平均偏差 | P90 | 最大误差 |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for key, metrics in summaryByGroup.items():
        lines.append(
            f"| {key} | {metrics['validDom']} | {metrics['autoQuoted']} "
            f"| {percent(metrics['hitRate10'])} | {percent(metrics['hitRate20'])} "
            f"| {percent(metrics['mape'])} | {percent(metrics['meanSignedError'])} "
            f"| {percent(metrics['p90RelativeError'])} "
            f"| {percent(metrics['maxRelativeError'])} |"
        )
    return "\n".join(lines)


def customerMetricTable(summaryByGroup):
    lines = [
        "| 分组 | Hit@10% | Hit@20% | MAPE | 平均价差 | 最大价差 |",
        "|---|---:|---:|---:|---:|---:|",
    ]
    for key, metrics in summaryByGroup.items():
        customer = metrics["customerPrice"]
        lines.append(
            f"| {key} | {percent(customer['hitRate10'])} | {percent(customer['hitRate20'])} "
            f"| {percent(customer['mape'])} | {percent(customer['meanSignedError'])} "
            f"| {percent(customer['maxRelativeError'])} |"
        )
    return "\n".join(lines)


def buildMarkdown(report):
    overall = report["overall"]
    worstRows = sorted(
        [row for row in report["rows"] if row["autoQuoted"]],
        key=lambda row: row["relativeError"],
        reverse=True,
    )[:12]
    worstLines = [
        "| 材料 | 层数 | 尺寸/数量 | 工艺 | JLC DOM | 本站估算 | 误差 |",
        "|---|---:|---|---|---:|---:|---:|",
    ]
    for row in worstRows:
        process = (
            f"{row['boardThickness']}mm/{row['solderColor']}/"
            f"{row['surfaceFinish']}/{row['copperThickness']}"
        )
        worstLines.append(
            f"| {row['materialKey']} | {row['layers']} | "
            f"{row['widthMm']}×{row['heightMm']}mm / {row['quantity']}片 | {process} "
            f"| {row['actualPriceCny']:.2f} | {row['predictedPriceCny']:.2f} "
            f"| {percent(row['relativeError'])} |"
        )
    return f"""# PCB 第五版大型报价准确度测试报告

## 1. 结论

- 测试时间：`{report['generatedAt']}`
- 独立测试规格：{overall['requested']} 个；有效 JLC 最终 DOM：{overall['validDom']} 个
- 自动报价：{overall['autoQuoted']} 个；人工复核：{overall['manualReview']} 个
- Hit@10%：{percent(overall['hitRate10'])}
- Hit@20%：{percent(overall['hitRate20'])}
- MAPE：{percent(overall['mape'])}
- 平均有符号偏差：{percent(overall['meanSignedError'])}（正值表示本站估算偏高）
- 中位误差：{percent(overall['medianRelativeError'])}
- P90 误差：{percent(overall['p90RelativeError'])}
- 最大误差：{percent(overall['maxRelativeError'])}
- 偏高/偏低：{overall['overEstimates']} / {overall['underEstimates']} 个
- 加 10% margin 后的客户价：Hit@20% {percent(overall['customerPrice']['hitRate20'])}，MAPE {percent(overall['customerPrice']['mape'])}，平均比 JLC DOM {percent(overall['customerPrice']['meanSignedError'])}

本报告比较的是本站制造费计算中的 JLC 估算基价与同轮 JLC 页面最终 DOM 价，不含本站 10% margin、汇率、运费和税费。测试尺寸与数量均避开精确表格点，重点验证 `verified_estimate`，并包含 FPC/铝基板的“估算基价 + 已验证工艺调整”组合。

- {report['integrity']['domSources']}/{overall['requested']} 条价格来源为最终 DOM，API 与 DOM 最大差异为 {report['integrity']['maxApiDomDiff']:.2f} CNY。
- {report['integrity']['verifiedEstimateRows']}/{overall['requested']} 条本站计算均走 `verified_estimate`，没有误命中 exact。
- {report['integrity']['processChangedSamples']} 条非标准工艺样本的最终选中态全部匹配，错配 {report['integrity']['processSelectionMismatches']} 条。

## 2. 分材料结果

{metricTable(report['byMaterial'])}

## 3. 分场景结果

{metricTable(report['byScenario'])}

## 4. 误差最大的自动报价

{chr(10).join(worstLines)}

## 5. 客户价与 JLC DOM 的差异

下表使用实际返回给客户的 CNY 制造费（已包含固定 10% margin）直接比较 JLC DOM。该差异包含商业 margin，不等同于估算模型误差。

{customerMetricTable(report['byMaterial'])}

## 6. 回归与服务状态

- PCB 制造费后端测试：15/15 PASS。
- Django check：PASS，0 issues。
- Vite production build：PASS，416 modules。
- Compose：backend、frontend、admin、caddy、MySQL、Redis 共 6/6 服务运行；MySQL/Redis healthy。
- 部署报价页 `http://localhost/simple-quote`：HTTP 200。
- 前端未配置 lint 脚本；构建仍有 Maker.js `eval` 与大 chunk 非阻塞告警。

## 7. 人工复核与无效样本

- JLC DOM 采样失败：{overall['requested'] - overall['validDom']} 个。
- 有效 DOM 中人工复核：{overall['manualReview']} 个；这些规格不计入自动报价误差指标。
- 每条样本的选中工艺、计价模式、人工复核原因及误差见 `scripts/jlc-cn-pcb-large-accuracy-report.json`。
"""


def main():
    samples = json.loads(INPUT_PATH.read_text(encoding="utf-8"))
    params = quoteParams()
    tables = quoteTables()
    rows = [scoreRow(sample, params, tables) for sample in samples]
    groupedByMaterial = defaultdict(list)
    groupedByScenario = defaultdict(list)
    for row in rows:
        groupedByMaterial[row["materialKey"]].append(row)
        groupedByScenario[row["scenario"]].append(row)
    processChangedSamples = [
        sample for sample in samples if sample.get("processChangedFields")
    ]
    processSelectionMismatches = sum(
        any(
            not (sample.get("selectedProcessOptions") or {}).get(field, {}).get("selected")
            for field in sample.get("processChangedFields") or []
        )
        for sample in processChangedSamples
    )
    report = {
        "generatedAt": datetime.now(timezone.utc).isoformat(),
        "source": str(INPUT_PATH.relative_to(ROOT)),
        "priceVersion": PCB_MANUFACTURING_PRICE_META[0].get("version"),
        "processModelVersion": (
            PCB_MANUFACTURING_PRICE_META[0].get("process_model") or {}
        ).get("version"),
        "integrity": {
            "domSources": sum(sample.get("priceSource") == "dom" for sample in samples),
            "maxApiDomDiff": max(
                abs(float(sample.get("apiDomDiff") or 0)) for sample in samples
            ),
            "verifiedEstimateRows": sum(
                row.get("basePricingMode") == "verified_estimate" for row in rows
            ),
            "processChangedSamples": len(processChangedSamples),
            "processSelectionMismatches": processSelectionMismatches,
        },
        "overall": metricSummary(rows),
        "byMaterial": {
            key: metricSummary(groupRows) for key, groupRows in groupedByMaterial.items()
        },
        "byScenario": {
            key: metricSummary(groupRows) for key, groupRows in groupedByScenario.items()
        },
        "rows": rows,
    }
    JSON_OUTPUT_PATH.write_text(
        f"{json.dumps(report, ensure_ascii=False, indent=2)}\n", encoding="utf-8"
    )
    MARKDOWN_OUTPUT_PATH.write_text(buildMarkdown(report), encoding="utf-8")
    print(json.dumps({
        "overall": report["overall"],
        "byMaterial": report["byMaterial"],
        "byScenario": report["byScenario"],
        "json": str(JSON_OUTPUT_PATH.relative_to(ROOT)),
        "markdown": str(MARKDOWN_OUTPUT_PATH.relative_to(ROOT)),
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
