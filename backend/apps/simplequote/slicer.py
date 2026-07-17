"""PrusaSlicer CLI + G-code filament/time extraction for print3d quotes.

Extracted from MIT Machine Shop Suite quote engine; silent fake fallbacks removed.
"""
from __future__ import annotations

import logging
import os
import re
import shutil
import subprocess
from typing import Any

logger = logging.getLogger(__name__)

DEFAULT_SLICER_PATH = os.environ.get("PRUSA_SLICER_PATH", "prusa-slicer")
DEFAULT_TIMEOUT = int(os.environ.get("PRUSA_SLICER_TIMEOUT", "300"))


class SlicerError(Exception):
    """Slicing or G-code parse failure with a stable error code."""

    def __init__(self, code: str, message: str):
        self.code = code
        self.message = message
        super().__init__(message)


def resolve_executable(path_value: str | None) -> str | None:
    if not path_value:
        return None
    if os.path.exists(path_value):
        return path_value
    return shutil.which(path_value)


def wrap_headless_gui_cmd(argv: list[str]) -> list[str]:
    """When DISPLAY is unset, run GTK/wx apps under xvfb-run if available."""
    if os.environ.get("DISPLAY"):
        return argv
    xvfb_run = shutil.which("xvfb-run")
    xauth = shutil.which("xauth")
    if not xvfb_run or not xauth:
        return argv
    return [xvfb_run, "-a", *argv]


def convert_stl_to_gcode(
    input_path: str,
    output_path: str,
    params: dict[str, Any],
    slicer_path: str | None = None,
    timeout: int | None = None,
) -> None:
    """Convert STL to G-code via PrusaSlicer CLI. Raises SlicerError on failure."""
    resolved = resolve_executable(slicer_path or DEFAULT_SLICER_PATH)
    if not resolved:
        raise SlicerError("PRINT3D_SLICER_NOT_FOUND", "PrusaSlicer 未安装或路径无效")

    cmd = [
        resolved,
        "--export-gcode",
        input_path,
        "--output",
        output_path,
        "--layer-height",
        str(params.get("layer_height", 0.2)),
        "--fill-density",
        f"{params.get('infill_density', 20)}%",
        "--bed-temperature",
        str(params.get("bed_temp", 60)),
        "--temperature",
        str(params.get("extruder_temp", 210)),
        "--perimeter-speed",
        str(params.get("perimeter_speed", 60)),
        "--infill-speed",
        str(params.get("infill_speed", 80)),
        "--solid-infill-speed",
        str(params.get("solid_infill_speed", 60)),
        # 提供密度后 PrusaSlicer 才会写出 "filament used [g]"
        "--filament-density",
        str(params.get("filament_density", 1.24)),
    ]
    if params.get("support"):
        cmd.append("--support-material")

    cmd = wrap_headless_gui_cmd(cmd)
    run_timeout = timeout if timeout is not None else DEFAULT_TIMEOUT
    logger.info("print3d slice cmd=%s timeout=%s", cmd[:4], run_timeout)

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=run_timeout,
            check=False,
        )
    except subprocess.TimeoutExpired as exc:
        raise SlicerError("PRINT3D_SLICE_TIMEOUT", "切片超时，模型可能过于复杂") from exc
    except OSError as exc:
        raise SlicerError("PRINT3D_SLICE_FAILED", f"切片进程启动失败: {exc}") from exc

    if result.returncode != 0:
        detail = (result.stderr or result.stdout or "unknown").strip()[:500]
        raise SlicerError("PRINT3D_SLICE_FAILED", f"切片失败: {detail}")

    if not os.path.exists(output_path) or os.path.getsize(output_path) == 0:
        raise SlicerError("PRINT3D_SLICE_FAILED", "切片未生成有效 G-code")


def _parse_time_string(time_str: str) -> int | None:
    hours = int(m.group(1)) if (m := re.search(r"(\d+)\s*h", time_str, re.I)) else 0
    minutes = int(m.group(1)) if (m := re.search(r"(\d+)\s*m(?:in)?", time_str, re.I)) else 0
    seconds = int(m.group(1)) if (m := re.search(r"(\d+)\s*s", time_str, re.I)) else 0
    total = hours * 3600 + minutes * 60 + seconds
    return total if total > 0 else None


