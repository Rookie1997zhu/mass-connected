"""Upload validation helpers for print3d STL / STEP files."""
from __future__ import annotations

import struct

STP_MAGIC = b"ISO-10303-21"
ALLOWED_EXT = {".stl", ".stp", ".step"}


def detect_ext(filename: str) -> str:
    name = (filename or "").lower()
    for ext in ALLOWED_EXT:
        if name.endswith(ext):
            return ext
    return ""


def validate_print3d_upload(upload, max_bytes: int) -> tuple[str | None, str | None, str]:
    """Return (error_code, error_message, ext). Success → (None, None, ext)."""
    if not upload:
        return "PRINT3D_FILE_INVALID", "请上传 3D 模型文件", ""
    ext = detect_ext(upload.name or "")
    if not ext:
        return "PRINT3D_FILE_INVALID", "仅支持 .stl / .stp / .step 文件", ""
    size = getattr(upload, "size", 0) or 0
    if size <= 0:
        return "PRINT3D_FILE_INVALID", "文件为空", ""
    if size > max_bytes:
        return "PRINT3D_FILE_TOO_LARGE", f"文件超过 {max_bytes // (1024 * 1024)}MB 上限", ""

    head = upload.read(128)
    upload.seek(0)

    if ext in (".stp", ".step"):
        if STP_MAGIC not in head:
            return "PRINT3D_FILE_INVALID", "文件不是有效的 STEP 格式", ""
        return None, None, ext

    # STL: ASCII starts with solid; binary has 80-byte header + uint32 facet count
    if head.lstrip().lower().startswith(b"solid"):
        return None, None, ext
    if size < 84:
        return "PRINT3D_FILE_INVALID", "无效的 STL 文件", ""
    upload.seek(80)
    count_bytes = upload.read(4)
    upload.seek(0)
    if len(count_bytes) != 4:
        return "PRINT3D_FILE_INVALID", "无效的 STL 文件", ""
    facet_count = struct.unpack("<I", count_bytes)[0]
    expected = 84 + facet_count * 50
    # Allow small trailer slack; reject obvious mismatch
    if facet_count == 0 or abs(expected - size) > 512:
        return "PRINT3D_FILE_INVALID", "无效的二进制 STL 文件", ""
    return None, None, ext
