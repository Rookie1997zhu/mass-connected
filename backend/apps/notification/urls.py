from django.urls import path

from apps.notification.views import (
    AdminNotificationListView,
    AdminNotificationReadAllView,
    AdminNotificationReadView,
    AdminNotificationUnreadCountView,
    MemberNotificationListView,
    MemberNotificationReadAllView,
    MemberNotificationReadView,
    MemberNotificationUnreadCountView,
    SupplierNotificationListView,
    SupplierNotificationReadAllView,
    SupplierNotificationReadView,
    SupplierNotificationUnreadCountView,
)

urlpatterns = [
    path("member/notifications", MemberNotificationListView.as_view()),
    path("member/notifications/unread-count", MemberNotificationUnreadCountView.as_view()),
    path("member/notifications/read-all", MemberNotificationReadAllView.as_view()),
    path("member/notifications/<int:pk>/read", MemberNotificationReadView.as_view()),
    path("admin/notifications", AdminNotificationListView.as_view()),
    path("admin/notifications/unread-count", AdminNotificationUnreadCountView.as_view()),
    path("admin/notifications/read-all", AdminNotificationReadAllView.as_view()),
    path("admin/notifications/<int:pk>/read", AdminNotificationReadView.as_view()),
    path("supplier/notifications", SupplierNotificationListView.as_view()),
    path("supplier/notifications/unread-count", SupplierNotificationUnreadCountView.as_view()),
    path("supplier/notifications/read-all", SupplierNotificationReadAllView.as_view()),
    path("supplier/notifications/<int:pk>/read", SupplierNotificationReadView.as_view()),
]
