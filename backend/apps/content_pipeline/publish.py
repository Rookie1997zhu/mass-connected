"""写入 BlogPost 并直接发布。"""

from __future__ import annotations

import logging
import re

from django.contrib.auth import get_user_model

from apps.blog.models import BlogPost
from apps.blog.services import stamp_published_at
from apps.content_pipeline.config import author_email
from apps.content_pipeline.exceptions import PipelineError

logger = logging.getLogger(__name__)

_YOUTUBE_URL_RE = re.compile(r"(https?://)?(www\.)?(youtube\.com|youtu\.be)\S*", re.I)


def resolve_author():
    email = author_email()
    if not email:
        raise PipelineError("PIPELINE_AUTHOR_MISSING", "未配置 CONTENT_PIPELINE_AUTHOR_EMAIL / BLOG_MCP_AUTHOR_EMAIL")
    User = get_user_model()
    user = User.objects.filter(email__iexact=email).first()
    if user is None or not user.is_active or getattr(user, "role", None) not in {
        "super_admin",
        "operator",
        "sales",
    }:
        raise PipelineError("PIPELINE_AUTHOR_INVALID", "流水线作者账号无效")
    return user


def assert_no_youtube_links(*parts: str) -> None:
    for part in parts:
        if _YOUTUBE_URL_RE.search(part or ""):
            raise PipelineError("YOUTUBE_LINK_FORBIDDEN", "文稿含 YouTube 链接，已拒绝发布")


def publish_blog_post(
    *,
    title: str,
    summary: str,
    content_html: str,
    language: str,
    tags: list[str] | None = None,
    cover_image: str = "",
    author=None,
) -> BlogPost:
    assert_no_youtube_links(title, summary, content_html)
    if author is None:
        author = resolve_author()
    post = BlogPost.objects.create(
        title=title[:200],
        summary=summary or "",
        content=content_html or "",
        cover_image=cover_image or "",
        tags=list(tags or [])[:10],
        language=language,
        status=BlogPost.STATUS_PUBLISHED,
        author=author,
    )
    stamp_published_at(post)
    post.refresh_from_db()
    logger.info(
        "pipeline_published post_id=%s language=%s title=%s",
        post.id,
        language,
        post.title[:80],
    )
    return post
