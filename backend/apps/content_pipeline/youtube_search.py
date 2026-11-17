"""YouTube Data API v3 关键词检索。"""

from __future__ import annotations

import json
import logging
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from apps.content_pipeline.config import youtube_api_key
from apps.content_pipeline.exceptions import PipelineError
from apps.content_pipeline.models import UsedYouTubeVideo

logger = logging.getLogger(__name__)

SEARCH_URL = "https://www.googleapis.com/youtube/v3/search"


def search_videos_for_keyword(keyword: str, *, max_results: int = 10) -> list[dict[str, Any]]:
    api_key = youtube_api_key()
    if not api_key:
        raise PipelineError("YOUTUBE_API_KEY_MISSING", "未配置 YOUTUBE_API_KEY")

    params = {
        "part": "snippet",
        "type": "video",
        "q": keyword,
        "maxResults": str(min(max(1, max_results), 25)),
        "order": "relevance",
        "safeSearch": "moderate",
        "key": api_key,
    }
    url = f"{SEARCH_URL}?{urlencode(params)}"
    req = Request(url, headers={"User-Agent": "OEMContentPipeline/1.0"})
    try:
        with urlopen(req, timeout=30) as resp:  # noqa: S310 — Google API
            payload = json.loads(resp.read().decode("utf-8"))
    except (HTTPError, URLError, TimeoutError, json.JSONDecodeError) as exc:
        logger.exception("youtube_search_failed keyword=%s", keyword)
        raise PipelineError("YOUTUBE_SEARCH_FAILED", f"YouTube 搜索失败: {exc}") from exc

    items = []
    for entry in payload.get("items") or []:
        video_id = ((entry.get("id") or {}).get("videoId") or "").strip()
        snippet = entry.get("snippet") or {}
        if not video_id:
            continue
        items.append(
            {
                "video_id": video_id,
                "title": (snippet.get("title") or "").strip(),
                "description": (snippet.get("description") or "").strip(),
                "keyword": keyword,
            }
        )
    return items


def collect_candidates(keywords: list[str], *, needed: int) -> list[dict[str, Any]]:
    """按关键词轮询检索，排除已用 video_id，凑满 needed 条。"""
    if needed <= 0:
        return []
    used = set(UsedYouTubeVideo.objects.values_list("video_id", flat=True))
    seen: set[str] = set()
    results: list[dict[str, Any]] = []
    if not keywords:
        raise PipelineError("CONTENT_PIPELINE_KEYWORDS_EMPTY", "未配置 CONTENT_PIPELINE_KEYWORDS")

    per_keyword = max(5, (needed // max(len(keywords), 1)) + 3)
    for keyword in keywords:
        if len(results) >= needed:
            break
        try:
            found = search_videos_for_keyword(keyword, max_results=per_keyword)
        except PipelineError:
            logger.exception("keyword_search_skip keyword=%s", keyword)
            continue
        for item in found:
            video_id = item["video_id"]
            if video_id in used or video_id in seen:
                continue
            seen.add(video_id)
            results.append(item)
            if len(results) >= needed:
                break
    return results
