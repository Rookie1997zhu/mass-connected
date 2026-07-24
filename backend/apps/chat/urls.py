from django.urls import path

from apps.chat.views import (
    AdminConversationMessagesView,
    AdminDisputeListView,
    AdminDisputeResolveView,
    AdminMessageTranslateView,
    MemberChatUnreadCountView,
    MemberConversationListCreateView,
    MemberConversationReadView,
    MemberDisputeOpenView,
    MemberDisputeResolveView,
    MemberMessageListCreateView,
    MemberMessageTranslateView,
    SupplierChatUnreadCountView,
    SupplierConversationListCreateView,
    SupplierConversationReadView,
    SupplierDisputeOpenView,
    SupplierDisputeResolveView,
    SupplierMessageListCreateView,
    SupplierMessageTranslateView,
)

urlpatterns = [
    path("member/chat/conversations", MemberConversationListCreateView.as_view()),
    path("member/chat/conversations/<int:pk>/messages", MemberMessageListCreateView.as_view()),
    path(
        "member/chat/conversations/<int:pk>/messages/<int:message_id>/translate",
        MemberMessageTranslateView.as_view(),
    ),
    path("member/chat/conversations/<int:pk>/read", MemberConversationReadView.as_view()),
    path("member/chat/conversations/<int:pk>/dispute/open", MemberDisputeOpenView.as_view()),
    path("member/chat/conversations/<int:pk>/dispute/resolve", MemberDisputeResolveView.as_view()),
    path("member/chat/unread-count", MemberChatUnreadCountView.as_view()),
    path("supplier/chat/conversations", SupplierConversationListCreateView.as_view()),
    path("supplier/chat/conversations/<int:pk>/messages", SupplierMessageListCreateView.as_view()),
    path(
        "supplier/chat/conversations/<int:pk>/messages/<int:message_id>/translate",
        SupplierMessageTranslateView.as_view(),
    ),
    path("supplier/chat/conversations/<int:pk>/read", SupplierConversationReadView.as_view()),
    path("supplier/chat/conversations/<int:pk>/dispute/open", SupplierDisputeOpenView.as_view()),
    path("supplier/chat/conversations/<int:pk>/dispute/resolve", SupplierDisputeResolveView.as_view()),
    path("supplier/chat/unread-count", SupplierChatUnreadCountView.as_view()),
    path("admin/chat/disputes", AdminDisputeListView.as_view()),
    path("admin/chat/conversations/<int:pk>/messages", AdminConversationMessagesView.as_view()),
    path(
        "admin/chat/conversations/<int:pk>/messages/<int:message_id>/translate",
        AdminMessageTranslateView.as_view(),
    ),
    path("admin/chat/conversations/<int:pk>/dispute/resolve", AdminDisputeResolveView.as_view()),
]
