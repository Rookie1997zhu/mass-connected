"""Celery heavy-queue task: async chat message translation via Gemini."""

from __future__ import annotations

import logging

from celery import shared_task
from django.core.cache import cache

from core.async_jobs import update_job

logger = logging.getLogger(__name__)

# 与 views._message_translate_response 保持一致的缓存 TTL
CHAT_TRANSLATE_CACHE_TTL = 3600


def _cache_key(message_id: int, lang: str) -> str:
    return f"chat:msg_tr:{message_id}:{lang}"


@shared_task(
    bind=True,
    name="chat.run_message_translate",
    queue="translate",
    max_retries=0,
    soft_time_limit=45,
    time_limit=60,
)
def run_message_translate(self, job_id: str, message_id: int, target_lang: str) -> dict:
    update_job(job_id, status="running")
    lang = str(target_lang or "").strip().lower()
    try:
        from apps.chat.models import Message
        from apps.project.translation import TranslationError, translate_text

        message = Message.objects.filter(pk=message_id).first()
        if not message:
            update_job(
                job_id,
                status="failed",
                error_code="CHAT_MESSAGE_NOT_FOUND",
                error_message="消息不存在",
            )
            return {"ok": False, "error_code": "CHAT_MESSAGE_NOT_FOUND"}

        text = (message.body or "").strip()
        if not text:
            update_job(
                job_id,
                status="failed",
                error_code="VALIDATION_ERROR",
                error_message="消息内容为空",
            )
            return {"ok": False, "error_code": "VALIDATION_ERROR"}

        try:
            translated = translate_text(text, target_lang)
        except TranslationError as exc:
            update_job(
                job_id,
                status="failed",
                error_code=exc.code,
                error_message=exc.message,
            )
            return {"ok": False, "error_code": exc.code}

        if translated:
            cache.set(_cache_key(message_id, lang), translated, CHAT_TRANSLATE_CACHE_TTL)
        update_job(
            job_id,
            status="done",
            result={"translated_text": translated},
            error_code=None,
            error_message=None,
        )
        return {"ok": True}
    except Exception as exc:  # noqa: BLE001
        logger.exception("run_message_translate failed job_id=%s", job_id)
        update_job(
            job_id,
            status="failed",
            error_code="TRANSLATE_JOB_FAILED",
            error_message=str(exc) or "翻译失败",
        )
        return {"ok": False, "error_code": "TRANSLATE_JOB_FAILED"}
