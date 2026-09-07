"""FEFCO 0427 mailer / hinged-lid self-locking tray segment builder.

Ported from frontend/src/lib/packaging/dieline0427.ts.
"""

from __future__ import annotations

from typing import List, MutableSequence

from .utils import (
    Segment,
    add_arc_approx,
    add_bleed_rect,
    add_segment,
    add_vertical_slot,
    manufacturing_dims,
)


def compute_0427_blank_size(
    length_mm: float,
    width_mm: float,
    height_mm: float,
    thickness_mm: float,
) -> dict:
    L = length_mm
    W = width_mm
    H = height_mm
    t = max(0.1, thickness_mm)
    tuck_height_mm = max(H - t, H * 0.9, 12)
    blank_width_mm = L + 2 * W
    blank_height_mm = 2 * H + 2 * W + tuck_height_mm
    return {
        "blank_width_mm": blank_width_mm,
        "blank_height_mm": blank_height_mm,
        "tuck_height_mm": tuck_height_mm,
    }


def _add_lock_slots(
    segments: MutableSequence[Segment],
    x: float,
    y_base: float,
    slot_h: float,
    slot_w: float,
    gap: float,
) -> None:
    """Vertical lock slots on base panel sides."""
    y1 = y_base + gap
    y2 = y1 + slot_h
    add_vertical_slot(segments, x, y1, y2, slot_w)


def _add_tuck_ear_slots(
    segments: MutableSequence[Segment],
    cx: float,
    y: float,
    ear_w: float,
    ear_d: float,
    spacing: float,
) -> None:
    """Tuck-ear slots on front wall top."""
    x_l = cx - spacing / 2
    x_r = cx + spacing / 2
    add_segment(segments, x_l - ear_w / 2, y, x_l + ear_w / 2, y, "cut")
    add_segment(segments, x_l - ear_w / 2, y, x_l - ear_w / 2, y + ear_d, "cut")
    add_segment(segments, x_l + ear_w / 2, y, x_l + ear_w / 2, y + ear_d, "cut")
    add_segment(segments, x_r - ear_w / 2, y, x_r + ear_w / 2, y, "cut")
    add_segment(segments, x_r - ear_w / 2, y, x_r - ear_w / 2, y + ear_d, "cut")
    add_segment(segments, x_r + ear_w / 2, y, x_r + ear_w / 2, y + ear_d, "cut")


def _build_left_side_wall(
    segments: MutableSequence[Segment],
    W: float,
    H: float,
    y_front: float,
    y_bot: float,
    y_back: float,
    corner_flap: float,
    tab_w: float,
    tab_h: float,
) -> None:
    x_outer = 0
    x_crease = W
    y_corner_bot = y_front
    y_corner_top = y_bot

    # Outer contour — left side-wall assembly
    add_segment(segments, x_outer, y_corner_bot, x_outer, y_corner_top + corner_flap, "cut")
    add_segment(
        segments, x_outer, y_corner_top + corner_flap, x_crease - tab_w, y_corner_top + corner_flap, "cut"
    )
    add_segment(
        segments, x_crease - tab_w, y_corner_top + corner_flap, x_crease - tab_w, y_corner_top, "cut"
    )
    add_segment(segments, x_crease - tab_w, y_corner_top, x_crease, y_corner_top, "cut")

    # Top corner flap
    add_segment(segments, x_crease, y_corner_top, x_crease, y_corner_top + corner_flap, "crease")
    add_segment(
        segments, x_crease, y_corner_top + corner_flap, x_outer, y_corner_top + corner_flap, "crease"
    )
    add_segment(segments, x_outer, y_corner_top + corner_flap, x_outer, y_back, "cut")

    # Back-wall side corner flap
    add_segment(segments, x_outer, y_back, x_crease, y_back, "cut")
    add_segment(segments, x_crease, y_back, x_crease, y_back + H, "crease")

    # Bottom corner flap
    add_segment(segments, x_crease, y_corner_bot, x_crease, y_corner_bot - corner_flap, "crease")
    add_segment(
        segments, x_crease, y_corner_bot - corner_flap, x_outer, y_corner_bot - corner_flap, "cut"
    )
    add_segment(segments, x_outer, y_corner_bot - corner_flap, x_outer, y_corner_bot, "cut")

    # Lock tabs (inner fold side wall)
    tab_y = y_front + (y_bot - y_front) * 0.35
    add_segment(segments, x_outer, tab_y, x_outer - tab_w, tab_y, "cut")
    add_segment(segments, x_outer - tab_w, tab_y, x_outer - tab_w, tab_y + tab_h, "cut")
    add_segment(segments, x_outer - tab_w, tab_y + tab_h, x_outer, tab_y + tab_h, "cut")

    tab_y2 = y_front + (y_bot - y_front) * 0.65
    add_segment(segments, x_outer, tab_y2, x_outer - tab_w, tab_y2, "cut")
    add_segment(segments, x_outer - tab_w, tab_y2, x_outer - tab_w, tab_y2 + tab_h, "cut")
    add_segment(segments, x_outer - tab_w, tab_y2 + tab_h, x_outer, tab_y2 + tab_h, "cut")

    # Side-wall creases
    add_segment(segments, x_crease, y_front, x_crease, y_bot, "crease")
    add_segment(segments, x_outer, y_front, x_outer, y_bot, "crease")


