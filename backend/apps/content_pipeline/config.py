"""内容流水线配置读取。"""

from __future__ import annotations

from django.conf import settings


def pipeline_enabled() -> bool:
    return bool(getattr(settings, "CONTENT_PIPELINE_ENABLED", False))


def daily_count() -> int:
    return max(1, int(getattr(settings, "CONTENT_PIPELINE_DAILY_COUNT", 10) or 10))


def keywords() -> list[str]:
    raw = getattr(settings, "CONTENT_PIPELINE_KEYWORDS", "") or ""
    return [part.strip() for part in raw.split(",") if part.strip()]


def languages() -> list[str]:
    raw = getattr(settings, "CONTENT_PIPELINE_LANGUAGES", "zh,ko") or "zh,ko"
    allowed = {"zh", "ko"}
    parsed = [part.strip().lower() for part in raw.split(",") if part.strip()]
    result = [lang for lang in parsed if lang in allowed]
    return result or ["zh", "ko"]


def language_for_index(index: int) -> str:
    langs = languages()
    return langs[index % len(langs)]


def author_email() -> str:
    return (getattr(settings, "CONTENT_PIPELINE_AUTHOR_EMAIL", "") or "").strip()


def youtube_api_key() -> str:
    return (getattr(settings, "YOUTUBE_API_KEY", "") or "").strip()


def gemini_api_key() -> str:
    return (getattr(settings, "GEMINI_API_KEY", "") or "").strip()


def gemini_model() -> str:
    return (getattr(settings, "GEMINI_MODEL", None) or "gemini-2.5-flash").strip()


def pipeline_timezone() -> str:
    return (getattr(settings, "CONTENT_PIPELINE_TIMEZONE", None) or "Asia/Shanghai").strip()


def candidate_pool_size(target: int) -> int:
    return max(target * 3, target)
