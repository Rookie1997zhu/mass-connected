from rest_framework import serializers

from apps.catalog.models import Product
from apps.i18n.fields import resolve_i18n
from apps.order.models import CartItem, Order, OrderItem
from core.media_urls import absolute_file_url


class CartItemSerializer(serializers.ModelSerializer):
    product_name = serializers.SerializerMethodField()
    product_sku = serializers.CharField(source="product.sku", read_only=True)
    cover_url = serializers.SerializerMethodField()

    class Meta:
        model = CartItem
        fields = [
            "id",
            "product",
            "product_name",
            "product_sku",
            "quantity",
            "unit_price_amount",
            "cover_url",
            "updated_at",
        ]
        read_only_fields = ["id", "unit_price_amount", "updated_at"]

    def get_product_name(self, obj):
        lang = self.context.get("lang", "ko")
        return resolve_i18n(obj.product.name, lang)

    def get_cover_url(self, obj):
        cover = obj.product.images.filter(is_cover=True).first() or obj.product.images.first()
        if not cover:
            return ""
        return absolute_file_url(self.context.get("request"), cover.file)


class CartItemCreateSerializer(serializers.Serializer):
    product_id = serializers.PrimaryKeyRelatedField(queryset=Product.objects.filter(is_active=True, is_shop_visible=True), source="product")
    quantity = serializers.IntegerField(min_value=1, default=1)


class OrderItemSerializer(serializers.ModelSerializer):
    product_name_text = serializers.SerializerMethodField()

    class Meta:
        model = OrderItem
        fields = [
            "id",
            "product",
            "product_name",
            "product_name_text",
            "quantity",
            "unit_price_amount",
            "line_total_amount",
        ]

    def get_product_name_text(self, obj):
        lang = self.context.get("lang", "ko")
        return resolve_i18n(obj.product_name, lang)


class OrderListSerializer(serializers.ModelSerializer):
    items_count = serializers.SerializerMethodField()

    class Meta:
        model = Order
        fields = [
            "id",
            "order_no",
            "status",
            "total_amount",
            "currency",
            "items_count",
            "created_at",
        ]

    def get_items_count(self, obj):
        return obj.items.count()


class OrderDetailSerializer(OrderListSerializer):
    items = OrderItemSerializer(many=True, read_only=True)

    class Meta(OrderListSerializer.Meta):
        fields = OrderListSerializer.Meta.fields + [
            "shipping_name",
            "shipping_phone",
            "shipping_address",
            "remark",
            "items",
            "updated_at",
        ]


class OrderCreateSerializer(serializers.Serializer):
    shipping_name = serializers.CharField(max_length=120)
    shipping_phone = serializers.CharField(max_length=32)
    shipping_address = serializers.CharField()
    remark = serializers.CharField(required=False, allow_blank=True)
