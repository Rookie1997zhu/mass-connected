"""Celery tasks for print3d slicing."""
from __future__ import annotations

import logging
import os
import tempfile

from celery import shared_task
from django.core.files import File
from django.utils import timezone

# Register heavy-queue tasks for Celery autodiscovery (tasks.py only).
from apps.simplequote import heavy_tasks as _heavy_tasks  # noqa: F401
from apps.simplequote.models import Print3dSliceJob
from apps.simplequote.print3d_config import slice_params_from_snapshot
from apps.simplequote.slicer import (
    SlicerError,
    convert_step_to_stl_ocp,
    convert_stl_to_gcode,
    extract_filament_usage,
)

logger = logging.getLogger(__name__)

PREVIEW_MAX_BYTES = 8 * 1024 * 1024


def _clear_source_file(job: Print3dSliceJob) -> None:
    if not job.source_file:
        return
    name = job.source_file.name
    try:
        job.source_file.delete(save=False)
    except Exception:  # noqa: BLE001
        logger.warning("print3d clear source failed job=%s name=%s", job.id, name)
    job.source_file = None
    job.source_cleared_at = timezone.now()
    job.save(update_fields=["source_file", "source_cleared_at", "updated_at"])


def _save_preview_stl(job: Print3dSliceJob, stl_path: str) -> None:
    """将预览 STL 写入 FileField，不再写入 preview_mesh JSON。"""
    try:
        size = os.path.getsize(stl_path)
        if size <= 0 or size > PREVIEW_MAX_BYTES:
            return
        filename = f"job_{job.id}_preview.stl"
        with open(stl_path, "rb") as fh:
            job.preview_file.save(filename, File(fh), save=False)
        job.preview_mesh = None
        job.save(update_fields=["preview_file", "preview_mesh", "updated_at"])
    except OSError:
        logger.warning("print3d preview save failed job=%s", job.id)


@shared_task(bind=True, name="simplequote.run_print3d_slice", max_retries=0, soft_time_limit=360, time_limit=420)
def run_print3d_slice(self, job_id: int) -> dict:
    try:
        job = Print3dSliceJob.objects.get(pk=job_id)
    except Print3dSliceJob.DoesNotExist:
        logger.error("print3d slice job missing id=%s", job_id)
        return {"ok": False, "error": "missing"}

    if job.status in (Print3dSliceJob.STATUS_DONE, Print3dSliceJob.STATUS_FAILED):
        return {"ok": job.status == Print3dSliceJob.STATUS_DONE, "status": job.status}

    if not job.source_file:
        job.mark_failed("PRINT3D_FILE_INVALID", "切片源文件不存在")
        return {"ok": False}

    snapshot = job.config_snapshot or {}
    timeout = int(snapshot.get("slicer_timeout_seconds") or 300)
    slice_params = slice_params_from_snapshot(snapshot)
    tmp_dir = tempfile.mkdtemp(prefix=f"print3d_{job_id}_")
    local_source = None
    stl_path = None
    gcode_path = os.path.join(tmp_dir, "out.gcode")

    try:
        ext = (job.file_ext or "").lower()
        with job.source_file.open("rb") as src:
            local_source = os.path.join(tmp_dir, f"source{ext or '.bin'}")
            with open(local_source, "wb") as dst:
                while True:
                    chunk = src.read(1024 * 1024)
                    if not chunk:
                        break
                    dst.write(chunk)

        if ext in (".stp", ".step"):
            job.status = Print3dSliceJob.STATUS_CONVERTING
            job.save(update_fields=["status", "updated_at"])
            stl_path = os.path.join(tmp_dir, "model.stl")
            convert_step_to_stl_ocp(local_source, stl_path)
            _save_preview_stl(job, stl_path)
        else:
            stl_path = local_source
            _save_preview_stl(job, stl_path)

        job.status = Print3dSliceJob.STATUS_SLICING
        job.save(update_fields=["status", "updated_at"])

        convert_stl_to_gcode(
            stl_path,
            gcode_path,
            slice_params,
            timeout=timeout,
        )
        usage = extract_filament_usage(
            gcode_path,
            density_g_cm3=slice_params.get("filament_density"),
        )
        job.result = {
            "filament_weight_g": usage["filament_weight_g"],
            "filament_length_mm": usage.get("filament_length_mm", 0),
            "filament_volume_cm3": usage.get("filament_volume_cm3", 0),
            "print_hours": usage["estimated_time_hours"],
            "estimated_time_seconds": usage["estimated_time_seconds"],
            "layer_height": slice_params.get("layer_height"),
            "infill_density": slice_params.get("infill_density"),
            "support": bool(slice_params.get("support")),
        }
        job.status = Print3dSliceJob.STATUS_DONE
        job.error_code = ""
        job.error_message = ""
        job.save(
            update_fields=[
                "result",
                "status",
                "error_code",
                "error_message",
                "updated_at",
            ]
        )
        _clear_source_file(job)
        return {"ok": True, "job_id": job_id, "result": job.result}
    except SlicerError as exc:
        logger.warning("print3d slice failed job=%s code=%s msg=%s", job_id, exc.code, exc.message)
        job.mark_failed(exc.code, exc.message)
        _clear_source_file(job)
        return {"ok": False, "code": exc.code}
    except Exception as exc:  # noqa: BLE001
        logger.exception("print3d slice unexpected job=%s", job_id)
        job.mark_failed("PRINT3D_SLICE_FAILED", f"切片异常: {type(exc).__name__}")
        _clear_source_file(job)
        return {"ok": False, "code": "PRINT3D_SLICE_FAILED"}
    finally:
        for path in (local_source, gcode_path if gcode_path != local_source else None):
            if path and os.path.exists(path) and path != stl_path:
                try:
                    os.remove(path)
                except OSError:
                    pass
        if stl_path and stl_path != local_source and os.path.exists(stl_path):
            try:
                os.remove(stl_path)
            except OSError:
                pass
        try:
            os.rmdir(tmp_dir)
        except OSError:
            for name in os.listdir(tmp_dir) if os.path.isdir(tmp_dir) else []:
                try:
                    os.remove(os.path.join(tmp_dir, name))
                except OSError:
                    pass
            try:
                os.rmdir(tmp_dir)
            except OSError:
                pass


@shared_task(name="simplequote.cleanup_expired_print3d_jobs")
def cleanup_expired_print3d_jobs() -> int:
    now = timezone.now()
    count = 0
    for job in Print3dSliceJob.objects.filter(expires_at__lt=now)[:200]:
        _clear_source_file(job)
        if job.preview_file:
            try:
                job.preview_file.delete(save=False)
            except Exception:  # noqa: BLE001
                pass
            job.preview_file = None
            job.preview_mesh = None
            job.save(update_fields=["preview_file", "preview_mesh", "updated_at"])
        count += 1
    return count
