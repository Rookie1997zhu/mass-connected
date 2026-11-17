"""日批编排与单篇处理。"""

from __future__ import annotations

import logging
from datetime import datetime
from zoneinfo import ZoneInfo

from django.db import transaction
from django.db.models import F
from django.utils import timezone

from apps.content_pipeline.config import (
    candidate_pool_size,
    daily_count,
    keywords,
    language_for_index,
    pipeline_enabled,
    pipeline_timezone,
)
from apps.content_pipeline.exceptions import PipelineError, PipelineSkip
from apps.content_pipeline.images import build_cover_image, inject_inline_images
from apps.content_pipeline.models import PipelineItem, PipelineRun, UsedYouTubeVideo
from apps.content_pipeline.publish import publish_blog_post, resolve_author
from apps.content_pipeline.rewrite import rewrite_transcript_to_article
from apps.content_pipeline.transcripts import fetch_transcript_text
from apps.content_pipeline.youtube_search import collect_candidates

logger = logging.getLogger(__name__)


def today_in_pipeline_tz():
    tz = ZoneInfo(pipeline_timezone())
    return datetime.now(tz).date()


def finalize_run(run: PipelineRun) -> PipelineRun:
    run.refresh_from_db()
    if run.status == PipelineRun.STATUS_DISABLED:
        return run
    if run.success_count >= run.target_count:
        run.status = PipelineRun.STATUS_SUCCESS
    elif run.success_count > 0:
        run.status = PipelineRun.STATUS_PARTIAL
    else:
        run.status = PipelineRun.STATUS_FAILED
    run.save(update_fields=["status", "updated_at"])
    return run


def process_pipeline_item(item_id: int) -> dict:
    """处理单条 PipelineItem：字幕→润色→配图→发布。"""
    item = PipelineItem.objects.select_related("run").get(pk=item_id)
    run = item.run
    log_extra = {
        "run_id": run.id,
        "video_id": item.youtube_video_id,
        "keyword": item.keyword,
        "language": item.language,
    }

    if UsedYouTubeVideo.objects.filter(video_id=item.youtube_video_id).exists():
        item.status = PipelineItem.STATUS_SKIPPED
        item.error_message = "video_id 已使用"
        item.save(update_fields=["status", "error_message", "updated_at"])
        logger.info("pipeline_item_skipped_dup %s", log_extra)
        return {"ok": False, "status": "skipped", **log_extra}

    # 目标已满则跳过
    run.refresh_from_db()
    if run.success_count >= run.target_count:
        item.status = PipelineItem.STATUS_SKIPPED
        item.error_message = "本轮目标已达成"
        item.save(update_fields=["status", "error_message", "updated_at"])
        return {"ok": False, "status": "skipped", **log_extra}

    try:
        transcript = fetch_transcript_text(item.youtube_video_id)
        article = rewrite_transcript_to_article(
            transcript=transcript,
            language=item.language or "zh",
            source_title=item.title,
            keyword=item.keyword,
        )
        cover = ""
        try:
            cover = build_cover_image(item.youtube_video_id)
        except Exception:  # noqa: BLE001
            logger.exception("cover_image_failed video_id=%s", item.youtube_video_id)

        content_html = inject_inline_images(
            article["content_html"],
            item.youtube_video_id,
            int(article.get("image_slots") or 0),
        )
        author = resolve_author()
        with transaction.atomic():
            # 再次检查去重
            if UsedYouTubeVideo.objects.filter(video_id=item.youtube_video_id).exists():
                raise PipelineSkip("VIDEO_USED", "video_id 已使用")
            post = publish_blog_post(
                title=article["title"],
                summary=article["summary"],
                content_html=content_html,
                language=article["language"],
                tags=article.get("tags") or [],
                cover_image=cover,
                author=author,
            )
            UsedYouTubeVideo.objects.create(
                video_id=item.youtube_video_id,
                keyword=item.keyword,
                language=article["language"],
                blog_post=post,
            )
            item.status = PipelineItem.STATUS_SUCCESS
            item.title = post.title
            item.blog_post = post
            item.error_message = ""
            item.save(update_fields=["status", "title", "blog_post", "error_message", "updated_at"])
            PipelineRun.objects.filter(pk=run.pk).update(
                success_count=F("success_count") + 1,
                updated_at=timezone.now(),
            )
        logger.info("pipeline_item_success %s post_id=%s", log_extra, post.id)
        return {"ok": True, "status": "success", "post_id": post.id, **log_extra}
    except PipelineSkip as exc:
        item.status = PipelineItem.STATUS_SKIPPED
        item.error_message = f"{exc.code}: {exc.message}"
        item.save(update_fields=["status", "error_message", "updated_at"])
        logger.info("pipeline_item_skipped %s err=%s", log_extra, item.error_message)
        return {"ok": False, "status": "skipped", "error": item.error_message, **log_extra}
    except Exception as exc:  # noqa: BLE001
        item.status = PipelineItem.STATUS_FAILED
        item.error_message = str(exc)[:2000]
        item.save(update_fields=["status", "error_message", "updated_at"])
        PipelineRun.objects.filter(pk=run.pk).update(
            fail_count=F("fail_count") + 1,
            updated_at=timezone.now(),
        )
        logger.exception("pipeline_item_failed %s", log_extra)
        return {"ok": False, "status": "failed", "error": item.error_message, **log_extra}


