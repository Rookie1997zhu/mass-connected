from django.urls import path

from apps.inquiry.views import AdminInquiryDetailView, AdminInquiryListView, PublicInquiryCreateView

urlpatterns = [
    path("public/inquiries", PublicInquiryCreateView.as_view()),
    path("admin/inquiries", AdminInquiryListView.as_view()),
    path("admin/inquiries/<int:pk>", AdminInquiryDetailView.as_view()),
]
