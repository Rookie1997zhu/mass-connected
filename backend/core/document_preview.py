"""Office/PDF document preview conversion and text extraction."""

from __future__ import annotations

import csv
import hashlib
import logging
import os
import shutil
import subprocess
import tempfile
from pathlib import Path

from django.conf import settings

logger = logging.getLogger(__name__)

CONVERT_TO_PDF_EXTS = frozenset({"xlsx", "xls", "docx", "doc", "csv"})
IMAGE_EXTS = frozenset({"jpg", "jpeg", "png", "gif", "webp"})
PDF_EXT = "pdf"

CONVERT_TIMEOUT_SEC = 60
MAX_EXTRACT_CHARS = 50_000
MAX_OCR_PAGES = 20
OCR_LANG = "eng+kor+chi_sim"
OCR_DPI = 300
# psm 11: sparse text — 适配图纸/设计稿上零散分布的标注文字
OCR_CONFIG = "--psm 11"

# Gemini vision fallback for image-only PDFs
MAX_VISION_PAGES = 5
VISION_DPI = 150
VISION_MAX_SIDE = 1600
VISION_JPEG_QUALITY = 85

CHUNK_SIZE = 6000


class PreviewError(Exception):
    def __init__(self, code: str, message: str):
        self.code = code
        self.message = message
        super().__init__(message)


def file_ext(name: str) -> str:
    if not name or "." not in name:
        return ""
    return name.rsplit(".", 1)[-1].lower()


def preview_mode_for_ext(ext: str) -> str:
    ext = (ext or "").lower()
    if ext in IMAGE_EXTS:
        return "image"
    if ext == PDF_EXT or ext in CONVERT_TO_PDF_EXTS:
        return "pdf_convert" if ext in CONVERT_TO_PDF_EXTS else "direct"
    return "none"


def _source_fingerprint(source_path: str) -> str:
    stat = os.stat(source_path)
    raw = f"{stat.st_size}:{int(stat.st_mtime_ns)}"
    return hashlib.sha256(raw.encode()).hexdigest()[:16]


def preview_cache_dir(file_id: int, cache_ns: str = "project") -> Path:
    base = Path(settings.MEDIA_ROOT) / "preview_cache" / cache_ns / str(file_id)
    base.mkdir(parents=True, exist_ok=True)
    return base


def cleanup_preview_cache(file_id: int, cache_ns: str = "project") -> None:
    cache_dir = Path(settings.MEDIA_ROOT) / "preview_cache" / cache_ns / str(file_id)
    if cache_dir.is_dir():
        shutil.rmtree(cache_dir, ignore_errors=True)


def _find_libreoffice() -> str:
    for cmd in ("libreoffice", "soffice"):
        path = shutil.which(cmd)
        if path:
            return path
    raise PreviewError("PREVIEW_CONVERT_UNAVAILABLE", "文档预览服务不可用")


def convert_to_pdf(source_path: str, out_dir: str) -> Path:
    """Convert office document to PDF via LibreOffice headless."""
    lo = _find_libreoffice()
    os.makedirs(out_dir, exist_ok=True)
    env = os.environ.copy()
    env.setdefault("HOME", "/tmp")
    try:
        proc = subprocess.run(
            [
                lo,
                "--headless",
                "--norestore",
                "--convert-to",
                "pdf",
                "--outdir",
                out_dir,
                source_path,
            ],
            capture_output=True,
            timeout=CONVERT_TIMEOUT_SEC,
            env=env,
            check=False,
        )
    except subprocess.TimeoutExpired as exc:
        raise PreviewError("PREVIEW_CONVERT_TIMEOUT", "文档转换超时，请下载原件查看") from exc

    if proc.returncode != 0:
        stderr = (proc.stderr or b"").decode("utf-8", errors="replace")[:500]
        logger.warning("LibreOffice convert failed rc=%s stderr=%s", proc.returncode, stderr)
        raise PreviewError("PREVIEW_CONVERT_FAILED", "文档转换失败，请下载原件查看")

    stem = Path(source_path).stem
    out_path = Path(out_dir) / f"{stem}.pdf"
    if not out_path.is_file():
        pdfs = list(Path(out_dir).glob("*.pdf"))
        if not pdfs:
            raise PreviewError("PREVIEW_CONVERT_FAILED", "文档转换失败，请下载原件查看")
        out_path = pdfs[0]
    return out_path


