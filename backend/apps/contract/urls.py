from django.urls import path

from apps.contract.views import (
    AdminContractListView,
    MemberContractDetailView,
    MemberContractListView,
    MemberContractSignView,
    SupplierContractDetailView,
    SupplierContractListView,
)

urlpatterns = [
    path("member/contracts", MemberContractListView.as_view()),
    path("member/contracts/<int:pk>", MemberContractDetailView.as_view()),
    path("member/contracts/<int:pk>/sign", MemberContractSignView.as_view()),
    path("supplier/contracts", SupplierContractListView.as_view()),
    path("supplier/contracts/<int:pk>", SupplierContractDetailView.as_view()),
    path("admin/contracts", AdminContractListView.as_view()),
]
