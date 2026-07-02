from django.urls import path

from apps.order.views import (
    AdminOrderDetailView,
    AdminOrderListView,
    MemberCartItemView,
    MemberCartView,
    MemberOrderDetailView,
    MemberOrderListCreateView,
)

urlpatterns = [
    path("member/cart", MemberCartView.as_view()),
    path("member/cart/items", MemberCartItemView.as_view()),
    path("member/cart/items/<int:pk>", MemberCartItemView.as_view()),
    path("member/orders", MemberOrderListCreateView.as_view()),
    path("member/orders/<int:pk>", MemberOrderDetailView.as_view()),
    path("admin/orders", AdminOrderListView.as_view()),
    path("admin/orders/<int:pk>", AdminOrderDetailView.as_view()),
]
