from django.urls import path

from apps.points.views import (
    AdminPointRuleDetailView,
    AdminPointRuleView,
    AdminRechargeOrderConfirmView,
    AdminRechargeOrderListView,
    AdminUserPointAdjustView,
    MemberPointTransactionListView,
    MemberPointWalletView,
    MemberRechargeOrderView,
)

urlpatterns = [
    path("member/points/wallet", MemberPointWalletView.as_view()),
    path("member/points/transactions", MemberPointTransactionListView.as_view()),
    path("member/points/recharge", MemberRechargeOrderView.as_view()),
    path("admin/points/rules", AdminPointRuleView.as_view()),
    path("admin/points/rules/<int:pk>", AdminPointRuleDetailView.as_view()),
    path("admin/points/users/<int:user_id>", AdminUserPointAdjustView.as_view()),
    path("admin/points/recharges", AdminRechargeOrderListView.as_view()),
    path("admin/points/recharges/<int:pk>/confirm", AdminRechargeOrderConfirmView.as_view()),
]
