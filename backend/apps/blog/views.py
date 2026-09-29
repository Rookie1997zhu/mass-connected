import logging

from django.db.models import Prefetch, Q
from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView

from apps.blog.models import BlogCategory, BlogComment, BlogPost
from apps.blog.serializers import (
    BlogCategorySerializer,
    BlogCommentAdminSerializer,
    BlogCommentPublicSerializer,
    BlogCommentWriteSerializer,
    BlogPostAdminSerializer,
    BlogPostCardSerializer,
    BlogPostPublicSerializer,
)
from apps.blog.services import (
    create_comment,
    delete_comment,
    like_post,
    record_post_view,
    set_comment_hidden,
    stamp_published_at,
    unlike_post,
)
from core.exceptions import AppAPIException
from core.pagination import StandardPagination
from core.permissions import IsAdminRole, IsEmailVerified
from core.responses import success_response

logger = logging.getLogger(__name__)


class BlogPostNotFound(AppAPIException):
    status_code = status.HTTP_404_NOT_FOUND
    default_code = "BLOG_POST_NOT_FOUND"
    default_detail = "文章不存在"


class BlogCommentForbidden(AppAPIException):
    status_code = status.HTTP_403_FORBIDDEN
    default_code = "BLOG_COMMENT_FORBIDDEN"
    default_detail = "只能删除自己的评论"


def _published_posts():
    return BlogPost.objects.filter(status=BlogPost.STATUS_PUBLISHED).select_related(
        "category", "author"
    )


def _parse_bool(value):
    return str(value).lower() in {"1", "true", "yes"}


def _apply_post_filters(qs, params):
    category = (params.get("category") or "").strip()
    if category:
        qs = qs.filter(category__slug=category)
    tag = (params.get("tag") or "").strip()
    if tag:
        qs = qs.filter(tags__contains=[tag])
    language = (params.get("language") or "").strip()
    if language:
        qs = qs.filter(language=language)
    keyword = (params.get("q") or "").strip()
    if keyword:
        qs = qs.filter(Q(title__icontains=keyword) | Q(summary__icontains=keyword))
    if "is_featured" in params and params.get("is_featured") != "":
        qs = qs.filter(is_featured=_parse_bool(params.get("is_featured")))
    return qs


def _order_posts(qs, ordering, pin_first=True):
    if ordering == "popular":
        return qs.order_by("-view_count", "-published_at", "-id")
    if pin_first:
        return qs.order_by("-is_pinned", "-published_at", "-id")
    return qs.order_by("-published_at", "-id")


def _paginate(request, qs, serializer_class, context=None):
    paginator = StandardPagination()
    page = paginator.paginate_queryset(qs, request)
    data = serializer_class(page, many=True, context=context or {"request": request}).data
    return paginator.get_paginated_response(data)


def _get_published_post(pk):
    post = BlogPost.objects.filter(pk=pk, status=BlogPost.STATUS_PUBLISHED).select_related(
        "category", "author"
    ).first()
    if post is None:
        raise BlogPostNotFound()
    return post


def _neighbor_cards(post):
    if post.published_at is None:
        return None, None
    base = _published_posts().exclude(pk=post.pk)
    previous = (
        base.filter(
            Q(published_at__gt=post.published_at)
            | Q(published_at=post.published_at, id__gt=post.id)
        )
        .order_by("published_at", "id")
        .first()
    )
    next_post = (
        base.filter(
            Q(published_at__lt=post.published_at)
            | Q(published_at=post.published_at, id__lt=post.id)
        )
        .order_by("-published_at", "-id")
        .first()
    )
    return previous, next_post


def _related_posts(post):
    qs = _published_posts().exclude(pk=post.pk)
    if post.category_id:
        same_category = qs.filter(category_id=post.category_id).order_by("-published_at", "-id")[:4]
        if same_category:
            return list(same_category)
    return list(qs.order_by("-published_at", "-id")[:4])


