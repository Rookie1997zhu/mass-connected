"""Formula dieline engines: build cut/crease/bleed segments by engine_key.

Ports frontend packaging dieline builders for authoritative backend DXF/PDF export.
"""

from __future__ import annotations

from typing import Callable, Dict, List

from .auto_lock_0716 import build_auto_lock_bottom_segments
from .folding_shipping import build_folding_shipping_segments
from .mailer_0427 import build_0427_segments, compute_0427_blank_size
from .rsc_0201 import build_0201_segments
from .tuck_end_0713 import build_tuck_end_segments

FORMULA_ENGINE_KEYS = (
    "slotted_rsc",
    "folding_shipping",
    "mailer_folder",
    "tuck_end",
    "auto_lock_bottom",
)

_ENGINE_BUILDERS: Dict[str, Callable[[dict], List[dict]]] = {
    "slotted_rsc": build_0201_segments,
    "folding_shipping": build_folding_shipping_segments,
    "mailer_folder": build_0427_segments,
    "tuck_end": build_tuck_end_segments,
    "auto_lock_bottom": build_auto_lock_bottom_segments,
}


def build_segments_by_engine(
    engine_key: str, geometry: dict, flap_gap_mm: float | None = None
) -> List[dict]:
    """Dispatch to the formula builder for ``engine_key``.

    Raises:
        ValueError: if ``engine_key`` is not a known formula engine.
    """
    builder = _ENGINE_BUILDERS.get(engine_key)
    if builder is None:
        raise ValueError(f"Unknown dieline engine_key: {engine_key!r}")
    if engine_key in ("tuck_end", "auto_lock_bottom"):
        gap = 2.0 if flap_gap_mm is None else float(flap_gap_mm)
        return builder(geometry, gap)
    return builder(geometry)


__all__ = [
    "FORMULA_ENGINE_KEYS",
    "build_segments_by_engine",
    "build_0201_segments",
    "build_folding_shipping_segments",
    "build_tuck_end_segments",
    "build_auto_lock_bottom_segments",
    "build_0427_segments",
    "compute_0427_blank_size",
]
