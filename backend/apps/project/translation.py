"""Gemini-powered plain-text and multimodal translation for project files."""

from __future__ import annotations

import hashlib
import logging

from django.conf import settings
from django.core.cache import cache

from core.document_preview import (
    CHUNK_SIZE,
    MAX_EXTRACT_CHARS,
    MAX_VISION_PAGES,
    PDF_EXT,
    chunk_text,
    extract_text_from_file,
    file_ext,
    inspect_pdf_text_layer,
    render_pdf_pages_as_images,
)

logger = logging.getLogger(__name__)

FILE_TRANSLATE_CACHE_TTL = 7 * 24 * 3600

SUPPORTED_TARGET_LANGS = frozenset({"zh", "ko", "en", "ja"})

_LANG_NAMES = {
    "zh": "Simplified Chinese",
    "ko": "Korean",
    "en": "English",
    "ja": "Japanese",
}


class TranslationError(Exception):
    def __init__(self, code: str, message: str):
        self.code = code
        self.message = message
        super().__init__(message)


def _normalize_target_lang(target_lang: str) -> str:
    lang = (target_lang or "").strip().lower()
    if lang not in SUPPORTED_TARGET_LANGS:
        raise TranslationError("TRANSLATE_LANG_INVALID", "不支持的目标语言")
    return lang


def _require_api_key() -> str:
    api_key = (getattr(settings, "GEMINI_API_KEY", None) or "").strip()
    if not api_key:
        raise TranslationError("TRANSLATE_NOT_CONFIGURED", "翻译服务未配置")
    return api_key


def _gemini_model() -> str:
    return (getattr(settings, "GEMINI_MODEL", None) or "gemini-2.5-flash").strip()


def translate_text(text: str, target_lang: str) -> str:
    """Translate plain text to target_lang. Returns translated text only."""
    source = (text or "").strip()
    if not source:
        raise TranslationError("TRANSLATE_TEXT_EMPTY", "翻译文本不能为空")
    if len(source) > 8000:
        raise TranslationError("TRANSLATE_TEXT_TOO_LONG", "翻译文本过长")
    lang = _normalize_target_lang(target_lang)
    api_key = _require_api_key()
    model = _gemini_model()
    lang_name = _LANG_NAMES[lang]
    system_instruction = (
        "You are a professional translator for a manufacturing project platform. "
        f"Translate the user's text into {lang_name}. "
        "Return only the translation, with no quotes, labels, or explanations. "
        "Preserve numbers, product codes, and proper nouns when appropriate."
    )

    try:
        from google import genai
        from google.genai import types
    except ImportError as exc:
        logger.exception("google-genai is not installed")
        raise TranslationError("TRANSLATE_UNAVAILABLE", "翻译服务不可用") from exc

    try:
        client = genai.Client(
            api_key=api_key,
            http_options=types.HttpOptions(timeout=30_000),
        )
        response = client.models.generate_content(
            model=model,
            contents=source,
            config=types.GenerateContentConfig(
                system_instruction=system_instruction,
                temperature=0.2,
            ),
        )
    except Exception as exc:
        logger.warning("Gemini translate failed: %s", type(exc).__name__)
        raise TranslationError("TRANSLATE_FAILED", "翻译失败，请稍后重试") from exc

    translated = (getattr(response, "text", None) or "").strip()
    if not translated:
        raise TranslationError("TRANSLATE_FAILED", "翻译失败，请稍后重试")
    return translated


def translate_text_chunks(chunks: list[str], target_lang: str) -> str:
    """Translate multiple text chunks sequentially and join with blank lines."""
    if not chunks:
        raise TranslationError("TRANSLATE_TEXT_EMPTY", "翻译文本不能为空")
    parts: list[str] = []
    for chunk in chunks:
        parts.append(translate_text(chunk, target_lang))
    return "\n\n".join(parts)


def translate_file_text(
    cache_ns: str,
    file_id: int,
    source_text: str,
    target_lang: str,
) -> str:
    """Translate extracted file text with Redis cache keyed by content hash."""
    lang = _normalize_target_lang(target_lang)
    content_hash = hashlib.sha256(source_text.encode("utf-8")).hexdigest()[:32]
    cache_key = f"file_translate:{cache_ns}:{file_id}:{lang}:{content_hash}"
    cached = cache.get(cache_key)
    if cached:
        return cached

    chunks = chunk_text(source_text, CHUNK_SIZE)
    translated = translate_text_chunks(chunks, lang)
    cache.set(cache_key, translated, FILE_TRANSLATE_CACHE_TTL)
    return translated


def translate_project_file_text(file_id: int, source_text: str, target_lang: str) -> str:
    return translate_file_text("project", file_id, source_text, target_lang)


def _file_fingerprint(source_path: str) -> str:
    import os

    stat = os.stat(source_path)
    raw = f"{stat.st_size}:{int(stat.st_mtime_ns)}"
    return hashlib.sha256(raw.encode()).hexdigest()[:32]


