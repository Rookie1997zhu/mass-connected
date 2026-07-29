from django.urls import path

from apps.payment.views import (
    AdminPaymentConfirmView,
    AdminPaymentListView,
    AdminPaymentProofDownloadView,
    MemberPaymentDetailView,
    MemberPaymentListView,
    MemberPaymentProofDownloadView,
    MemberPaymentProofView,
    SupplierPaymentConfirmView,
    SupplierPaymentProofDownloadView,
)

urlpatterns = [
    path("member/payments", MemberPaymentListView.as_view()),
    path("member/payments/<int:pk>", MemberPaymentDetailView.as_view()),
    path("member/payments/<int:pk>/proof", MemberPaymentProofView.as_view()),
    path("member/payments/<int:pk>/proof/download", MemberPaymentProofDownloadView.as_view()),
    path("supplier/payments/<int:pk>/confirm", SupplierPaymentConfirmView.as_view()),
    path(
        "supplier/payments/<int:pk>/proof/download",
        SupplierPaymentProofDownloadView.as_view(),
    ),
    path("admin/payments", AdminPaymentListView.as_view()),
    path("admin/payments/<int:pk>/confirm", AdminPaymentConfirmView.as_view()),
    path("admin/payments/<int:pk>/proof/download", AdminPaymentProofDownloadView.as_view()),
]