def peek_cached_preview_pdf(
    source_path: str,
    file_id: int,
    ext: str,
    cache_ns: str = "project",
) -> Path | None:
    """Return cached/direct PDF path without converting; None on cache miss."""
    ext = (ext or "").lower()
    if ext == PDF_EXT:
        path = Path(source_path)
        return path if path.is_file() else None
    if ext not in CONVERT_TO_PDF_EXTS:
        return None
    if not os.path.isfile(source_path):
        return None
    fingerprint = _source_fingerprint(source_path)
    cached = preview_cache_dir(file_id, cache_ns=cache_ns) / f"{fingerprint}.pdf"
    return cached if cached.is_file() else None


def get_or_create_preview_pdf(
    source_path: str,
    file_id: int,
    ext: str,
    cache_ns: str = "project",
) -> Path:
    """Return path to PDF suitable for inline preview (original or converted)."""
    ext = (ext or "").lower()
    if ext == PDF_EXT:
        return Path(source_path)
    if ext not in CONVERT_TO_PDF_EXTS:
        raise PreviewError("PREVIEW_PDF_NOT_APPLICABLE", "该文件类型不支持 PDF 预览")

    fingerprint = _source_fingerprint(source_path)
    cache_dir = preview_cache_dir(file_id, cache_ns=cache_ns)
    cached = cache_dir / f"{fingerprint}.pdf"
    if cached.is_file():
        return cached

    with tempfile.TemporaryDirectory() as tmp:
        converted = convert_to_pdf(source_path, tmp)
        shutil.copy2(converted, cached)
    return cached


def _truncate_text(text: str) -> tuple[str, bool]:
    if len(text) <= MAX_EXTRACT_CHARS:
        return text, False
    return text[:MAX_EXTRACT_CHARS], True


def _extract_docx(path: str) -> tuple[str, str]:
    from docx import Document

    doc = Document(path)
    parts: list[str] = []
    for para in doc.paragraphs:
        line = (para.text or "").strip()
        if line:
            parts.append(line)
    for table in doc.tables:
        for row in table.rows:
            cells = [((cell.text or "").strip()) for cell in row.cells]
            if any(cells):
                parts.append("\t".join(cells))
    return "\n".join(parts), "docx_parser"


def _extract_xlsx(path: str, ext: str) -> tuple[str, str]:
    if ext == "xls":
        # openpyxl does not read legacy xls; convert via LO then pymupdf text
        with tempfile.TemporaryDirectory() as tmp:
            pdf_path = convert_to_pdf(path, tmp)
            return _extract_pdf(str(pdf_path))
    from openpyxl import load_workbook

    wb = load_workbook(path, read_only=True, data_only=True)
    parts: list[str] = []
    for sheet_name in wb.sheetnames:
        ws = wb[sheet_name]
        parts.append(f"## {sheet_name}")
        for row in ws.iter_rows(values_only=True):
            cells = [str(c).strip() if c is not None else "" for c in row]
            if any(cells):
                parts.append("\t".join(cells))
    wb.close()
    return "\n".join(parts), "xlsx_parser"


def _extract_csv(path: str) -> tuple[str, str]:
    with open(path, newline="", encoding="utf-8", errors="replace") as fh:
        reader = csv.reader(fh)
        lines = ["\t".join(row) for row in reader if any(cell.strip() for cell in row)]
    return "\n".join(lines), "csv_text"


def inspect_pdf_text_layer(path: str) -> dict:
    """Inspect whether a PDF has an extractable text layer."""
    import fitz  # PyMuPDF

    doc = fitz.open(path)
    try:
        page_count = doc.page_count
        parts: list[str] = []
        for i in range(page_count):
            page = doc.load_page(i)
            text = (page.get_text() or "").strip()
            if text:
                parts.append(text)
        combined = "\n\n".join(parts).strip()
        return {
            "has_text_layer": bool(combined),
            "page_count": page_count,
            "text": combined,
        }
    finally:
        doc.close()