def _build_right_side_wall(
    segments: MutableSequence[Segment],
    total_w: float,
    W: float,
    H: float,
    y_front: float,
    y_bot: float,
    y_back: float,
    corner_flap: float,
    tab_w: float,
    tab_h: float,
) -> None:
    x_crease = total_w - W
    x_outer = total_w
    y_corner_bot = y_front
    y_corner_top = y_bot

    add_segment(segments, x_outer, y_corner_bot, x_outer, y_corner_top + corner_flap, "cut")
    add_segment(
        segments, x_outer, y_corner_top + corner_flap, x_crease + tab_w, y_corner_top + corner_flap, "cut"
    )
    add_segment(
        segments, x_crease + tab_w, y_corner_top + corner_flap, x_crease + tab_w, y_corner_top, "cut"
    )
    add_segment(segments, x_crease + tab_w, y_corner_top, x_crease, y_corner_top, "cut")

    add_segment(segments, x_crease, y_corner_top, x_crease, y_corner_top + corner_flap, "crease")
    add_segment(
        segments, x_crease, y_corner_top + corner_flap, x_outer, y_corner_top + corner_flap, "crease"
    )
    add_segment(segments, x_outer, y_corner_top + corner_flap, x_outer, y_back, "cut")

    add_segment(segments, x_outer, y_back, x_crease, y_back, "cut")
    add_segment(segments, x_crease, y_back, x_crease, y_back + H, "crease")

    add_segment(segments, x_crease, y_corner_bot, x_crease, y_corner_bot - corner_flap, "crease")
    add_segment(
        segments, x_crease, y_corner_bot - corner_flap, x_outer, y_corner_bot - corner_flap, "cut"
    )
    add_segment(segments, x_outer, y_corner_bot - corner_flap, x_outer, y_corner_bot, "cut")

    tab_y = y_front + (y_bot - y_front) * 0.35
    add_segment(segments, x_outer, tab_y, x_outer + tab_w, tab_y, "cut")
    add_segment(segments, x_outer + tab_w, tab_y, x_outer + tab_w, tab_y + tab_h, "cut")
    add_segment(segments, x_outer + tab_w, tab_y + tab_h, x_outer, tab_y + tab_h, "cut")

    tab_y2 = y_front + (y_bot - y_front) * 0.65
    add_segment(segments, x_outer, tab_y2, x_outer + tab_w, tab_y2, "cut")
    add_segment(segments, x_outer + tab_w, tab_y2, x_outer + tab_w, tab_y2 + tab_h, "cut")
    add_segment(segments, x_outer + tab_w, tab_y2 + tab_h, x_outer, tab_y2 + tab_h, "cut")

    add_segment(segments, x_crease, y_front, x_crease, y_bot, "crease")
    add_segment(segments, x_outer, y_front, x_outer, y_bot, "crease")


