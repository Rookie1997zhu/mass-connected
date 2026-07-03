from django.db import transaction
from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.views import APIView

from apps.order.models import CartItem, Order, OrderItem
from apps.order.serializers import (
    CartItemCreateSerializer,
    CartItemSerializer,
    OrderCreateSerializer,
    OrderDetailSerializer,
    OrderListSerializer,
)
from apps.notification.services import notify_staff
from core.pagination import StandardPagination
from core.permissions import IsAdminRole, IsMemberRole
from core.responses import error_response, success_response


def get_lang(request):
    return request.query_params.get("lang") or request.headers.get("Accept-Language", "ko")[:2]


class MemberCartView(APIView):
    permission_classes = [IsMemberRole]

    def get(self, request):
        items = CartItem.objects.filter(member=request.user).select_related("product").prefetch_related("product__images")
        serializer = CartItemSerializer(items, many=True, context={"request": request, "lang": get_lang(request)})
        total = sum(item.unit_price_amount * item.quantity for item in items)
        return success_response({"items": serializer.data, "total_amount": total, "currency": "KRW"}, request=request)


class MemberCartItemView(APIView):
    permission_classes = [IsMemberRole]

    def post(self, request):
        serializer = CartItemCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        product = serializer.validated_data["product"]
        quantity = serializer.validated_data["quantity"]
        if product.stock < quantity:
            return error_response("PRODUCT_STOCK_INSUFFICIENT", "库存不足", request=request)
        item, created = CartItem.objects.get_or_create(
            member=request.user,
            product=product,
            defaults={"quantity": quantity, "unit_price_amount": product.price_amount},
        )
        if not created:
            item.quantity = quantity
            item.unit_price_amount = product.price_amount
            item.save(update_fields=["quantity", "unit_price_amount", "updated_at"])
        return success_response(
            CartItemSerializer(item, context={"request": request, "lang": get_lang(request)}).data,
            status=status.HTTP_201_CREATED if created else status.HTTP_200_OK,
            request=request,
        )

    def patch(self, request, pk):
        item = get_object_or_404(CartItem, pk=pk, member=request.user)
        quantity = request.data.get("quantity")
        if not quantity or int(quantity) < 1:
            return error_response("CART_QUANTITY_INVALID", "数量无效", request=request)
        if item.product.stock < int(quantity):
            return error_response("PRODUCT_STOCK_INSUFFICIENT", "库存不足", request=request)
        item.quantity = int(quantity)
        item.unit_price_amount = item.product.price_amount
        item.save(update_fields=["quantity", "unit_price_amount", "updated_at"])
        return success_response(
            CartItemSerializer(item, context={"request": request, "lang": get_lang(request)}).data,
            request=request,
        )

    def delete(self, request, pk):
        item = get_object_or_404(CartItem, pk=pk, member=request.user)
        item.delete()
        return success_response({}, message="已移除", request=request)


class MemberOrderListCreateView(APIView):
    permission_classes = [IsMemberRole]
    pagination_class = StandardPagination

    def get(self, request):
        qs = Order.objects.filter(member=request.user).prefetch_related("items").order_by("-created_at")
        paginator = self.pagination_class()
        page = paginator.paginate_queryset(qs, request)
        serializer = OrderListSerializer(page, many=True)
        return paginator.get_paginated_response(serializer.data)

    @transaction.atomic
    def post(self, request):
        cart_items = CartItem.objects.filter(member=request.user).select_related("product")
        if not cart_items.exists():
            return error_response("CART_EMPTY", "购物车为空", request=request)
        serializer = OrderCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        total = sum(item.unit_price_amount * item.quantity for item in cart_items)
        order = Order.objects.create(
            member=request.user,
            total_amount=total,
            currency="KRW",
            status="pending",
            **serializer.validated_data,
        )
        for item in cart_items:
            OrderItem.objects.create(
                order=order,
                product=item.product,
                product_name=item.product.name,
                quantity=item.quantity,
                unit_price_amount=item.unit_price_amount,
                line_total_amount=item.unit_price_amount * item.quantity,
            )
            item.product.stock = max(0, item.product.stock - item.quantity)
            item.product.save(update_fields=["stock", "updated_at"])
        cart_items.delete()
        notify_staff(
            "order",
            "新商城订单",
            f"订单 {order.order_no} 已创建，金额 {order.total_amount:,} {order.currency}。",
            related_type="order",
            related_id=order.id,
        )
        return success_response(
            OrderDetailSerializer(order, context={"lang": get_lang(request)}).data,
            message="订单已创建",
            status=status.HTTP_201_CREATED,
            request=request,
        )


class MemberOrderDetailView(APIView):
    permission_classes = [IsMemberRole]

    def get(self, request, pk):
        order = get_object_or_404(Order.objects.prefetch_related("items"), pk=pk, member=request.user)
        return success_response(
            OrderDetailSerializer(order, context={"lang": get_lang(request)}).data,
            request=request,
        )


class AdminOrderListView(APIView):
    permission_classes = [IsAdminRole]
    pagination_class = StandardPagination

    def get(self, request):
        qs = Order.objects.select_related("member").prefetch_related("items").order_by("-created_at")
        status_filter = request.query_params.get("status")
        if status_filter:
            qs = qs.filter(status=status_filter)
        paginator = self.pagination_class()
        page = paginator.paginate_queryset(qs, request)
        data = []
        for order in page:
            row = OrderListSerializer(order).data
            row["member_email"] = order.member.email
            row["member_name"] = order.member.name
            data.append(row)
        return paginator.get_paginated_response(data)


class AdminOrderDetailView(APIView):
    permission_classes = [IsAdminRole]

    def get(self, request, pk):
        order = get_object_or_404(Order.objects.select_related("member").prefetch_related("items"), pk=pk)
        payload = OrderDetailSerializer(order, context={"lang": get_lang(request)}).data
        payload["member_email"] = order.member.email
        payload["member_name"] = order.member.name
        return success_response(payload, request=request)

    def patch(self, request, pk):
        order = get_object_or_404(Order, pk=pk)
        new_status = request.data.get("status")
        valid = {choice[0] for choice in Order.STATUS_CHOICES}
        if new_status not in valid:
            return error_response("ORDER_STATUS_INVALID", "无效的状态", request=request)
        order.status = new_status
        order.save(update_fields=["status", "updated_at"])
        return success_response(
            OrderDetailSerializer(order, context={"lang": get_lang(request)}).data,
            request=request,
        )
