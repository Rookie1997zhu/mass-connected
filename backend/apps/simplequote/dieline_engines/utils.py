"""Shared helpers for formula dieline segment builders.

Ported from frontend/src/lib/packaging/dielineUtils.ts — numeric logic must stay identical.
"""

from __future__ import annotations

import math
from typing import List, MutableSequence, Sequence, Tuple

Segment = dict  # {"x1", "y1", "x2", "y2", "kind"} with kind in cut/crease/bleed
Gap = Tuple[float, float]


def add_segment(
    segments: MutableSequence[Segment],
    x1: float,
    y1: float,
    x2: float,
    y2: float,
    kind: str,
) -> None:
    segments.append({"x1": x1, "y1": y1, "x2": x2, "y2": y2, "kind": kind})


def add_bleed_rect(
    segments: MutableSequence[Segment],
    w: float,
    h: float,
    bleed_mm: float = 3,
) -> None:
    add_segment(segments, -bleed_mm, -bleed_mm, w + bleed_mm, -bleed_mm, "bleed")
    add_segment(segments, w + bleed_mm, -bleed_mm, w + bleed_mm, h + bleed_mm, "bleed")
    add_segment(segments, w + bleed_mm, h + bleed_mm, -bleed_mm, h + bleed_mm, "bleed")
    add_segment(segments, -bleed_mm, h + bleed_mm, -bleed_mm, -bleed_mm, "bleed")


def slot_width_from_thickness(thickness_mm: float) -> float:
    return max(0.1, thickness_mm)


def slot_corner_radius(thickness_mm: float, slot_w: float) -> float:
    return min(slot_w / 2, thickness_mm * 0.6, 2)


def add_arc_approx(
    segments: MutableSequence[Segment],
    cx: float,
    cy: float,
    r: float,
    start_deg: float,
    end_deg: float,
    kind: str,
    steps: int = 6,
) -> None:
    if r <= 0.01:
        return
    start = (start_deg * math.pi) / 180
    end = (end_deg * math.pi) / 180
    step = (end - start) / steps
    for i in range(steps):
        a1 = start + step * i
        a2 = start + step * (i + 1)
        add_segment(
            segments,
            cx + r * math.cos(a1),
            cy + r * math.sin(a1),
            cx + r * math.cos(a2),
            cy + r * math.sin(a2),
            kind,
        )


def add_vertical_slot(
    segments: MutableSequence[Segment],
    x_center: float,
    y1: float,
    y2: float,
    slot_w: float,
    kind: str = "cut",
) -> None:
    """Rectangular vertical slot centered on x_center: left/right sides + top/bottom caps."""
    half = slot_w / 2
    x_left = x_center - half
    x_right = x_center + half
    add_segment(segments, x_left, y1, x_left, y2, kind)
    add_segment(segments, x_right, y1, x_right, y2, kind)
    add_segment(segments, x_left, y1, x_right, y1, kind)
    add_segment(segments, x_left, y2, x_right, y2, kind)


def add_vertical_slot_rounded(
    segments: MutableSequence[Segment],
    x_center: float,
    y1: float,
    y2: float,
    slot_w: float,
    thickness_mm: float,
    kind: str = "cut",
) -> None:
    """Rounded vertical slot with small corner arcs."""
    half = slot_w / 2
    x_left = x_center - half
    x_right = x_center + half
    r = slot_corner_radius(thickness_mm, slot_w)

    if r < 0.2 or y2 - y1 < r * 2:
        add_vertical_slot(segments, x_center, y1, y2, slot_w, kind)
        return

    add_segment(segments, x_left + r, y1, x_right - r, y1, kind)
    add_arc_approx(segments, x_right - r, y1 + r, r, 270, 360, kind)
    add_segment(segments, x_right, y1 + r, x_right, y2 - r, kind)
    add_arc_approx(segments, x_right - r, y2 - r, r, 0, 90, kind)
    add_segment(segments, x_right - r, y2, x_left + r, y2, kind)
    add_arc_approx(segments, x_left + r, y2 - r, r, 90, 180, kind)
    add_segment(segments, x_left, y2 - r, x_left, y1 + r, kind)
    add_arc_approx(segments, x_left + r, y1 + r, r, 180, 270, kind)


def add_horizontal_cut_with_gaps(
    segments: MutableSequence[Segment],
    y: float,
    x_start: float,
    x_end: float,
    gaps: Sequence[Gap],
) -> None:
    """Draw a horizontal cut at y, interrupted by gaps ([x_left, x_right] pairs)."""
    sorted_gaps: List[Gap] = sorted(gaps, key=lambda g: g[0])
    cursor = min(x_start, x_end)
    end = max(x_start, x_end)

    for g_left, g_right in sorted_gaps:
        if cursor < g_left:
            add_segment(segments, cursor, y, g_left, y, "cut")
        cursor = max(cursor, g_right)

    if cursor < end:
        add_segment(segments, cursor, y, end, y, "cut")


def manufacturing_dims(geometry: dict) -> Tuple[float, float, float, float, float]:
    """Extract L, W, H, thickness_mm, glue_tab_mm from a geometry dict."""
    mfg = geometry.get("manufacturing") or {}
    length = float(mfg["length"])
    width = float(mfg["width"])
    height = float(mfg["height"])
    thickness_mm = float(geometry.get("thickness_mm", 0))
    glue_tab_mm = float(geometry.get("glue_tab_mm", 0))
    return length, width, height, thickness_mm, glue_tab_mm
