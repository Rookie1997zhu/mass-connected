"""Celery 任务：日批编排与单篇处理。"""

from __future__ import annotations

import logging

from celery import shared_task

from apps.content_pipeline.models import PipelineRun
from apps.content_pipeline.services import finalize_run, process_pipeline_item, run_daily_batch

logger = logging.getLogger(__name__)


@shared_task(name="content_pipeline.run_daily_batch", ignore_result=True)
def run_daily_batch_task():
    result = run_daily_batch(sync=False)
    logger.info("content_pipeline_run_daily_batch result=%s", result)
    return result


@shared_task(name="content_pipeline.process_video_item", ignore_result=True, soft_time_limit=300, time_limit=360)
def process_video_item(item_id: int):
    result = process_pipeline_item(item_id)
    try:
        item_run_id = result.get("run_id")
        if item_run_id:
            run = PipelineRun.objects.filter(pk=item_run_id).first()
            if run and run.status == PipelineRun.STATUS_RUNNING:
                pending = run.items.filter(status="pending").exists()
                if not pending or run.success_count >= run.target_count:
                    finalize_run(run)
    except Exception:  # noqa: BLE001
        logger.exception("finalize_after_item_failed item_id=%s", item_id)
    return result


@shared_task(name="content_pipeline.finalize_daily_run", ignore_result=True)
def finalize_daily_run(run_id: int):
    run = PipelineRun.objects.filter(pk=run_id).first()
    if not run:
        return {"ok": False, "error": "run_not_found"}
    if run.status in {
        PipelineRun.STATUS_SUCCESS,
        PipelineRun.STATUS_PARTIAL,
        PipelineRun.STATUS_FAILED,
        PipelineRun.STATUS_DISABLED,
    }:
        return {"ok": True, "status": run.status}
    finalize_run(run)
    run.refresh_from_db()
    return {"ok": True, "status": run.status, "success_count": run.success_count}
