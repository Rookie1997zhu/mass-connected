"""Gemini-powered plain-text translation for project timeline/issues."""

from __future__ import annotations

import hashlib
import logging

from django.conf import settings
from django.core.cache import cache

from core.document_preview import CHUNK_SIZE, chunk_text

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


def translate_text(text: str, target_lang: str) -> str:
    """Translate plain text to target_lang. Returns translated text only."""
    source = (text or "").strip()
    if not source:
        raise TranslationError("TRANSLATE_TEXT_EMPTY", "翻译文本不能为空")
    if len(source) > 8000:
        raise TranslationError("TRANSLATE_TEXT_TOO_LONG", "翻译文本过长")
    lang = (target_lang or "").strip().lower()
    if lang not in SUPPORTED_TARGET_LANGS:
        raise TranslationError("TRANSLATE_LANG_INVALID", "不支持的目标语言")

    api_key = (getattr(settings, "GEMINI_API_KEY", None) or "").strip()
    if not api_key:
        raise TranslationError("TRANSLATE_NOT_CONFIGURED", "翻译服务未配置")

    model = (getattr(settings, "GEMINI_MODEL", None) or "gemini-2.5-flash").strip()
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


def translate_project_file_text(file_id: int, source_text: str, target_lang: str) -> str:
    """Translate extracted file text with Redis cache keyed by content hash."""
    lang = (target_lang or "").strip().lower()
    content_hash = hashlib.sha256(source_text.encode("utf-8")).hexdigest()[:32]
    cache_key = f"file_translate:{file_id}:{lang}:{content_hash}"
    cached = cache.get(cache_key)
    if cached:
        return cached

    chunks = chunk_text(source_text, CHUNK_SIZE)
    translated = translate_text_chunks(chunks, lang)
    cache.set(cache_key, translated, FILE_TRANSLATE_CACHE_TTL)
    return translated
