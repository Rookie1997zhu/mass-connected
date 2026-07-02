from rest_framework import serializers

from apps.catalog.models import Category, Product, ProductImage
from apps.i18n.fields import resolve_i18n


class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ["id", "parent", "name", "slug", "sort_order", "is_active", "created_at", "updated_at"]
        read_only_fields = ["id", "created_at", "updated_at"]


class ProductImageSerializer(serializers.ModelSerializer):
    url = serializers.SerializerMethodField()

    class Meta:
        model = ProductImage
        fields = ["id", "url", "alt_text", "sort_order", "is_cover"]
        read_only_fields = ["id"]

    def get_url(self, obj):
        request = self.context.get("request")
        if obj.file and request:
            return request.build_absolute_uri(obj.file.url)
        return obj.file.url if obj.file else ""


class ProductListSerializer(serializers.ModelSerializer):
    name_text = serializers.SerializerMethodField()
    category_name = serializers.SerializerMethodField()
    cover_url = serializers.SerializerMethodField()

    class Meta:
        model = Product
        fields = [
            "id",
            "sku",
            "name",
            "name_text",
            "category",
            "category_name",
            "price_amount",
            "currency",
            "stock",
            "cover_url",
            "is_active",
            "is_shop_visible",
        ]

    def get_name_text(self, obj):
        lang = self.context.get("lang", "ko")
        return resolve_i18n(obj.name, lang)

    def get_category_name(self, obj):
        lang = self.context.get("lang", "ko")
        return resolve_i18n(obj.category.name, lang) if obj.category else ""

    def get_cover_url(self, obj):
        cover = obj.images.filter(is_cover=True).first() or obj.images.first()
        if not cover:
            return ""
        request = self.context.get("request")
        if cover.file and request:
            return request.build_absolute_uri(cover.file.url)
        return cover.file.url if cover.file else ""


class ProductDetailSerializer(ProductListSerializer):
    description_text = serializers.SerializerMethodField()
    images = ProductImageSerializer(many=True, read_only=True)

    class Meta(ProductListSerializer.Meta):
        fields = ProductListSerializer.Meta.fields + [
            "description",
            "description_text",
            "specs",
            "moq",
            "lead_time_days",
            "images",
            "created_at",
            "updated_at",
        ]

    def get_description_text(self, obj):
        lang = self.context.get("lang", "ko")
        return resolve_i18n(obj.description, lang)


class ProductWriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = Product
        fields = [
            "category",
            "sku",
            "name",
            "description",
            "specs",
            "price_amount",
            "currency",
            "stock",
            "moq",
            "lead_time_days",
            "is_active",
            "is_shop_visible",
            "is_oem_visible",
        ]
