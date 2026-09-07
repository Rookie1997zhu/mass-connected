"""FEFCO 0201 / slotted RSC segment builder.

Ported from frontend/src/lib/packaging/boxEngine.ts build0201Segments.
"""

from __future__ import annotations

from typing import List

from .utils import (
    Segment,
    add_bleed_rect,
    add_horizontal_cut_with_gaps,
    add_segment,
    add_vertical_slot_rounded,
    manufacturing_dims,
    slot_width_from_thickness,
)


def build_0201_segments(geometry: dict) -> List[Segment]:
    L, W, H, thickness_mm, glue = manufacturing_dims(geometry)

    x_glue = 0
    x_l1 = glue
    x_w1 = glue + L
    x_l2 = glue + L + W
    x_w2 = glue + L + W + L
    x_end = glue + 2 * L + 2 * W

    y_top = 0
    y_body_top = W / 2
    y_body_bot = W / 2 + H
    y_bot = W + H

    slot_w = slot_width_from_thickness(thickness_mm)
    half = slot_w / 2
    slit_xs = [x_w1, x_l2, x_w2]
    slit_gaps = [(x - half, x + half) for x in slit_xs]

    segments: List[Segment] = []

    add_bleed_rect(segments, x_end, y_bot)

    # Outer contour cut (top/bottom edges leave gaps at slits)
    add_horizontal_cut_with_gaps(segments, y_bot, x_l1, x_end, slit_gaps)
    add_segment(segments, x_end, y_bot, x_end, y_top, "cut")
    add_horizontal_cut_with_gaps(segments, y_top, x_l1, x_end, slit_gaps)
    add_segment(segments, x_l1, y_top, x_l1, y_body_top, "cut")
    add_segment(segments, x_l1, y_body_top, x_glue, y_body_top, "cut")
    add_segment(segments, x_glue, y_body_top, x_glue, y_body_bot, "cut")
    add_segment(segments, x_glue, y_body_bot, x_l1, y_body_bot, "cut")
    add_segment(segments, x_l1, y_body_bot, x_l1, y_bot, "cut")

    # Flap slits (rounded vertical slots ~ board thickness)
    for xi in slit_xs:
        add_vertical_slot_rounded(segments, xi, y_top, y_body_top, slot_w, thickness_mm)
        add_vertical_slot_rounded(segments, xi, y_body_bot, y_bot, slot_w, thickness_mm)

    # Vertical creases (4 panel folds)
    for xi in [x_l1, x_w1, x_l2, x_w2]:
        add_segment(segments, xi, y_body_top, xi, y_body_bot, "crease")

    # Horizontal creases (body / flap boundary)
    add_segment(segments, x_l1, y_body_top, x_end, y_body_top, "crease")
    add_segment(segments, x_l1, y_body_bot, x_end, y_body_bot, "crease")

    return segments
