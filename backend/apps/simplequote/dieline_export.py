"""Dieline segment export: DXF (R12 ASCII), PDF (reportlab), and fixed-asset calibration."""

from __future__ import annotations

import io
from typing import Iterable, List, Sequence, Tuple

from reportlab.lib import colors
from reportlab.lib.units import mm
from reportlab.pdfgen import canvas

Segment = dict  # {"x1","y1","x2","y2","kind"}

DRAW_ORDER: Tuple[str, ...] = ("bleed", "crease", "cut")


def effective_bbox(
    segments: Sequence[Segment],
    exclude_kinds: Sequence[str] = ("bleed",),
) -> Tuple[float, float, float, float]:
    """Return (min_x, min_y, max_x, max_y) over segments whose kind is not excluded.

    Raises:
        ValueError: if no segments remain after filtering.
    """
    exclude = set(exclude_kinds)
    xs: List[float] = []
    ys: List[float] = []
    for seg in segments:
        if seg.get("kind") in exclude:
            continue
        xs.extend([float(seg["x1"]), float(seg["x2"])])
        ys.extend([float(seg["y1"]), float(seg["y2"])])
    if not xs:
        raise ValueError("No segments available for effective bbox")
    return min(xs), min(ys), max(xs), max(ys)


def calibrate_fixed_segments(
    entities: Sequence[dict],
    calibrated_width_mm: float,
    calibrated_height_mm: float,
) -> List[Segment]:
    """Scale parsed entities to calibrated physical blank size.

    Entities with ``role == "ignore"`` are excluded from both the effective bbox
    and the output. Remaining roles map to segment ``kind`` (cut/crease/bleed).
    Coordinates are uniformly scaled so the effective bbox matches
    ``calibrated_width_mm`` × ``calibrated_height_mm``.
    """
    usable = [e for e in entities if e.get("role") != "ignore"]
    if not usable:
        raise ValueError("No usable entities for calibration")

    xs: List[float] = []
    ys: List[float] = []
    for e in usable:
        xs.extend([float(e["x1"]), float(e["x2"])])
        ys.extend([float(e["y1"]), float(e["y2"])])

    min_x, min_y = min(xs), min(ys)
    max_x, max_y = max(xs), max(ys)
    span_x = max_x - min_x
    span_y = max_y - min_y
    if span_x <= 0 or span_y <= 0:
        raise ValueError("Effective entity bbox has zero width or height")

    scale_x = float(calibrated_width_mm) / span_x
    scale_y = float(calibrated_height_mm) / span_y

    result: List[Segment] = []
    for e in usable:
        role = e.get("role") or "cut"
        kind = role if role in ("cut", "crease", "bleed") else "cut"
        result.append(
            {
                "x1": (float(e["x1"]) - min_x) * scale_x,
                "y1": (float(e["y1"]) - min_y) * scale_y,
                "x2": (float(e["x2"]) - min_x) * scale_x,
                "y2": (float(e["y2"]) - min_y) * scale_y,
                "kind": kind,
            }
        )
    return result


def entities_to_raw_segments(entities: Sequence[dict]) -> List[Segment]:
    """Map parsed dieline entities to segments, skipping role=ignore."""
    result: List[Segment] = []
    for e in entities:
        role = e.get("role") or "cut"
        if role == "ignore":
            continue
        kind = role if role in ("cut", "crease", "bleed") else "cut"
        result.append(
            {
                "x1": float(e["x1"]),
                "y1": float(e["y1"]),
                "x2": float(e["x2"]),
                "y2": float(e["y2"]),
                "kind": kind,
            }
        )
    return result


def normalize_fixed_segments(entities: Sequence[dict]) -> List[Segment]:
    """Skip ignore roles and translate usable entities so bbox starts at origin.

    Matches frontend preview behaviour when calibrated size is absent (scale=1).
    """
    usable = [e for e in entities if e.get("role") != "ignore"]
    if not usable:
        raise ValueError("No usable entities for normalization")

    xs: List[float] = []
    ys: List[float] = []
    for e in usable:
        xs.extend([float(e["x1"]), float(e["x2"])])
        ys.extend([float(e["y1"]), float(e["y2"])])

    min_x, min_y = min(xs), min(ys)
    max_x, max_y = max(xs), max(ys)
    if max_x - min_x <= 0 or max_y - min_y <= 0:
        raise ValueError("Effective entity bbox has zero width or height")

    result: List[Segment] = []
    for e in usable:
        role = e.get("role") or "cut"
        kind = role if role in ("cut", "crease", "bleed") else "cut"
        result.append(
            {
                "x1": float(e["x1"]) - min_x,
                "y1": float(e["y1"]) - min_y,
                "x2": float(e["x2"]) - min_x,
                "y2": float(e["y2"]) - min_y,
                "kind": kind,
            }
        )
    return result


def iter_drawable_segments(segments: Sequence[Segment]) -> Iterable[Segment]:
    """Yield segments in preview draw order: bleed → crease → cut."""
    by_kind = {kind: [] for kind in DRAW_ORDER}
    for seg in segments:
        kind = seg.get("kind") or "cut"
        if kind not in by_kind:
            kind = "cut"
        by_kind[kind].append(seg)
    for kind in DRAW_ORDER:
        yield from by_kind[kind]


