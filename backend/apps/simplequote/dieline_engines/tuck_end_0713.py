"""FEFCO 0713 tuck-end carton segment builder.

Ported from frontend/src/lib/packaging/dieline0713.ts.
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


def build_tuck_end_segments(geometry: dict, flap_gap_mm: float = 2) -> List[Segment]:
    """FEFCO 0713 tuck-end: bottom tuck W + body H + top tuck H."""
    L, W, H, thickness_mm, glue = manufacturing_dims(geometry)
    gap = max(0, flap_gap_mm)

    x_glue = 0
    x_l1 = glue
    x_w1 = glue + L
    x_l2 = glue + L + W
    x_w2 = glue + L + W + L
    x_end = glue + 2 * L + 2 * W

    y_top = 0
    y_body_top = W
    y_body_bot = W + H
    y_bot = W + 2 * H

    slot_w = slot_width_from_thickness(thickness_mm)
    half = slot_w / 2
    joint_xs = [x_w1, x_l2, x_w2]
    joint_gaps = [(x - half, x + half) for x in joint_xs]

    dust_w = max(W * 0.35, 20)
    tuck_depth = max(H * 0.85, 12)

    segments: List[Segment] = []
    add_bleed_rect(segments, x_end, y_bot)

    add_horizontal_cut_with_gaps(segments, y_bot, x_l1, x_end, joint_gaps)
    add_segment(segments, x_end, y_bot, x_end, y_top, "cut")
    add_horizontal_cut_with_gaps(segments, y_top, x_l1, x_end, joint_gaps)

    add_segment(segments, x_l1, y_top, x_l1, y_body_top, "cut")
    add_segment(segments, x_l1, y_body_top, x_glue, y_body_top, "cut")
    add_segment(segments, x_glue, y_body_top, x_glue, y_body_bot, "cut")
    add_segment(segments, x_glue, y_body_bot, x_l1, y_body_bot, "cut")
    add_segment(segments, x_l1, y_body_bot, x_l1, y_bot, "cut")

    for xi in joint_xs:
        add_vertical_slot_rounded(segments, xi, y_top, y_body_top, slot_w, thickness_mm)
        add_vertical_slot_rounded(segments, xi, y_body_bot, y_bot, slot_w, thickness_mm)

    for xi in [x_l1, x_w1, x_l2, x_w2]:
        add_segment(segments, xi, y_body_top, xi, y_body_bot, "crease")
    add_segment(segments, x_l1, y_body_top, x_end, y_body_top, "crease")
    add_segment(segments, x_l1, y_body_bot, x_end, y_body_bot, "crease")

    top_tuck_y = y_body_top - tuck_depth
    bot_tuck_y = y_body_bot + tuck_depth
    for xc in [x_l1 + L / 2, x_l2 + L / 2]:
        add_segment(segments, xc - dust_w / 2, y_top, xc + dust_w / 2, y_top, "cut")
        add_segment(segments, xc - dust_w / 2, y_top, xc - dust_w / 2, top_tuck_y, "cut")
        add_segment(segments, xc + dust_w / 2, y_top, xc + dust_w / 2, top_tuck_y, "cut")
        add_segment(segments, xc - dust_w / 2, y_bot, xc + dust_w / 2, y_bot, "cut")
        add_segment(segments, xc - dust_w / 2, bot_tuck_y, xc - dust_w / 2, y_bot, "cut")
        add_segment(segments, xc + dust_w / 2, bot_tuck_y, xc + dust_w / 2, y_bot, "cut")

    for xc in [x_w1 + W / 2, x_w2 + W / 2]:
        tuck_half = min(W * 0.4, 40)
        add_segment(segments, xc - tuck_half, y_top, xc + tuck_half, y_top, "cut")
        add_segment(segments, xc - tuck_half, y_top, xc, top_tuck_y - gap, "cut")
        add_segment(segments, xc + tuck_half, y_top, xc, top_tuck_y - gap, "cut")
        add_segment(segments, xc - tuck_half, y_bot, xc + tuck_half, y_bot, "cut")
        add_segment(segments, xc - tuck_half, y_bot, xc, bot_tuck_y + gap, "cut")
        add_segment(segments, xc + tuck_half, y_bot, xc, bot_tuck_y + gap, "cut")

    return segments
