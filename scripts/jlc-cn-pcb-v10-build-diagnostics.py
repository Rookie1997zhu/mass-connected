"""Build v10 diagnostic-only artifacts from the consumed v9 acceptance run."""

from __future__ import annotations

import json
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCORED = ROOT / "scripts" / "jlc-cn-pcb-v9-acceptance-scored.json"
REPORT = ROOT / "scripts" / "jlc-cn-pcb-v9-acceptance-report.json"
OUT = ROOT / "scripts" / "jlc-cn-pcb-v10-diagnostic-v9-acceptance.json"
SUMMARY_OUT = ROOT / "scripts" / "jlc-cn-pcb-v10-diagnostic-report.json"
MATERIALS = ("fr4", "fpc", "aluminum")


def segment_key(row: dict) -> str:
    area = float(row.get("widthMm") or 0) * float(row.get("heightMm") or 0)
    quantity = int(row.get("quantity") or 0)
    area_segment = "small" if area <= 6000 else ("medium" if area <= 16000 else "large")
    quantity_segment = "low" if quantity <= 20 else ("medium" if quantity <= 75 else "high")
    return f"L{row.get('layers')}|{area_segment}|{quantity_segment}"


scored_payload = json.loads(SCORED.read_text(encoding="utf-8"))
acceptance_report = json.loads(REPORT.read_text(encoding="utf-8"))
rows = scored_payload.get("rows") or []
diagnostic_rows = [
    {
        **row,
        "diagnosticOnly": True,
        "sampleRole": "diagnostic_only",
        "diagnosticReason": "v9_final_acceptance_do_not_train",
    }
    for row in rows
]

summary = {}
for material in MATERIALS:
    material_rows = [row for row in rows if row.get("materialKey") == material]
    auto = [row for row in material_rows if row.get("relativeError") is not None]
    manual_reasons = Counter(
        reason
        for row in material_rows
        if row.get("requiresManualReview")
        for reason in row.get("manualReviewReasons") or ["unknown"]
    )
    segment_groups = defaultdict(list)
    for row in material_rows:
        segment_groups[segment_key(row)].append(row)
    summary[material] = {
        "stable": len(material_rows),
        "autoQuoted": len(auto),
        "coverage": round(len(auto) / len(material_rows), 4) if material_rows else 0,
        "hitRate20": acceptance_report.get("byMaterial", {}).get(material, {}).get("hitRate20"),
        "mape": acceptance_report.get("byMaterial", {}).get(material, {}).get("mape"),
        "maxRelativeError": acceptance_report.get("byMaterial", {}).get(material, {}).get(
            "maxRelativeError"
        ),
        "manualReviewReasonCounts": dict(manual_reasons),
        "highErrorIds": [
            row.get("baseSampleId") or row.get("id")
            for row in auto
            if float(row.get("relativeError") or 0) > 0.20
        ],
        "segments": {
            key: {
                "total": len(group),
                "autoQuoted": sum(row.get("relativeError") is not None for row in group),
                "maxRelativeError": max(
                    (float(row["relativeError"]) for row in group if row.get("relativeError") is not None),
                    default=None,
                ),
            }
            for key, group in sorted(segment_groups.items())
        },
    }

OUT.write_text(json.dumps(diagnostic_rows, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
SUMMARY_OUT.write_text(
    json.dumps(
        {
            "sourceFingerprint": acceptance_report.get("fingerprint", {}).get("hash"),
            "diagnosticOnly": True,
            "materials": summary,
        },
        ensure_ascii=False,
        indent=2,
    )
    + "\n",
    encoding="utf-8",
)
print(json.dumps(summary, ensure_ascii=False, indent=2))
