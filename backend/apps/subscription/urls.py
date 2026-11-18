from django.urls import path

from apps.subscription.views import (
    AdminPlanVersionDetailView,
    AdminPlanVersionListCreateView,
    AdminSubscriptionGrantView,
    AdminSubscriptionListView,
    AdminSubscriptionOrderConfirmView,
    AdminSubscriptionOrderListView,
    AdminUsageLedgerListView,
    MemberEntitlementsView,
    MemberSubscriptionOrderView,
    MemberUsageLedgerListView,
    PublicSubscriptionExplainView,
)

urlpatterns = [
    path("public/subscription/plans", PublicSubscriptionExplainView.as_view()),
    path("member/subscription/entitlements", MemberEntitlementsView.as_view()),
    path("member/subscription/ledgers", MemberUsageLedgerListView.as_view()),
    path("member/subscription/orders", MemberSubscriptionOrderView.as_view()),
    path("admin/subscription/plans", AdminPlanVersionListCreateView.as_view()),
    path("admin/subscription/plans/<int:pk>", AdminPlanVersionDetailView.as_view()),
    path("admin/subscription/grants", AdminSubscriptionGrantView.as_view()),
    path("admin/subscriptions", AdminSubscriptionListView.as_view()),
    path("admin/subscription/orders", AdminSubscriptionOrderListView.as_view()),
    path(
        "admin/subscription/orders/<int:pk>/confirm",
        AdminSubscriptionOrderConfirmView.as_view(),
    ),
    path("admin/subscription/ledgers", AdminUsageLedgerListView.as_view()),
]
