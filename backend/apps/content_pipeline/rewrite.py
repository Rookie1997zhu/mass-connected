"""Gemini 润色：字幕 → 博客 JSON。"""

from __future__ import annotations

import json
import logging
import re
from typing import Any

from apps.content_pipeline.config import gemini_api_key, gemini_model
from apps.content_pipeline.exceptions import PipelineError

logger = logging.getLogger(__name__)

_YOUTUBE_URL_RE = re.compile(r"(https?://)?(www\.)?(youtube\.com|youtu\.be)\S*", re.I)

_LANG_NAMES = {
    "zh": "Simplified Chinese",
    "ko": "Korean",
}


def _strip_youtube_urls(text: str) -> str:
    return _YOUTUBE_URL_RE.sub("", text or "").strip()


def _extract_json(raw: str) -> dict[str, Any]:
    text = (raw or "").strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text)
        text = re.sub(r"\s*```$", "", text)
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        match = re.search(r"\{[\s\S]*\}", text)
        if not match:
            raise PipelineError("REWRITE_JSON_INVALID", "Gemini 返回非 JSON")
        try:
            data = json.loads(match.group(0))
        except json.JSONDecodeError as exc:
            raise PipelineError("REWRITE_JSON_INVALID", "Gemini JSON 解析失败") from exc
    if not isinstance(data, dict):
        raise PipelineError("REWRITE_JSON_INVALID", "Gemini JSON 根节点须为对象")
    return data


def rewrite_transcript_to_article(
    *,
    transcript: str,
    language: str,
    source_title: str = "",
    keyword: str = "",
) -> dict[str, Any]:
    api_key = gemini_api_key()
    if not api_key:
        raise PipelineError("GEMINI_NOT_CONFIGURED", "未配置 GEMINI_API_KEY")
    lang = (language or "zh").strip().lower()
    if lang not in _LANG_NAMES:
        raise PipelineError("REWRITE_LANG_INVALID", "语种仅支持 zh/ko")

    lang_name = _LANG_NAMES[lang]
    system_instruction = (
        "You are an editorial writer for an OEM/ODM manufacturing platform blog. "
        f"Rewrite the transcript into an original article in {lang_name}. "
        "Do deep paraphrase — never copy sentences verbatim. "
        "Do NOT include any YouTube URLs or video links. "
        "Return ONLY a JSON object with keys: "
        "title (string, <=80 chars), summary (string), content_html (string HTML with <p>/<h2>/<ul>), "
        "tags (array of up to 5 short strings). "
        "Optionally include image_slots as an integer 0-2 for inline illustrations. "
        "content_html may contain placeholders like <!--IMAGE_1--> and <!--IMAGE_2-->."
    )
    user_prompt = (
        f"Keyword focus: {keyword or 'manufacturing'}\n"
        f"Source title (for context only, do not copy): {source_title or '(none)'}\n"
        f"Transcript:\n{transcript}"
    )

    try:
        from google import genai
        from google.genai import types
    except ImportError as exc:  # pragma: no cover
        raise PipelineError("GEMINI_SDK_MISSING", "未安装 google-genai") from exc

    try:
        client = genai.Client(api_key=api_key)
        response = client.models.generate_content(
            model=gemini_model(),
            contents=user_prompt,
            config=types.GenerateContentConfig(
                system_instruction=system_instruction,
                temperature=0.7,
                response_mime_type="application/json",
            ),
        )
        raw = (getattr(response, "text", None) or "").strip()
    except Exception as exc:  # noqa: BLE001
        logger.exception("gemini_rewrite_failed")
        raise PipelineError("REWRITE_FAILED", f"Gemini 润色失败: {exc}") from exc

    data = _extract_json(raw)
    title = _strip_youtube_urls(str(data.get("title") or "").strip())
    summary = _strip_youtube_urls(str(data.get("summary") or "").strip())
    content_html = _strip_youtube_urls(str(data.get("content_html") or data.get("content") or "").strip())
    if not title or not content_html:
        raise PipelineError("REWRITE_INCOMPLETE", "润色结果缺少 title 或 content")

    tags_raw = data.get("tags") or []
    tags: list[str] = []
    if isinstance(tags_raw, list):
        for item in tags_raw:
            tag = str(item).strip()
            if tag and tag not in tags and len(tag) <= 32:
                tags.append(tag)
            if len(tags) >= 5:
                break

    image_slots = data.get("image_slots", 1)
    try:
        image_slots = int(image_slots)
    except (TypeError, ValueError):
        image_slots = 1
    image_slots = max(0, min(2, image_slots))

    return {
        "title": title[:200],
        "summary": summary[:2000],
        "content_html": content_html,
        "tags": tags,
        "image_slots": image_slots,
        "language": lang,
    }
