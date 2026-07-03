from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework.views import APIView

from apps.contract.models import Contract
from apps.contract.serializers import AdminContractSerializer, ContractSerializer
from core.pagination import StandardPagination
from core.permissions import IsAdminRole, IsBuyerRole, IsSupplierRole
from core.responses import error_response, success_response


class MemberContractListView(APIView):
    permission_classes = [IsBuyerRole]
    pagination_class = StandardPagination

    def get(self, request):
        qs = Contract.objects.filter(buyer=request.user).order_by("-created_at")
        paginator = self.pagination_class()
        page = paginator.paginate_queryset(qs, request)
        return paginator.get_paginated_response(
            ContractSerializer(page, many=True, context={"request": request}).data
        )


class MemberContractDetailView(APIView):
    permission_classes = [IsBuyerRole]

    def get(self, request, pk):
        contract = get_object_or_404(Contract, pk=pk, buyer=request.user)
        return success_response(
            ContractSerializer(contract, context={"request": request}).data, request=request
        )


class MemberContractSignView(APIView):
    """会员确认签署合同。"""

    permission_classes = [IsBuyerRole]

    def post(self, request, pk):
        contract = get_object_or_404(Contract, pk=pk, buyer=request.user)
        if contract.status != "pending_sign":
            return error_response("CONTRACT_STATUS_INVALID", "当前状态不可签署", request=request)
        contract.status = "signed"
        contract.signed_at = timezone.now()
        contract.save(update_fields=["status", "signed_at", "updated_at"])
        return success_response(
            ContractSerializer(contract, context={"request": request}).data,
            message="合同已签署",
            request=request,
        )


class SupplierContractListView(APIView):
    permission_classes = [IsSupplierRole]
    pagination_class = StandardPagination

    def get(self, request):
        qs = Contract.objects.filter(supplier=request.user).order_by("-created_at")
        paginator = self.pagination_class()
        page = paginator.paginate_queryset(qs, request)
        return paginator.get_paginated_response(
            ContractSerializer(page, many=True, context={"request": request}).data
        )


class SupplierContractDetailView(APIView):
    permission_classes = [IsSupplierRole]

    def get(self, request, pk):
        contract = get_object_or_404(Contract, pk=pk, supplier=request.user)
        return success_response(
            ContractSerializer(contract, context={"request": request}).data, request=request
        )


class AdminContractListView(APIView):
    permission_classes = [IsAdminRole]
    pagination_class = StandardPagination

    def get(self, request):
        qs = Contract.objects.select_related("buyer", "supplier").order_by("-created_at")
        status_filter = request.query_params.get("status")
        if status_filter:
            qs = qs.filter(status=status_filter)
        paginator = self.pagination_class()
        page = paginator.paginate_queryset(qs, request)
        return paginator.get_paginated_response(
            AdminContractSerializer(page, many=True, context={"request": request}).data
        )