def render_pdf_pages_as_images(
    path: str,
    max_pages: int = MAX_VISION_PAGES,
    dpi: int = VISION_DPI,
) -> dict:
    """Render the first N PDF pages as compressed JPEG bytes for Gemini vision."""
    import fitz  # PyMuPDF
    from io import BytesIO

    from PIL import Image

    doc = fitz.open(path)
    try:
        page_count = doc.page_count
        process_count = min(page_count, max_pages)
        images: list[dict] = []
        for i in range(process_count):
            page = doc.load_page(i)
            pix = page.get_pixmap(dpi=dpi)
            mode = "RGB" if pix.n < 4 else "RGBA"
            img = Image.frombytes(mode, (pix.width, pix.height), pix.samples)
            if img.mode != "RGB":
                img = img.convert("RGB")
            max_side = max(img.size)
            if max_side > VISION_MAX_SIDE:
                scale = VISION_MAX_SIDE / max_side
                img = img.resize(
                    (max(1, int(img.width * scale)), max(1, int(img.height * scale))),
                    Image.Resampling.LANCZOS,
                )
            buf = BytesIO()
            img.save(buf, format="JPEG", quality=VISION_JPEG_QUALITY, optimize=True)
            images.append(
                {
                    "page_index": i,
                    "mime_type": "image/jpeg",
                    "data": buf.getvalue(),
                }
            )
            img.close()
            buf.close()
        return {
            "page_count": page_count,
            "processed_pages": process_count,
            "truncated": page_count > process_count,
            "images": images,
        }
    finally:
        doc.close()


def _extract_pdf(path: str) -> tuple[str, str]:
    inspected = inspect_pdf_text_layer(path)
    if inspected["has_text_layer"]:
        return inspected["text"], "pdf_text"
    return _extract_pdf_ocr(path, min(inspected["page_count"], MAX_OCR_PAGES))


def _extract_pdf_ocr(path: str, max_pages: int) -> tuple[str, str]:
    import fitz  # PyMuPDF
    import pytesseract
    from PIL import Image

    doc = fitz.open(path)
    parts: list[str] = []
    for i in range(min(doc.page_count, max_pages)):
        page = doc.load_page(i)
        pix = page.get_pixmap(dpi=OCR_DPI)
        mode = "RGB" if pix.n < 4 else "RGBA"
        img = Image.frombytes(mode, (pix.width, pix.height), pix.samples)
        parts.append(pytesseract.image_to_string(img, lang=OCR_LANG, config=OCR_CONFIG))
    doc.close()
    return "\n\n".join(parts), "pdf_ocr"


def extract_text_from_file(source_path: str, ext: str) -> dict:
    """Extract plain text from a project file for AI translation."""
    ext = (ext or file_ext(source_path)).lower()
    if not os.path.isfile(source_path):
        raise PreviewError("PROJECT_FILE_MISSING", "文件不存在")

    if ext == "docx":
        text, method = _extract_docx(source_path)
    elif ext in {"xlsx", "xls"}:
        text, method = _extract_xlsx(source_path, ext)
    elif ext == "csv":
        text, method = _extract_csv(source_path)
    elif ext == PDF_EXT:
        text, method = _extract_pdf(source_path)
    elif ext == "doc":
        with tempfile.TemporaryDirectory() as tmp:
            pdf_path = convert_to_pdf(source_path, tmp)
            text, method = _extract_pdf(str(pdf_path))
            method = "doc_converted_pdf"
    elif ext in CONVERT_TO_PDF_EXTS:
        with tempfile.TemporaryDirectory() as tmp:
            pdf_path = convert_to_pdf(source_path, tmp)
            text, method = _extract_pdf(str(pdf_path))
    else:
        raise PreviewError("PREVIEW_EXTRACT_UNSUPPORTED", "该文件类型不支持翻译")

    text = (text or "").strip()
    if not text:
        raise PreviewError("PREVIEW_EXTRACT_EMPTY", "未能从文件中提取文本")

    truncated = False
    if len(text) > MAX_EXTRACT_CHARS:
        text, truncated = _truncate_text(text)

    page_count = 0
    if ext == PDF_EXT:
        try:
            import fitz

            doc = fitz.open(source_path)
            page_count = doc.page_count
            doc.close()
        except Exception:  # noqa: BLE001
            page_count = 0

    return {
        "text": text,
        "truncated": truncated,
        "page_count": page_count,
        "extraction_method": method,
        "char_count": len(text),
    }


def chunk_text(text: str, chunk_size: int = CHUNK_SIZE) -> list[str]:
    text = (text or "").strip()
    if not text:
        return []
    if len(text) <= chunk_size:
        return [text]
    chunks: list[str] = []
    start = 0
    while start < len(text):
        end = min(start + chunk_size, len(text))
        if end < len(text):
            split_at = text.rfind("\n", start, end)
            if split_at > start + chunk_size // 2:
                end = split_at + 1
        chunks.append(text[start:end].strip())
        start = end
    return [c for c in chunks if c]
