import logging

from django.core.cache import cache
from django.db import transaction
from django.db.models import F
from django.db.models.functions import Greatest
from django.utils import timezone

from apps.blog.models import BlogComment, BlogLike, BlogPost

logger = logging.getLogger(__name__)

VIEW_DEDUPE_SECONDS = 30 * 60


def author_display_name(user):
    if user is None:
        return ""
    name = (getattr(user, "name", "") or "").strip()
    if name:
        return name
    email = getattr(user, "email", "") or ""
    return email.split("@")[0]


def stamp_published_at(post):
    """首次发布时写入 published_at，之后保持不变。"""
    if post.status == BlogPost.STATUS_PUBLISHED and post.published_at is None:
        post.published_at = timezone.now()
        post.save(update_fields=["published_at"])


def adjust_count(post_id, field_name, delta):
    if not delta:
        return
    BlogPost.objects.filter(pk=post_id).update(
        **{field_name: Greatest(F(field_name) + delta, 0)}
    )


def visitor_key(request):
    user = getattr(request, "user", None)
    if user is not None and getattr(user, "is_authenticated", False):
        return f"u{user.id}"
    forwarded = request.META.get("HTTP_X_FORWARDED_FOR", "")
    ip = forwarded.split(",")[0].strip() if forwarded else request.META.get("REMOTE_ADDR", "")
    return f"ip{ip or 'anon'}"


def record_post_view(request, post):
    """同一访客 30 分钟内只计一次浏览。缓存失败时仍计数，避免丢统计。"""
    key = f"blog:view:{post.id}:{visitor_key(request)}"
    try:
        is_new = cache.add(key, "1", timeout=VIEW_DEDUPE_SECONDS)
    except Exception:
        logger.exception("blog view dedupe failed post_id=%s", post.id)
        is_new = True
    if not is_new:
        return
    BlogPost.objects.filter(pk=post.id).update(view_count=F("view_count") + 1)
    post.refresh_from_db(fields=["view_count"])


def like_post(post, user):
    with transaction.atomic():
        _, created = BlogLike.objects.get_or_create(post=post, user=user)
        if created:
            adjust_count(post.id, "like_count", 1)
    post.refresh_from_db(fields=["like_count"])
    return post.like_count


def unlike_post(post, user):
    with transaction.atomic():
        deleted, _ = BlogLike.objects.filter(post=post, user=user).delete()
        if deleted:
            adjust_count(post.id, "like_count", -1)
    post.refresh_from_db(fields=["like_count"])
    return post.like_count


def visible_tree_count(comment):
    visible_replies = comment.replies.filter(is_hidden=False).count()
    return visible_replies + (0 if comment.is_hidden else 1)


def create_comment(post, user, content, parent=None):
    comment = BlogComment.objects.create(
        post=post,
        user=user,
        parent=parent,
        content=content,
    )
    adjust_count(post.id, "comment_count", 1)
    transaction.on_commit(lambda: _notify_new_comment(post.id, comment.id))
    return comment


def _notify_new_comment(post_id, comment_id):
    from apps.notification.services import notify_staff

    post = BlogPost.objects.filter(pk=post_id).first()
    comment = BlogComment.objects.filter(pk=comment_id).first()
    if post is None or comment is None:
        return
    notify_staff(
        "blog",
        f"博客新评论：{post.title[:40]}",
        comment.content[:200],
        related_type="blog_post",
        related_id=post.id,
    )


def set_comment_hidden(comment, hidden):
    hidden = bool(hidden)
    if comment.is_hidden == hidden:
        return comment
    comment.is_hidden = hidden
    comment.save(update_fields=["is_hidden", "updated_at"])
    adjust_count(comment.post_id, "comment_count", -1 if hidden else 1)
    return comment


def delete_comment(comment):
    delta = visible_tree_count(comment)
    post_id = comment.post_id
    comment.delete()
    adjust_count(post_id, "comment_count", -delta)