def _build_dust_flap(
    segments: MutableSequence[Segment],
    side: str,
    x_attach: float,
    y_lid0: float,
    y_lid1: float,
    dust_depth: float,
    dust_r: float,
) -> None:
    if side == "left":
        x_outer = x_attach - dust_depth
        add_segment(segments, x_attach, y_lid0, x_attach, y_lid1, "crease")
        add_segment(segments, x_attach, y_lid1, x_outer + dust_r, y_lid1, "cut")
        add_arc_approx(segments, x_outer + dust_r, y_lid1 - dust_r, dust_r, 90, 180, "cut")
        add_segment(segments, x_outer, y_lid1 - dust_r, x_outer, y_lid0 + dust_r, "cut")
        add_arc_approx(segments, x_outer + dust_r, y_lid0 + dust_r, dust_r, 180, 270, "cut")
        add_segment(segments, x_outer + dust_r, y_lid0, x_attach, y_lid0, "cut")
        add_segment(segments, x_attach, y_lid0, x_attach, y_lid1, "crease")
    else:
        x_outer = x_attach + dust_depth
        add_segment(segments, x_attach, y_lid0, x_attach, y_lid1, "crease")
        add_segment(segments, x_attach, y_lid0, x_outer - dust_r, y_lid0, "cut")
        add_arc_approx(segments, x_outer - dust_r, y_lid0 + dust_r, dust_r, 270, 360, "cut")
        add_segment(segments, x_outer, y_lid0 + dust_r, x_outer, y_lid1 - dust_r, "cut")
        add_arc_approx(segments, x_outer - dust_r, y_lid1 - dust_r, dust_r, 0, 90, "cut")
        add_segment(segments, x_outer - dust_r, y_lid1, x_attach, y_lid1, "cut")


def _build_tuck_flap(
    segments: MutableSequence[Segment],
    cx: float,
    y_base: float,
    tuck_w: float,
    tuck_h: float,
    tuck_r: float,
    ear_w: float,
    ear_h: float,
) -> None:
    x_l = cx - tuck_w / 2
    x_r = cx + tuck_w / 2
    y_top = y_base + tuck_h

    add_segment(segments, x_l + tuck_r, y_base, x_r - tuck_r, y_base, "crease")
    add_arc_approx(segments, x_r - tuck_r, y_base + tuck_r, tuck_r, 270, 0, "cut")
    add_segment(segments, x_r, y_base + tuck_r, x_r, y_top - tuck_r, "cut")
    add_arc_approx(segments, x_r - tuck_r, y_top - tuck_r, tuck_r, 0, 90, "cut")
    add_segment(segments, x_r - tuck_r, y_top, x_l + tuck_r, y_top, "cut")
    add_arc_approx(segments, x_l + tuck_r, y_top - tuck_r, tuck_r, 90, 180, "cut")
    add_segment(segments, x_l, y_top - tuck_r, x_l, y_base + tuck_r, "cut")
    add_arc_approx(segments, x_l + tuck_r, y_base + tuck_r, tuck_r, 180, 270, "cut")

    # Tuck side ears
    ear_xl = cx - tuck_w * 0.35
    ear_xr = cx + tuck_w * 0.35
    add_segment(segments, ear_xl - ear_w / 2, y_base, ear_xl + ear_w / 2, y_base, "cut")
    add_segment(segments, ear_xl - ear_w / 2, y_base, ear_xl - ear_w / 2, y_base - ear_h, "cut")
    add_segment(segments, ear_xl + ear_w / 2, y_base, ear_xl + ear_w / 2, y_base - ear_h, "cut")
    add_segment(segments, ear_xr - ear_w / 2, y_base, ear_xr + ear_w / 2, y_base, "cut")
    add_segment(segments, ear_xr - ear_w / 2, y_base, ear_xr - ear_w / 2, y_base - ear_h, "cut")
    add_segment(segments, ear_xr + ear_w / 2, y_base, ear_xr + ear_w / 2, y_base - ear_h, "cut")