class PublicBlogCategoryListView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        qs = BlogCategory.objects.filter(is_active=True).order_by("sort_order", "id")
        return success_response(
            {"items": BlogCategorySerializer(qs, many=True).data},
            request=request,
        )


class PublicBlogTagListView(APIView):
    """已发布文章的标签及出现次数，供前台标签云使用。"""

    permission_classes = [AllowAny]

    def get(self, request):
        counts = {}
        for tags in BlogPost.objects.filter(status=BlogPost.STATUS_PUBLISHED).values_list(
            "tags", flat=True
        ):
            if not isinstance(tags, list):
                continue
            for tag in tags:
                text = str(tag).strip()
                if text:
                    counts[text] = counts.get(text, 0) + 1
        items = [
            {"name": name, "count": count}
            for name, count in sorted(counts.items(), key=lambda item: (-item[1], item[0]))
        ]
        return success_response({"items": items[:40]}, request=request)


class PublicBlogPostListView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        ordering = request.query_params.get("ordering") or "latest"
        qs = _order_posts(_apply_post_filters(_published_posts(), request.query_params), ordering)
        return _paginate(request, qs, BlogPostCardSerializer)


class PublicBlogPostDetailView(APIView):
    permission_classes = [AllowAny]

    def get(self, request, pk):
        post = _get_published_post(pk)
        record_post_view(request, post)
        user = request.user
        liked = bool(
            user
            and user.is_authenticated
            and post.likes.filter(user=user).exists()
        )
        previous, next_post = _neighbor_cards(post)
        data = BlogPostPublicSerializer(post, context={"request": request}).data
        data["liked_by_me"] = liked
        data["previous"] = BlogPostCardSerializer(previous).data if previous else None
        data["next"] = BlogPostCardSerializer(next_post).data if next_post else None
        data["related"] = BlogPostCardSerializer(_related_posts(post), many=True).data
        return success_response(data, request=request)


class PublicBlogCommentListView(APIView):
    permission_classes = [AllowAny]

    def get(self, request, pk):
        post = _get_published_post(pk)
        visible_replies = BlogComment.objects.filter(is_hidden=False).select_related("user")
        qs = (
            BlogComment.objects.filter(post=post, parent__isnull=True, is_hidden=False)
            .select_related("user")
            .prefetch_related(Prefetch("replies", queryset=visible_replies, to_attr="visible_replies"))
            .order_by("created_at", "id")
        )
        return _paginate(request, qs, BlogCommentPublicSerializer, context={"request": request})


class BlogPostLikeView(APIView):
    permission_classes = [IsAuthenticated, IsEmailVerified]

    def put(self, request, pk):
        post = _get_published_post(pk)
        like_count = like_post(post, request.user)
        return success_response({"liked": True, "like_count": like_count}, request=request)

    def delete(self, request, pk):
        post = _get_published_post(pk)
        like_count = unlike_post(post, request.user)
        return success_response({"liked": False, "like_count": like_count}, request=request)


class BlogPostCommentCreateView(APIView):
    permission_classes = [IsAuthenticated, IsEmailVerified]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "blog_comment"

    def post(self, request, pk):
        post = _get_published_post(pk)
        serializer = BlogCommentWriteSerializer(data=request.data, context={"post": post, "request": request})
        serializer.is_valid(raise_exception=True)
        comment = create_comment(
            post,
            request.user,
            serializer.validated_data["content"],
            parent=serializer.validated_data.get("parent"),
        )
        comment = BlogComment.objects.select_related("user").get(pk=comment.pk)
        return success_response(
            BlogCommentPublicSerializer(comment, context={"request": request}).data,
            status=status.HTTP_201_CREATED,
            request=request,
        )


