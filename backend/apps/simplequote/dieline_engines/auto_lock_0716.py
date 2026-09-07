"""FEFCO 0716 auto-lock bottom carton segment builder.

Ported from frontend/src/lib/packaging/dieline0716.ts.
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


def build_auto_lock_bottom_segments(geometry: dict, flap_gap_mm: float = 2) -> List[Segment]:
    """FEFCO 0716 auto-lock bottom: lock structure 1.25W + body H + top tuck H."""
    L, W, H, thickness_mm, glue = manufacturing_dims(geometry)
    gap = max(0, flap_gap_mm)
    lock_extra = W * 0.25

    x_glue = 0
    x_l1 = glue
    x_w1 = glue + L
    x_l2 = glue + L + W
    x_w2 = glue + L + W + L
    x_end = glue + 2 * L + 2 * W

    y_top = 0
    y_body_top = W + lock_extra
    y_body_bot = W + lock_extra + H
    y_bot = W + lock_extra + 2 * H

    slot_w = slot_width_from_thickness(thickness_mm)
    half = slot_w / 2
    joint_xs = [x_w1, x_l2, x_w2]
    joint_gaps = [(x - half, x + half) for x in joint_xs]

    dust_w = max(W * 0.35, 20)
    tuck_depth = max(H * 0.85, 12)
    latch_slot_w = max(slot_w, min(W * 0.08, 32))
    latch_half = latch_slot_w / 2

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
    add_segment(segments, x_l1, y_body_top - lock_extra, x_end, y_body_top - lock_extra, "crease")

    lock_mid_y = y_body_top - lock_extra / 2
    l_flap_centers = [x_l1 + L / 2, x_l2 + L / 2]
    for xc in l_flap_centers:
        add_vertical_slot_rounded(
            segments, xc, y_top, y_body_top - lock_extra, latch_slot_w, thickness_mm
        )
        add_segment(segments, xc - latch_half, lock_mid_y, xc + latch_half, lock_mid_y, "cut")

    top_tuck_y = y_body_top - tuck_depth
    for xc in [x_l1 + L / 2, x_l2 + L / 2]:
        add_segment(segments, xc - dust_w / 2, y_top, xc + dust_w / 2, y_top, "cut")
        add_segment(segments, xc - dust_w / 2, y_top, xc - dust_w / 2, top_tuck_y, "cut")
        add_segment(segments, xc + dust_w / 2, y_top, xc + dust_w / 2, top_tuck_y, "cut")

    for xc in [x_w1 + W / 2, x_w2 + W / 2]:
        tuck_half = min(W * 0.4, 40)
        add_segment(segments, xc - tuck_half, y_top, xc + tuck_half, y_top, "cut")
        add_segment(segments, xc - tuck_half, y_top, xc, top_tuck_y - gap, "cut")
        add_segment(segments, xc + tuck_half, y_top, xc, top_tuck_y - gap, "cut")

    return segments
