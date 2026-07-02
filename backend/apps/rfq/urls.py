from django.urls import path

from apps.rfq.views import (
    AdminQuoteDetailView,
    AdminRFQDetailView,
    AdminRFQListView,
    AdminRFQQuoteCreateView,
    AdminRFQStatusView,
    AdminServiceCategoryDetailView,
    AdminServiceCategoryListCreateView,
    FactoryQuoteListView,
    FactoryRFQDetailView,
    FactoryRFQListView,
    FactoryRFQQuoteCreateView,
    MemberQuoteAcceptView,
    MemberRFQAttachmentView,
    MemberRFQDetailView,
    MemberRFQListCreateView,
    PublicServiceCategoryListView,
)

urlpatterns = [
    path("public/service-categories", PublicServiceCategoryListView.as_view()),
    path("member/rfqs", MemberRFQListCreateView.as_view()),
    path("member/rfqs/<int:pk>", MemberRFQDetailView.as_view()),
    path("member/rfqs/<int:pk>/attachments", MemberRFQAttachmentView.as_view()),
    path("member/rfqs/<int:pk>/quotes/<int:quote_id>/accept", MemberQuoteAcceptView.as_view()),
    path("factory/rfqs", FactoryRFQListView.as_view()),
    path("factory/rfqs/<int:pk>", FactoryRFQDetailView.as_view()),
    path("factory/rfqs/<int:pk>/quotes", FactoryRFQQuoteCreateView.as_view()),
    path("factory/quotes", FactoryQuoteListView.as_view()),
    path("admin/service-categories", AdminServiceCategoryListCreateView.as_view()),
    path("admin/service-categories/<int:pk>", AdminServiceCategoryDetailView.as_view()),
    path("admin/rfqs", AdminRFQListView.as_view()),
    path("admin/rfqs/<int:pk>", AdminRFQDetailView.as_view()),
    path("admin/rfqs/<int:pk>/status", AdminRFQStatusView.as_view()),
    path("admin/rfqs/<int:pk>/quotes", AdminRFQQuoteCreateView.as_view()),
    path("admin/quotes/<int:pk>", AdminQuoteDetailView.as_view()),
]
