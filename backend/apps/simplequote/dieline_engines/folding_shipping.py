"""Folding shipping box segment builder.

Ported from frontend/src/lib/packaging/dielineFoldingShipping.ts.
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


def build_folding_shipping_segments(geometry: dict) -> List[Segment]:
    """Folding shipping carton: slotted RSC top + interlocking bottom (alternating vertical slots)."""
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
    top_joint_xs = [x_w1, x_l2, x_w2]
    top_slit_gaps = [(x - half, x + half) for x in top_joint_xs]

    latch_slot_w = max(slot_w, min(W * 0.08, 32))
    latch_half = latch_slot_w / 2
    latch_mid_y = y_body_bot + W / 4

    l_flap_centers = [x_l1 + L / 2, x_l2 + L / 2]
    bottom_gaps = [(xc - latch_half, xc + latch_half) for xc in l_flap_centers]

    segments: List[Segment] = []

    add_bleed_rect(segments, x_end, y_bot)

    add_horizontal_cut_with_gaps(segments, y_top, x_l1, x_end, top_slit_gaps)
    add_segment(segments, x_end, y_bot, x_end, y_top, "cut")
    add_horizontal_cut_with_gaps(segments, y_bot, x_l1, x_end, bottom_gaps)
    add_segment(segments, x_l1, y_top, x_l1, y_body_top, "cut")
    add_segment(segments, x_l1, y_body_top, x_glue, y_body_top, "cut")
    add_segment(segments, x_glue, y_body_top, x_glue, y_body_bot, "cut")
    add_segment(segments, x_glue, y_body_bot, x_l1, y_body_bot, "cut")
    add_segment(segments, x_l1, y_body_bot, x_l1, y_bot, "cut")

    for xi in top_joint_xs:
        add_vertical_slot_rounded(segments, xi, y_top, y_body_top, slot_w, thickness_mm)

    bottom_flaps = [
        {"x": x_l1 + L / 2, "from_bottom": True},
        {"x": x_w1 + W / 2, "from_bottom": False},
        {"x": x_l2 + L / 2, "from_bottom": True},
        {"x": x_w2 + W / 2, "from_bottom": False},
    ]
    for flap in bottom_flaps:
        if flap["from_bottom"]:
            add_vertical_slot_rounded(
                segments, flap["x"], latch_mid_y, y_bot, latch_slot_w, thickness_mm
            )
        else:
            add_vertical_slot_rounded(
                segments, flap["x"], y_body_bot, latch_mid_y, latch_slot_w, thickness_mm
            )

    for xi in [x_l1, x_w1, x_l2, x_w2]:
        add_segment(segments, xi, y_body_top, xi, y_body_bot, "crease")
    add_segment(segments, x_l1, y_body_top, x_end, y_body_top, "crease")
    add_segment(segments, x_l1, y_body_bot, x_end, y_body_bot, "crease")

    return segments