def translate_pdf_pages_with_vision(
    file_id: int,
    source_path: str,
    target_lang: str,
    max_pages: int = MAX_VISION_PAGES,
    cache_ns: str = "project",
) -> dict:
    """Translate visible text on image-only PDF pages via Gemini multimodal."""
    lang = _normalize_target_lang(target_lang)
    api_key = _require_api_key()
    model = _gemini_model()
    fingerprint = _file_fingerprint(source_path)
    # v2: 缓存结构新增 source_text（原文/译文对照）
    cache_key = (
        f"file_vision_translate:v2:{cache_ns}:{file_id}:{lang}:{model}:{max_pages}:{fingerprint}"
    )
    cached = cache.get(cache_key)
    if cached:
        return cached

    rendered = render_pdf_pages_as_images(source_path, max_pages=max_pages)
    images = rendered.get("images") or []
    if not images:
        raise TranslationError("PREVIEW_EXTRACT_EMPTY", "未能从文件中提取文本")

    lang_name = _LANG_NAMES[lang]
    system_instruction = (
        "You are a professional translator for a manufacturing project platform. "
        "The user provides scanned or drawing PDF page images. "
        "Detect all visible text in the images, then return a JSON object with "
        "two string fields: 'source_text' containing the detected original text, "
        f"and 'translated_text' containing its translation into {lang_name}. "
        "Keep the same line order in both fields so lines correspond. "
        "Preserve numbers, dimensions, product codes, and proper nouns. "
        "Keep page order with a short page marker like '[Page 1]' in both fields "
        "when multiple pages are provided. "
        "Do not describe drawings, colors, or layout. "
        "If no readable text is present, set both fields to empty strings."
    )

    try:
        from google import genai
        from google.genai import types
    except ImportError as exc:
        logger.exception("google-genai is not installed")
        raise TranslationError("TRANSLATE_UNAVAILABLE", "翻译服务不可用") from exc

    contents: list = [
        (
            "Extract and translate all visible text from these PDF page images. "
            f"There are {len(images)} page image(s)."
        )
    ]
    for item in images:
        contents.append(
            types.Part.from_bytes(data=item["data"], mime_type=item["mime_type"])
        )

    response_schema = {
        "type": "object",
        "properties": {
            "source_text": {"type": "string"},
            "translated_text": {"type": "string"},
        },
        "required": ["source_text", "translated_text"],
    }

    try:
        client = genai.Client(
            api_key=api_key,
            http_options=types.HttpOptions(timeout=90_000),
        )
        response = client.models.generate_content(
            model=model,
            contents=contents,
            config=types.GenerateContentConfig(
                system_instruction=system_instruction,
                temperature=0.2,
                response_mime_type="application/json",
                response_schema=response_schema,
            ),
        )
    except Exception as exc:
        logger.warning("Gemini vision translate failed: %s", type(exc).__name__)
        raise TranslationError("TRANSLATE_FAILED", "翻译失败，请稍后重试") from exc

    raw = (getattr(response, "text", None) or "").strip()
    source_text, translated = _parse_vision_payload(raw)
    if not translated:
        raise TranslationError("PREVIEW_EXTRACT_EMPTY", "未能从文件中提取文本")

    result = {
        "translated_text": translated,
        "source_text": source_text,
        "truncated": bool(rendered.get("truncated")),
        "extraction_method": "gemini_vision",
        "page_count": int(rendered.get("page_count") or 0),
        "processed_pages": int(rendered.get("processed_pages") or 0),
        "char_count": len(translated),
    }
    cache.set(cache_key, result, FILE_TRANSLATE_CACHE_TTL)
    return result


def _parse_vision_payload(raw: str) -> tuple[str, str]:
    """Parse Gemini JSON payload; fall back to treating raw text as translation."""
    import json

    if not raw:
        return "", ""
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError:
        return "", raw
    if not isinstance(payload, dict):
        return "", raw
    source = (payload.get("source_text") or "").strip()
    translated = (payload.get("translated_text") or "").strip()
    return source, translated


def translate_pdf_file(
    cache_ns: str,
    file_id: int,
    source_path: str,
    target_lang: str,
) -> dict:
    """Route PDF translation: text layer → text translate; else Gemini vision."""
    inspected = inspect_pdf_text_layer(source_path)
    page_count = int(inspected.get("page_count") or 0)
    if inspected.get("has_text_layer"):
        text = (inspected.get("text") or "").strip()
        if not text:
            raise TranslationError("PREVIEW_EXTRACT_EMPTY", "未能从文件中提取文本")
        truncated = False
        if len(text) > MAX_EXTRACT_CHARS:
            text = text[:MAX_EXTRACT_CHARS]
            truncated = True
        translated = translate_file_text(cache_ns, file_id, text, target_lang)
        return {
            "translated_text": translated,
            "source_text": text,
            "truncated": truncated,
            "extraction_method": "pdf_text",
            "page_count": page_count,
            "processed_pages": page_count,
            "char_count": len(translated),
        }

    return translate_pdf_pages_with_vision(
        file_id,
        source_path,
        target_lang,
        max_pages=MAX_VISION_PAGES,
        cache_ns=cache_ns,
    )


def translate_project_pdf_file(file_id: int, source_path: str, target_lang: str) -> dict:
    return translate_pdf_file("project", file_id, source_path, target_lang)


def translate_file_by_path(
    cache_ns: str,
    file_id: int,
    source_path: str,
    ext: str,
    target_lang: str,
) -> dict:
    """Translate any supported office/PDF file by path (resource-agnostic)."""
    ext = (ext or file_ext(source_path)).lower()
    if ext == PDF_EXT:
        return translate_pdf_file(cache_ns, file_id, source_path, target_lang)

    extracted = extract_text_from_file(source_path, ext)
    text = extracted.get("text") or ""
    translated = translate_file_text(cache_ns, file_id, text, target_lang)
    return {
        "translated_text": translated,
        "source_text": text,
        "truncated": extracted.get("truncated", False),
        "extraction_method": extracted.get("extraction_method", ""),
        "page_count": extracted.get("page_count", 0),
        "processed_pages": extracted.get("page_count", 0),
        "char_count": len(translated),
    }
