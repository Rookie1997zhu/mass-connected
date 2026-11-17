"""拉取 YouTube 字幕。"""

from __future__ import annotations

import logging

from apps.content_pipeline.exceptions import PipelineSkip

logger = logging.getLogger(__name__)

PREFERRED_LANGS = ("zh-Hans", "zh-CN", "zh", "ko", "en")


def _snippets_to_text(snippets) -> str:
    parts = []
    for item in snippets:
        if isinstance(item, dict):
            text = (item.get("text") or "").strip()
        else:
            text = (getattr(item, "text", None) or "").strip()
        if text:
            parts.append(text)
    return "\n".join(parts).strip()


def fetch_transcript_text(video_id: str) -> str:
    try:
        from youtube_transcript_api import YouTubeTranscriptApi
    except ImportError as exc:  # pragma: no cover
        raise PipelineSkip("TRANSCRIPT_DEP_MISSING", "未安装 youtube-transcript-api") from exc

    try:
        # 兼容 0.x get_transcript 与 1.x list/fetch
        if hasattr(YouTubeTranscriptApi, "get_transcript"):
            snippets = YouTubeTranscriptApi.get_transcript(video_id, languages=list(PREFERRED_LANGS))
        else:
            api = YouTubeTranscriptApi()
            transcript_list = api.list(video_id)
            transcript = None
            for finder_name in ("find_transcript", "find_generated_transcript"):
                finder = getattr(transcript_list, finder_name, None)
                if finder is None:
                    continue
                try:
                    transcript = finder(list(PREFERRED_LANGS))
                    break
                except Exception:  # noqa: BLE001
                    continue
            if transcript is None:
                iterator = iter(transcript_list)
                transcript = next(iterator, None)
            if transcript is None:
                raise PipelineSkip("TRANSCRIPT_NOT_FOUND", "无可用字幕")
            snippets = list(transcript.fetch())
    except PipelineSkip:
        raise
    except Exception as exc:  # noqa: BLE001
        name = type(exc).__name__
        if name in {"TranscriptsDisabled", "NoTranscriptFound", "VideoUnavailable"}:
            raise PipelineSkip("TRANSCRIPT_UNAVAILABLE", f"字幕不可用: {exc}") from exc
        logger.exception("transcript_fetch_failed video_id=%s", video_id)
        raise PipelineSkip("TRANSCRIPT_FETCH_FAILED", f"拉字幕失败: {exc}") from exc

    joined = _snippets_to_text(snippets)
    if len(joined) < 80:
        raise PipelineSkip("TRANSCRIPT_TOO_SHORT", "字幕过短")
    if len(joined) > 12000:
        joined = joined[:12000]
    return joined
