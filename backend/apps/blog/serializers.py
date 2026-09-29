from django.db import IntegrityError
from rest_framework import serializers

from apps.blog.models import BlogCategory, BlogComment, BlogPost
from apps.blog.services import author_display_name
from core.exceptions import AppAPIException


class BlogCategorySlugConflict(AppAPIException):
    status_code = 409
    default_code = "BLOG_CATEGORY_SLUG_CONFLICT"
    default_detail = "分类标识已存在"


class BlogCommentTooLong(AppAPIException):
    status_code = 400
    default_code = "BLOG_COMMENT_TOO_LONG"
    default_detail = "评论超过 1000 字"


class BlogCategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = BlogCategory
        fields = ["id", "name", "slug", "sort_order", "is_active", "created_at", "updated_at"]
        read_only_fields = ["id", "created_at", "updated_at"]
        extra_kwargs = {"slug": {"validators": []}}

    def validate_slug(self, value):
        slug = (value or "").strip().lower()
        if not slug:
            raise serializers.ValidationError("请填写分类标识")
        qs = BlogCategory.objects.filter(slug=slug)
        if self.instance is not None:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise BlogCategorySlugConflict()
        return slug

    def create(self, validated_data):
        try:
            return super().create(validated_data)
        except IntegrityError as exc:
            raise BlogCategorySlugConflict() from exc

    def update(self, instance, validated_data):
        try:
            return super().update(instance, validated_data)
        except IntegrityError as exc:
            raise BlogCategorySlugConflict() from exc


class BlogCategoryBriefSerializer(serializers.ModelSerializer):
    class Meta:
        model = BlogCategory
        fields = ["id", "name", "slug"]
        read_only_fields = fields


class BlogPostCardSerializer(serializers.ModelSerializer):
    category = BlogCategoryBriefSerializer(read_only=True)
    author_name = serializers.SerializerMethodField()

    class Meta:
        model = BlogPost
        fields = [
            "id",
            "title",
            "summary",
            "cover_image",
            "category",
            "tags",
            "language",
            "author_name",
            "is_pinned",
            "is_featured",
            "published_at",
            "view_count",
            "like_count",
            "comment_count",
        ]
        read_only_fields = fields

    def get_author_name(self, obj):
        return author_display_name(obj.author)


class BlogPostPublicSerializer(BlogPostCardSerializer):
    class Meta(BlogPostCardSerializer.Meta):
        fields = BlogPostCardSerializer.Meta.fields + ["content"]


class BlogPostAdminSerializer(serializers.ModelSerializer):
    author_name = serializers.SerializerMethodField()

    class Meta:
        model = BlogPost
        fields = [
            "id",
            "title",
            "summary",
            "content",
            "cover_image",
            "category",
            "tags",
            "language",
            "status",
            "is_pinned",
            "is_featured",
            "published_at",
            "view_count",
            "like_count",
            "comment_count",
            "author",
            "author_name",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "published_at",
            "view_count",
            "like_count",
            "comment_count",
            "author",
            "author_name",
            "created_at",
            "updated_at",
        ]

    def get_author_name(self, obj):
        return author_display_name(obj.author)

    def validate_title(self, value):
        title = (value or "").strip()
        if not title:
            raise serializers.ValidationError("请填写标题")
        return title

    def validate_tags(self, value):
        if value in (None, ""):
            return []
        if not isinstance(value, list):
            raise serializers.ValidationError("标签须为字符串列表")
        cleaned = []
        for item in value:
            tag = str(item).strip()
            if not tag:
                continue
            if len(tag) > 32:
                raise serializers.ValidationError("单个标签不超过 32 字")
            if tag not in cleaned:
                cleaned.append(tag)
        if len(cleaned) > 10:
            raise serializers.ValidationError("最多 10 个标签")
        return cleaned

    def validate_language(self, value):
        allowed = {code for code, _label in BlogPost.LANGUAGE_CHOICES}
        if value not in allowed:
            raise serializers.ValidationError("语种无效")
        return value

    def validate_status(self, value):
        allowed = {code for code, _label in BlogPost.STATUS_CHOICES}
        if value not in allowed:
            raise serializers.ValidationError("状态无效")
        return value


class BlogCommentPublicSerializer(serializers.ModelSerializer):
    author_name = serializers.SerializerMethodField()
    is_mine = serializers.SerializerMethodField()
    replies = serializers.SerializerMethodField()

    class Meta:
        model = BlogComment
        fields = ["id", "content", "created_at", "author_name", "is_mine", "replies"]
        read_only_fields = fields

    def get_author_name(self, obj):
        return author_display_name(obj.user)

    def get_is_mine(self, obj):
        request = self.context.get("request")
        user = getattr(request, "user", None)
        return bool(user and user.is_authenticated and obj.user_id == user.id)

    def get_replies(self, obj):
        if obj.parent_id:
            return []
        replies = getattr(obj, "visible_replies", None)
        if replies is None:
            replies = obj.replies.filter(is_hidden=False).select_related("user")
        return BlogCommentPublicSerializer(replies, many=True, context=self.context).data


class BlogCommentWriteSerializer(serializers.Serializer):
    content = serializers.CharField()
    parent = serializers.PrimaryKeyRelatedField(
        queryset=BlogComment.objects.all(),
        required=False,
        allow_null=True,
    )

    def validate_content(self, value):
        text = (value or "").strip()
        if not text:
            raise serializers.ValidationError("评论不能为空")
        if len(text) > BlogComment.CONTENT_MAX_LENGTH:
            raise BlogCommentTooLong()
        return text

    def validate_parent(self, parent):
        if parent is None:
            return None
        post = self.context["post"]
        if parent.post_id != post.id:
            raise serializers.ValidationError("回复必须属于同一篇文章")
        if parent.parent_id:
            raise serializers.ValidationError("仅支持一级回复")
        if parent.is_hidden:
            raise serializers.ValidationError("无法回复已隐藏的评论")
        return parent


class BlogCommentAdminSerializer(serializers.ModelSerializer):
    author_name = serializers.SerializerMethodField()
    author_email = serializers.EmailField(source="user.email", read_only=True)
    post_title = serializers.CharField(source="post.title", read_only=True)

    class Meta:
        model = BlogComment
        fields = [
            "id",
            "post",
            "post_title",
            "parent",
            "content",
            "is_hidden",
            "author_name",
            "author_email",
            "created_at",
        ]
        read_only_fields = [
            "id",
            "post",
            "post_title",
            "parent",
            "content",
            "author_name",
            "author_email",
            "created_at",
        ]

    def get_author_name(self, obj):
        return author_display_name(obj.user)