def run_daily_batch(*, sync: bool = False) -> dict:
    """
    编排日批。sync=True 时在当前进程串行处理（管理命令/测试）；
    False 时对每条 item 投递 Celery 任务。
    """
    run_date = today_in_pipeline_tz()
    target = daily_count()

    if not pipeline_enabled():
        run = PipelineRun.objects.create(
            run_date=run_date,
            status=PipelineRun.STATUS_DISABLED,
            target_count=target,
            error_message="CONTENT_PIPELINE_ENABLED=false",
        )
        logger.info("pipeline_disabled run_id=%s", run.id)
        return {"ok": True, "disabled": True, "run_id": run.id}

    run = PipelineRun.objects.create(
        run_date=run_date,
        status=PipelineRun.STATUS_RUNNING,
        target_count=target,
    )

    try:
        pool = candidate_pool_size(target)
        candidates = collect_candidates(keywords(), needed=pool)
    except PipelineError as exc:
        run.status = PipelineRun.STATUS_FAILED
        run.error_message = f"{exc.code}: {exc.message}"
        run.save(update_fields=["status", "error_message", "updated_at"])
        return {"ok": False, "run_id": run.id, "error": run.error_message}

    if not candidates:
        run.status = PipelineRun.STATUS_FAILED
        run.error_message = "无可用候选视频"
        run.save(update_fields=["status", "error_message", "updated_at"])
        return {"ok": False, "run_id": run.id, "error": run.error_message}

    items = []
    for idx, cand in enumerate(candidates):
        item = PipelineItem.objects.create(
            run=run,
            youtube_video_id=cand["video_id"],
            keyword=cand.get("keyword") or "",
            language=language_for_index(idx),
            title=(cand.get("title") or "")[:200],
            status=PipelineItem.STATUS_PENDING,
        )
        items.append(item)

    if sync:
        for item in items:
            run.refresh_from_db()
            if run.success_count >= run.target_count:
                item.status = PipelineItem.STATUS_SKIPPED
                item.error_message = "本轮目标已达成"
                item.save(update_fields=["status", "error_message", "updated_at"])
                continue
            process_pipeline_item(item.id)
        finalize_run(run)
        run.refresh_from_db()
        return {
            "ok": run.success_count > 0,
            "run_id": run.id,
            "success_count": run.success_count,
            "fail_count": run.fail_count,
            "status": run.status,
        }

    from apps.content_pipeline.tasks import process_video_item

    for item in items:
        process_video_item.delay(item.id)

    # 异步模式下由最后完成的任务 finalize；此处先保持 running
    # 另投递收尾检查任务
    from apps.content_pipeline.tasks import finalize_daily_run

    finalize_daily_run.apply_async(args=[run.id], countdown=600)
    return {
        "ok": True,
        "run_id": run.id,
        "queued": len(items),
        "status": run.status,
    }
