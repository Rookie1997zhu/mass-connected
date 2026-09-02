"""Celery heavy-queue tasks: STP parse, drawing OCR, LibreOffice preview, email."""

from __future__ import annotations

import logging
import os

from celery import shared_task
from django.conf import settings
from django.core.mail import send_mail

from core.async_jobs import update_job

logger = logging.getLogger(__name__)


def _safe_unlink(path: str | None) -> None:
    if not path:
        return
    try:
        if os.path.exists(path):
            os.remove(path)
    except OSError:
        logger.warning("failed to remove tmp file path=%s", path)


@shared_task(
    bind=True,
    name="simplequote.run_stp_parse",
    queue="heavy",
    max_retries=0,
    soft_time_limit=60,
    time_limit=90,
)
def run_stp_parse(self, job_id: str, tmp_path: str) -> dict:
    update_job(job_id, status="running")
    try:
        from apps.simplequote.geometry import parse_step
        from apps.simplequote.views import injection_densities

        geometry = parse_step(tmp_path)
        parse_status = geometry.get("parse_status")
        if parse_status == "timeout":
            update_job(
                job_id,
                status="failed",
                error_code="STP_PARSE_TIMEOUT",
                error_message="文件解析超时，请改为手动填写参数",
            )
            return {"ok": False, "error_code": "STP_PARSE_TIMEOUT"}
        if parse_status != "ok":
            update_job(
                job_id,
                status="failed",
                error_code="STP_PARSE_FAILED",
                error_message="文件解析失败，请改为手动填写参数",
                result={"reason": geometry.get("error")},
            )
            return {"ok": False, "error_code": "STP_PARSE_FAILED"}

        update_job(
            job_id,
            status="done",
            result={"geometry": geometry, "densities": injection_densities()},
            error_code=None,
            error_message=None,
        )
        return {"ok": True}
    except Exception as exc:  # noqa: BLE001
        logger.exception("run_stp_parse failed job_id=%s", job_id)
        update_job(
            job_id,
            status="failed",
            error_code="PARSE_JOB_FAILED",
            error_message=str(exc) or "STP 解析失败",
        )
        return {"ok": False, "error_code": "PARSE_JOB_FAILED"}
    finally:
        _safe_unlink(tmp_path)


@shared_task(
    bind=True,
    name="simplequote.run_drawing_parse",
    queue="heavy",
    max_retries=0,
    soft_time_limit=60,
    time_limit=90,
)
def run_drawing_parse(self, job_id: str, tmp_path: str, kind: str) -> dict:
    update_job(job_id, status="running")
    try:
        from apps.simplequote.ocr import parse_drawing

        ocr = parse_drawing(tmp_path, kind)
        parse_status = ocr.get("parse_status")
        if parse_status == "unavailable":
            update_job(
                job_id,
                status="failed",
                error_code="OCR_UNAVAILABLE",
                error_message="OCR 服务不可用，请改为手动填写参数",
            )
            return {"ok": False, "error_code": "OCR_UNAVAILABLE"}
        if parse_status == "timeout":
            update_job(
                job_id,
                status="failed",
                error_code="DRAWING_PARSE_TIMEOUT",
                error_message="图纸解析超时，请改为手动填写参数",
            )
            return {"ok": False, "error_code": "DRAWING_PARSE_TIMEOUT"}
        if parse_status != "ok":
            update_job(
                job_id,
                status="failed",
                error_code="DRAWING_PARSE_FAILED",
                error_message="图纸解析失败，请改为手动填写参数",
                result={"reason": ocr.get("error")},
            )
            return {"ok": False, "error_code": "DRAWING_PARSE_FAILED"}

        update_job(
            job_id,
            status="done",
            result={"ocr": ocr},
            error_code=None,
            error_message=None,
        )
        return {"ok": True}
    except Exception as exc:  # noqa: BLE001
        logger.exception("run_drawing_parse failed job_id=%s", job_id)
        update_job(
            job_id,
            status="failed",
            error_code="PARSE_JOB_FAILED",
            error_message=str(exc) or "图纸解析失败",
        )
        return {"ok": False, "error_code": "PARSE_JOB_FAILED"}
    finally:
        _safe_unlink(tmp_path)


@shared_task(
    bind=True,
    name="simplequote.run_preview_convert",
    queue="heavy",
    max_retries=0,
    soft_time_limit=90,
    time_limit=120,
)
def run_preview_convert(
    self,
    job_id: str,
    source_path: str,
    file_id: int,
    ext: str,
    cache_ns: str = "project",
) -> dict:
    update_job(job_id, status="running")
    try:
        from core.document_preview import PreviewError, get_or_create_preview_pdf

        pdf_path = get_or_create_preview_pdf(source_path, file_id, ext, cache_ns=cache_ns)
        update_job(
            job_id,
            status="done",
            result={"pdf_path": str(pdf_path), "file_id": file_id, "cache_ns": cache_ns},
            error_code=None,
            error_message=None,
        )
        return {"ok": True}
    except PreviewError as exc:
        logger.warning(
            "run_preview_convert PreviewError job_id=%s code=%s", job_id, exc.code
        )
        update_job(
            job_id,
            status="failed",
            error_code=exc.code,
            error_message=exc.message,
        )
        return {"ok": False, "error_code": exc.code}
    except Exception as exc:  # noqa: BLE001
        logger.exception("run_preview_convert failed job_id=%s", job_id)
        update_job(
            job_id,
            status="failed",
            error_code="PREVIEW_CONVERT_FAILED",
            error_message=str(exc) or "文档转换失败，请下载原件查看",
        )
        return {"ok": False, "error_code": "PREVIEW_CONVERT_FAILED"}


@shared_task(
    bind=True,
    name="simplequote.send_notification_email",
    queue="heavy",
    max_retries=0,
    soft_time_limit=30,
    time_limit=60,
)
def send_notification_email(self, subject: str, message: str, recipient: str) -> dict:
    try:
        send_mail(
            subject=subject,
            message=message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[recipient],
            fail_silently=False,
        )
        return {"ok": True}
    except Exception:  # noqa: BLE001
        logger.exception("send_notification_email failed recipient=%s", recipient)
        return {"ok": False}


@shared_task(
    bind=True,
    name="accounts.send_verification_email",
    queue="heavy",
    max_retries=0,
    soft_time_limit=30,
    time_limit=60,
)
def send_verification_email(self, user_id: int, lang: str = "ko") -> dict:
    try:
        from apps.accounts.models import User
        from apps.accounts.services.email_verification import get_email_content

        user = User.objects.get(pk=user_id)
        subject, message = get_email_content(user, lang)
        send_mail(
            subject=subject,
            message=message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[user.email],
            fail_silently=False,
        )
        return {"ok": True}
    except Exception:  # noqa: BLE001
        logger.exception("send_verification_email failed user_id=%s", user_id)
        return {"ok": False}