def drawable_segment_kinds(segments: Sequence[Segment]) -> List[str]:
    """Return unique kinds that will be drawn, in draw order (for tests)."""
    seen = {seg.get("kind") or "cut" for seg in segments}
    return [kind for kind in DRAW_ORDER if kind in seen]


def segments_to_dxf(segments: Sequence[Segment]) -> str:
    """Build a minimal AutoCAD R12 ASCII DXF with LINE entities on CUT / CREASE / BLEED."""
    lines: List[str] = []

    def pair(code: int, value) -> None:
        lines.append(f"{code}\n{value}")

    pair(0, "SECTION")
    pair(2, "HEADER")
    pair(9, "$ACADVER")
    pair(1, "AC1009")
    pair(0, "ENDSEC")

    pair(0, "SECTION")
    pair(2, "TABLES")
    pair(0, "TABLE")
    pair(2, "LAYER")
    pair(70, 3)
    for name, color in (("CUT", 5), ("CREASE", 1), ("BLEED", 3)):
        pair(0, "LAYER")
        pair(2, name)
        pair(70, 0)
        pair(62, color)
        pair(6, "CONTINUOUS")
    pair(0, "ENDTAB")
    pair(0, "ENDSEC")

    pair(0, "SECTION")
    pair(2, "ENTITIES")
    for seg in segments:
        kind = seg.get("kind") or "cut"
        if kind == "crease":
            layer = "CREASE"
        elif kind == "bleed":
            layer = "BLEED"
        else:
            layer = "CUT"
        pair(0, "LINE")
        pair(8, layer)
        pair(10, f"{float(seg['x1']):.6f}")
        pair(20, f"{float(seg['y1']):.6f}")
        pair(30, "0.0")
        pair(11, f"{float(seg['x2']):.6f}")
        pair(21, f"{float(seg['y2']):.6f}")
        pair(31, "0.0")
    pair(0, "ENDSEC")
    pair(0, "EOF")
    return "\n".join(lines) + "\n"


def segments_to_pdf_bytes(segments: Sequence[Segment], title: str = "") -> bytes:
    """Draw segments to a PDF with white page, centered dieline, including bleed.

    Title is ignored for layout (no title band) so content stays centered on the
    white artboard; kept as a no-op parameter for call-site compatibility.
    """
    _ = title  # layout never reserves a title band
    min_x, min_y, max_x, max_y = effective_bbox(segments, exclude_kinds=())

    content_w_mm = max(max_x - min_x, 1.0)
    content_h_mm = max(max_y - min_y, 1.0)

    margin = 15 * mm
    # 1 drawing unit = 1 mm of geometry, converted via reportlab mm
    natural_w = content_w_mm * mm + 2 * margin
    natural_h = content_h_mm * mm + 2 * margin
    # Cap huge blanks to ~A3; scale drawing to fit
    max_page_w, max_page_h = 420 * mm, 594 * mm
    fit = min(1.0, max_page_w / natural_w, max_page_h / natural_h)
    page_w = natural_w * fit
    page_h = natural_h * fit

    buffer = io.BytesIO()
    c = canvas.Canvas(buffer, pagesize=(page_w, page_h))

    # Full-page white background (Illustrator / PDF viewers)
    c.setFillColor(colors.white)
    c.rect(0, 0, page_w, page_h, fill=1, stroke=0)

    usable_w = page_w - 2 * margin * fit
    usable_h = page_h - 2 * margin * fit
    s = min(usable_w / content_w_mm, usable_h / content_h_mm)
    drawn_w = content_w_mm * s
    drawn_h = content_h_mm * s
    offset_x = (page_w - drawn_w) / 2.0
    offset_y = (page_h - drawn_h) / 2.0

    def to_pdf(x: float, y: float) -> Tuple[float, float]:
        px = offset_x + (x - min_x) * s
        # Flip Y so dieline top (small y) is near top of page
        py = offset_y + (max_y - y) * s
        return px, py

    for seg in iter_drawable_segments(segments):
        kind = seg.get("kind") or "cut"
        x1, y1 = to_pdf(float(seg["x1"]), float(seg["y1"]))
        x2, y2 = to_pdf(float(seg["x2"]), float(seg["y2"]))
        if kind == "bleed":
            c.setStrokeColor(colors.Color(0.13, 0.77, 0.37))  # ~#22c55e
            c.setDash()
            c.setLineWidth(0.5)
        elif kind == "crease":
            c.setStrokeColor(colors.Color(0.85, 0.15, 0.15))
            c.setDash(3, 2)
            c.setLineWidth(0.6)
        else:
            c.setStrokeColor(colors.Color(0.1, 0.25, 0.85))
            c.setDash()
            c.setLineWidth(0.8)
        c.line(x1, y1, x2, y2)

    c.showPage()
    c.save()
    return buffer.getvalue()


def segments_to_ai_bytes(segments: Sequence[Segment], title: str = "") -> bytes:
    """Export PDF-compatible ``.ai`` (same layout as PDF: white page, centered, bleed).

    True proprietary binary AI is not generated; Illustrator opens this PDF
    payload when saved as ``.ai``.
    """
    return segments_to_pdf_bytes(segments, title="")
