"""工程图 OCR 服务（阶段 C）。

对上传的 2D 工程图（PDF / PNG / JPG）做离线 OCR（Tesseract），抽取材料、精密度、
颜色等关键字段，作为报价表单的低置信度建议值。子进程 + 超时保护，结果不落库。
仅抽取关键字段，不追求版面还原；识别失败或 tesseract 不可用时回退手动填写。
"""

import multiprocessing as mp
import re
from datetime import datetime, timezone

OCR_TIMEOUT_SEC = 25
OCR_LANG = "eng+kor+chi_sim"
_RAW_EXCERPT_LEN = 500

# 材料关键字 → 规范材料名（顺序影响优先级，先匹配更具体的 ABS+GF）
_MATERIAL_PATTERNS = [
    (r"ABS\s*\+?\s*(GF|G\.F|玻纤|유리)", "ABS+Gf"),
    (r"PA\s*66", "PA66"),
    (r"\bPC\b", "PC"),
    (r"\bPP\b", "PP"),
    (r"\bABS\b", "ABS"),
]

_COLOR_PATTERNS = [
    (r"투명|透明|TRANSPARENT|CLEAR", "transparent"),
    (r"반투명|半透明|SEMI[- ]?TRANS", "semi"),
    (r"PANTONE\s*[0-9A-Z\-]+", "pantone"),
]


def _now_iso():
    return datetime.now(timezone.utc).isoformat()


def _ocr_text_from_file(path, kind):
    """图片直接 OCR；PDF 用 fitz 光栅化首页后 OCR。返回纯文本。"""
    import pytesseract
    from PIL import Image

    if kind == "pdf":
        import fitz  # PyMuPDF

        doc = fitz.open(path)
        if doc.page_count == 0:
            return ""
        page = doc.load_page(0)
        pix = page.get_pixmap(dpi=200)
        mode = "RGB" if pix.n < 4 else "RGBA"
        img = Image.frombytes(mode, (pix.width, pix.height), pix.samples)
        doc.close()
    else:
        img = Image.open(path)

    return pytesseract.image_to_string(img, lang=OCR_LANG)


def _extract_material(text):
    upper = text.upper()
    for pattern, material in _MATERIAL_PATTERNS:
        if re.search(pattern, upper, re.IGNORECASE):
            return {"value": material, "confidence": "medium"}
    return None


def _extract_precision(text):
    """抽取公差数值，取最严（最小）者；命中 ≤0.2 视为精密。"""
    values = []
    for m in re.finditer(r"[±\+\-]?\s*0\.(\d{1,3})", text):
        try:
            values.append(float("0." + m.group(1)))
        except ValueError:
            continue
    if not values:
        return None
    tightest = min(v for v in values if v > 0) if any(v > 0 for v in values) else None
    if tightest is None:
        return None
    return {
        "value": round(tightest, 3),
        "is_precision": tightest <= 0.2,
        "confidence": "low",
    }


def _extract_colors(text):
    found = []
    for pattern, color in _COLOR_PATTERNS:
        if re.search(pattern, text, re.IGNORECASE):
            found.append(color)
    return found


def _parse_drawing_sync(path, kind):
    try:
        import pytesseract

        pytesseract.get_tesseract_version()
    except Exception:  # noqa: BLE001 - tesseract 未安装/不可用
        return {"parse_status": "unavailable", "error": "tesseract unavailable"}

    try:
        text = _ocr_text_from_file(path, kind)
    except Exception as exc:  # noqa: BLE001
        return {"parse_status": "error", "error": f"{type(exc).__name__}: {exc}"}

    return {
        "parse_status": "ok",
        "material": _extract_material(text),
        "precision": _extract_precision(text),
        "colors": _extract_colors(text),
        "raw_text_excerpt": (text or "").strip()[:_RAW_EXCERPT_LEN],
        "error": None,
    }


def _worker(path, kind, queue):
    try:
        queue.put(_parse_drawing_sync(path, kind))
    except Exception as exc:  # noqa: BLE001
        queue.put({"parse_status": "error", "error": f"{type(exc).__name__}: {exc}"})


def parse_drawing(path, kind, timeout=OCR_TIMEOUT_SEC):
    """OCR 解析工程图。独立进程 + 超时。

    parse_status: ok / error / timeout / unavailable。调用方据此映射错误码。
    """
    ctx = mp.get_context("fork")
    queue = ctx.Queue()
    proc = ctx.Process(target=_worker, args=(path, kind, queue), daemon=True)
    proc.start()
    proc.join(timeout)

    if proc.is_alive():
        proc.terminate()
        proc.join()
        return {"parse_status": "timeout", "error": "ocr timeout", "parsed_at": _now_iso()}

    try:
        result = queue.get_nowait()
    except Exception:  # noqa: BLE001
        result = {"parse_status": "error", "error": "no result from ocr"}

    result["parsed_at"] = _now_iso()
    return result