def extract_filament_usage(
    gcode_path: str, density_g_cm3: float | None = None
) -> dict[str, float | int]:
    """Parse PrusaSlicer G-code comments. Raises if weight or time missing.

    density_g_cm3: 当 G-code 缺少 [g] 注释时，用体积 [cm3] × 密度换算重量。
    """
    try:
        with open(gcode_path, "r", encoding="utf-8", errors="ignore") as fh:
            content = fh.read()
    except OSError as exc:
        raise SlicerError("PRINT3D_GCODE_PARSE_FAILED", f"无法读取 G-code: {exc}") from exc

    filament_used_g = None
    filament_used_mm = None
    filament_used_cm3 = None
    estimated_time_seconds = None

    if m := re.search(r";\s*filament\s+used\s*\[g\]\s*=\s*([\d.]+)", content, re.I):
        filament_used_g = float(m.group(1))
    elif m := re.search(r";\s*filament_used_g\s*=\s*([\d.]+)", content, re.I):
        filament_used_g = float(m.group(1))

    if m := re.search(r";\s*filament\s+used\s*\[mm\]\s*=\s*([\d.]+)", content, re.I):
        filament_used_mm = float(m.group(1))
    elif m := re.search(r";\s*filament_used_mm\s*=\s*([\d.]+)", content, re.I):
        filament_used_mm = float(m.group(1))

    if m := re.search(r";\s*filament\s+used\s*\[cm3\]\s*=\s*([\d.]+)", content, re.I):
        filament_used_cm3 = float(m.group(1))

    if m := re.search(r";\s*estimated\s+printing\s+time.*?=\s*(.+?)(?:\n|$)", content, re.I):
        estimated_time_seconds = _parse_time_string(m.group(1).strip())

    if (
        (filament_used_g is None or filament_used_g <= 0)
        and filament_used_cm3
        and density_g_cm3
        and density_g_cm3 > 0
    ):
        filament_used_g = filament_used_cm3 * density_g_cm3

    if filament_used_g is None or filament_used_g <= 0:
        raise SlicerError(
            "PRINT3D_GCODE_PARSE_FAILED",
            "G-code 缺少有效耗材重量（filament used [g]）",
        )
    if estimated_time_seconds is None or estimated_time_seconds <= 0:
        raise SlicerError(
            "PRINT3D_GCODE_PARSE_FAILED",
            "G-code 缺少有效打印时间（estimated printing time）",
        )

    return {
        "filament_length_mm": round(filament_used_mm or 0, 2),
        "filament_volume_cm3": round(filament_used_cm3 or 0, 4),
        "filament_weight_g": round(filament_used_g, 2),
        "estimated_time_seconds": int(estimated_time_seconds),
        "estimated_time_hours": round(estimated_time_seconds / 3600.0, 4),
    }


def convert_step_to_stl_ocp(input_path: str, output_path: str) -> None:
    """Convert STEP to binary STL using OpenCASCADE (subprocess-free in worker)."""
    try:
        from OCP.IFSelect import IFSelect_RetDone
        from OCP.STEPControl import STEPControl_Reader
        from OCP.BRepMesh import BRepMesh_IncrementalMesh
        from OCP.StlAPI import StlAPI_Writer
    except ImportError as exc:
        raise SlicerError("PRINT3D_STEP_CONVERT_FAILED", "OpenCASCADE 不可用，无法转换 STEP") from exc

    reader = STEPControl_Reader()
    if reader.ReadFile(input_path) != IFSelect_RetDone:
        raise SlicerError("PRINT3D_STEP_CONVERT_FAILED", "STEP 文件读取失败")
    reader.TransferRoots()
    shape = reader.OneShape()
    if shape is None or shape.IsNull():
        raise SlicerError("PRINT3D_STEP_CONVERT_FAILED", "STEP 模型为空")

    mesh = BRepMesh_IncrementalMesh(shape, 0.5, False, 0.5, True)
    mesh.Perform()
    if not mesh.IsDone():
        raise SlicerError("PRINT3D_STEP_CONVERT_FAILED", "STEP 网格化失败")

    writer = StlAPI_Writer()
    writer.ASCIIMode = False
    if not writer.Write(shape, output_path):
        raise SlicerError("PRINT3D_STEP_CONVERT_FAILED", "STEP 写出 STL 失败")
    if not os.path.exists(output_path) or os.path.getsize(output_path) == 0:
        raise SlicerError("PRINT3D_STEP_CONVERT_FAILED", "STEP 转换未生成 STL")