class BlogCommentDeleteView(APIView):
    permission_classes = [IsAuthenticated, IsEmailVerified]

    def delete(self, request, pk):
        comment = BlogComment.objects.filter(pk=pk).first()
        if comment is None or comment.post.status != BlogPost.STATUS_PUBLISHED:
            raise BlogPostNotFound()
        if comment.user_id != request.user.id:
            raise BlogCommentForbidden()
        delete_comment(comment)
        return success_response({}, message="已删除", request=request)


class AdminBlogCategoryListCreateView(APIView):
    permission_classes = [IsAdminRole]

    def get(self, request):
        qs = BlogCategory.objects.all().order_by("sort_order", "id")
        return _paginate(request, qs, BlogCategorySerializer)

    def post(self, request):
        serializer = BlogCategorySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return success_response(serializer.data, status=status.HTTP_201_CREATED, request=request)


class AdminBlogCategoryDetailView(APIView):
    permission_classes = [IsAdminRole]

    def get(self, request, pk):
        category = get_object_or_404(BlogCategory, pk=pk)
        return success_response(BlogCategorySerializer(category).data, request=request)

    def patch(self, request, pk):
        category = get_object_or_404(BlogCategory, pk=pk)
        serializer = BlogCategorySerializer(category, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return success_response(serializer.data, request=request)

    def delete(self, request, pk):
        category = get_object_or_404(BlogCategory, pk=pk)
        category.delete()
        return success_response({}, message="已删除", request=request)


class AdminBlogPostListCreateView(APIView):
    permission_classes = [IsAdminRole]

    def get(self, request):
        qs = BlogPost.objects.select_related("category", "author").all()
        status_value = (request.query_params.get("status") or "").strip()
        if status_value:
            qs = qs.filter(status=status_value)
        qs = _apply_post_filters(qs, request.query_params)
        qs = qs.order_by("-updated_at", "-id")
        return _paginate(request, qs, BlogPostAdminSerializer)

    def post(self, request):
        serializer = BlogPostAdminSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        post = serializer.save(author=request.user)
        stamp_published_at(post)
        post.refresh_from_db()
        return success_response(
            BlogPostAdminSerializer(post).data,
            status=status.HTTP_201_CREATED,
            request=request,
        )


class AdminBlogPostDetailView(APIView):
    permission_classes = [IsAdminRole]

    def get(self, request, pk):
        post = get_object_or_404(BlogPost.objects.select_related("category", "author"), pk=pk)
        return success_response(BlogPostAdminSerializer(post).data, request=request)

    def patch(self, request, pk):
        post = get_object_or_404(BlogPost, pk=pk)
        serializer = BlogPostAdminSerializer(post, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        post = serializer.save()
        stamp_published_at(post)
        post.refresh_from_db()
        return success_response(BlogPostAdminSerializer(post).data, request=request)

    def delete(self, request, pk):
        post = get_object_or_404(BlogPost, pk=pk)
        post.delete()
        return success_response({}, message="已删除", request=request)


class AdminBlogCommentListView(APIView):
    permission_classes = [IsAdminRole]

    def get(self, request):
        qs = BlogComment.objects.select_related("post", "user").order_by("-created_at", "-id")
        post_id = request.query_params.get("post")
        if post_id:
            qs = qs.filter(post_id=post_id)
        hidden = request.query_params.get("is_hidden")
        if hidden not in (None, ""):
            qs = qs.filter(is_hidden=_parse_bool(hidden))
        return _paginate(request, qs, BlogCommentAdminSerializer)


class AdminBlogCommentDetailView(APIView):
    permission_classes = [IsAdminRole]

    def patch(self, request, pk):
        comment = get_object_or_404(BlogComment.objects.select_related("post", "user"), pk=pk)
        if "is_hidden" in request.data:
            set_comment_hidden(comment, _parse_bool(request.data.get("is_hidden")))
            comment.refresh_from_db()
        return success_response(BlogCommentAdminSerializer(comment).data, request=request)

    def delete(self, request, pk):
        comment = get_object_or_404(BlogComment, pk=pk)
        delete_comment(comment)
        return success_response({}, message="已删除", request=request)
