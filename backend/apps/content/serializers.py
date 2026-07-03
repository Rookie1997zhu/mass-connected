from rest_framework import serializers

from apps.content.models import Case, ContentPage, Download, FAQ, NavItem, News


class CaseSerializer(serializers.ModelSerializer):
    class Meta:
        model = Case
        fields = "__all__"


class NewsSerializer(serializers.ModelSerializer):
    class Meta:
        model = News
        fields = "__all__"


class FAQSerializer(serializers.ModelSerializer):
    class Meta:
        model = FAQ
        fields = "__all__"


class DownloadSerializer(serializers.ModelSerializer):
    url = serializers.SerializerMethodField()

    class Meta:
        model = Download
        fields = [
            "id",
            "title",
            "file",
            "url",
            "file_type",
            "locale",
            "sort_order",
            "is_active",
        ]
        read_only_fields = ["id", "url"]

    def get_url(self, obj):
        request = self.context.get("request")
        if obj.file and request:
            return request.build_absolute_uri(obj.file.url)
        return obj.file.url if obj.file else ""


class ContentPageSerializer(serializers.ModelSerializer):
    class Meta:
        model = ContentPage
        fields = ["id", "page_key", "title", "body", "updated_at"]


class NavItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = NavItem
        fields = [
            "id",
            "parent",
            "label",
            "path",
            "sort_order",
            "is_active",
            "open_in_new_tab",
            "created_at",
            "updated_at",
        ]

    def validate(self, attrs):
        parent = attrs.get("parent", getattr(self.instance, "parent", None))
        path = attrs.get("path", getattr(self.instance, "path", ""))
        if parent and not path:
            raise serializers.ValidationError({"path": "子菜单项必须填写链接路径。"})
        if parent and parent.parent_id:
            raise serializers.ValidationError({"parent": "导航仅支持两级结构。"})
        return attrs
