from django.urls import path

from apps.contract.views import (
    AdminContractListView,
    AdminContractPdfDownloadView,
    AdminContractSignatureDownloadView,
    MemberContractDetailView,
    MemberContractListView,
    MemberContractPdfDownloadView,
    MemberContractSignView,
    MemberContractSignatureDownloadView,
    MemberNdaListView,
    MemberNdaPdfDownloadView,
    MemberNdaSignView,
    MemberNdaTemplateView,
    SupplierContractDetailView,
    SupplierContractListView,
    SupplierContractPdfDownloadView,
    SupplierContractSignatureDownloadView,
)

urlpatterns = [
    path("member/contracts", MemberContractListView.as_view()),
    path("member/contracts/<int:pk>", MemberContractDetailView.as_view()),
    path("member/contracts/<int:pk>/sign", MemberContractSignView.as_view()),
    path("member/contracts/<int:pk>/pdf/download", MemberContractPdfDownloadView.as_view()),
    path(
        "member/contracts/<int:pk>/signature/download",
        MemberContractSignatureDownloadView.as_view(),
    ),
    path("member/nda/template", MemberNdaTemplateView.as_view()),
    path("member/nda", MemberNdaListView.as_view()),
    path("member/nda/sign", MemberNdaSignView.as_view()),
    path("member/nda/<int:pk>/pdf/download", MemberNdaPdfDownloadView.as_view()),
    path("supplier/contracts", SupplierContractListView.as_view()),
    path("supplier/contracts/<int:pk>", SupplierContractDetailView.as_view()),
    path(
        "supplier/contracts/<int:pk>/pdf/download",
        SupplierContractPdfDownloadView.as_view(),
    ),
    path(
        "supplier/contracts/<int:pk>/signature/download",
        SupplierContractSignatureDownloadView.as_view(),
    ),
    path("admin/contracts", AdminContractListView.as_view()),
    path("admin/contracts/<int:pk>/pdf/download", AdminContractPdfDownloadView.as_view()),
    path(
        "admin/contracts/<int:pk>/signature/download",
        AdminContractSignatureDownloadView.as_view(),
    ),
]