def build_0427_segments(geometry: dict) -> List[Segment]:
    L, W, H, t, _glue = manufacturing_dims(geometry)

    blank = compute_0427_blank_size(L, W, H, t)
    total_w = blank["blank_width_mm"]
    total_h = blank["blank_height_mm"]
    tuck_h = blank["tuck_height_mm"]

    x_l = W
    x_r = W + L
    cx = W + L / 2

    y_front0 = 0
    y_front1 = H
    y_bot0 = H
    y_bot1 = H + W
    y_back0 = y_bot1
    y_back1 = y_bot1 + H
    y_lid0 = y_back1
    y_lid1 = y_back1 + W
    y_tuck0 = y_lid1
    y_tuck1 = y_lid1 + tuck_h

    tuck_r = min(0.6 * H, 10, tuck_h * 0.35)
    dust_depth = max(W * 0.42, H * 1.1)
    dust_r = min(W * 0.12, H * 0.5, 15)
    corner_flap = max(H * 0.85, H - t)
    slot_w = max(6, W * 0.055)
    slot_h = max(10, H * 0.55)
    slot_gap = max(4, H * 0.12)
    tab_w = max(5, W * 0.045)
    tab_h = max(8, H * 0.45)
    ear_w = max(5, W * 0.04)
    ear_h = max(4, H * 0.2)
    tuck_w = L * 0.55
    ear_spacing = L * 0.38

    segments: List[Segment] = []
    add_bleed_rect(segments, total_w, total_h)

    # Front wall
    add_segment(segments, x_l, y_front0, x_r, y_front0, "cut")
    add_segment(segments, x_l, y_front0, x_l, y_front1, "crease")
    add_segment(segments, x_r, y_front0, x_r, y_front1, "crease")
    add_segment(segments, x_l, y_front1, x_r, y_front1, "crease")
    _add_tuck_ear_slots(segments, cx, y_front1, ear_w, ear_h, ear_spacing)

    # Base panel
    add_segment(segments, x_l, y_bot0, x_r, y_bot0, "crease")
    add_segment(segments, x_l, y_bot1, x_r, y_bot1, "crease")
    _add_lock_slots(segments, x_l + slot_gap + slot_w, y_bot0, slot_h, slot_w, slot_gap)
    _add_lock_slots(segments, x_l + slot_gap + slot_w * 2.5, y_bot0, slot_h, slot_w, slot_gap * 2.5)
    _add_lock_slots(segments, x_r - slot_gap - slot_w, y_bot0, slot_h, slot_w, slot_gap)
    _add_lock_slots(segments, x_r - slot_gap - slot_w * 2.5, y_bot0, slot_h, slot_w, slot_gap * 2.5)

    # Back wall
    add_segment(segments, x_l, y_back0, x_r, y_back0, "crease")
    add_segment(segments, x_l, y_back1, x_r, y_back1, "crease")

    # Lid body
    add_segment(segments, x_l, y_lid0, x_r, y_lid0, "crease")
    add_segment(segments, x_l, y_lid1, x_r, y_lid1, "crease")

    # Dust flaps
    _build_dust_flap(segments, "left", x_l, y_lid0, y_lid1, dust_depth, dust_r)
    _build_dust_flap(segments, "right", x_r, y_lid0, y_lid1, dust_depth, dust_r)

    # Tuck flap
    _build_tuck_flap(segments, cx, y_tuck0, tuck_w, tuck_h, tuck_r, ear_w, ear_h)

    # Side-wall assemblies
    _build_left_side_wall(segments, W, H, y_bot0, y_bot1, y_back0, corner_flap, tab_w, tab_h)
    _build_right_side_wall(segments, total_w, W, H, y_bot0, y_bot1, y_back0, corner_flap, tab_w, tab_h)

    # Main vertical creases
    for x in [x_l, x_r]:
        add_segment(segments, x, y_front0, x, y_tuck1, "crease")

    # Top outer contour
    add_segment(segments, 0, y_tuck1, total_w, y_tuck1, "cut")

    return segments
