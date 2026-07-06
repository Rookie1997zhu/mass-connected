from django.core.files.base import ContentFile
from django.shortcuts import get_object_or_404
from django.utils import timezone
from datetime import timedelta
from rest_framework import status
from rest_framework.views import APIView

from apps.contract.models import Contract, NdaSignature, NdaTemplate
from apps.contract.serializers import (
    AdminContractSerializer,
    ContractSerializer,
    NdaSignSerializer,
    NdaSignatureSerializer,
    NdaTemplateSerializer,
)
from core.pagination import StandardPagination
from core.pdf import build_nda_pdf
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


def _buyer_company_name(user, override=""):
    if override:
        return override.strip()
    profile = getattr(user, "factory_profile", None)
    if profile and profile.company_name:
        return profile.company_name
    return user.name or user.email


class MemberNdaTemplateView(APIView):
    permission_classes = [IsBuyerRole]

    def get(self, request):
        template = NdaTemplate.objects.filter(is_active=True).order_by("-effective_date", "-id").first()
        if not template:
            return error_response("NDA_TEMPLATE_MISSING", "暂无可用保密协议模板", request=request)
        company = _buyer_company_name(request.user)
        body = template.body.replace("（客户公司名称）", company).replace("{{company_name}}", company)
        return success_response(
            {
                "template": NdaTemplateSerializer(template).data,
                "rendered_body": body,
                "company_name": company,
            },
            request=request,
        )


class MemberNdaListView(APIView):
    permission_classes = [IsBuyerRole]
    pagination_class = StandardPagination

    def get(self, request):
        qs = NdaSignature.objects.filter(buyer=request.user).select_related("template").order_by("-created_at")
        paginator = self.pagination_class()
        page = paginator.paginate_queryset(qs, request)
        return paginator.get_paginated_response(
            NdaSignatureSerializer(page, many=True, context={"request": request}).data
        )


class MemberNdaSignView(APIView):
    permission_classes = [IsBuyerRole]

    def post(self, request):
        serializer = NdaSignSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        template = NdaTemplate.objects.filter(is_active=True).order_by("-effective_date", "-id").first()
        if not template:
            return error_response("NDA_TEMPLATE_MISSING", "暂无可用保密协议模板", request=request)

        company = _buyer_company_name(request.user, serializer.validated_data.get("company_name", ""))
        if not company:
            return error_response("NDA_COMPANY_REQUIRED", "请填写客户公司名称", request=request)

        signed_at = timezone.now()
        retention_delete_at = signed_at + timedelta(days=365)
        body = template.body.replace("（客户公司名称）", company).replace("{{company_name}}", company)
        pdf_bytes = build_nda_pdf(
            title=template.title,
            version=template.version,
            company_name=company,
            body=body,
            signed_at=signed_at.strftime("%Y-%m-%d %H:%M"),
        )
        signature = NdaSignature.objects.create(
            buyer=request.user,
            template=template,
            company_name=company,
            status="signed",
            signed_at=signed_at,
            retention_delete_at=retention_delete_at,
        )
        signature.pdf.save(f"nda-{signature.id}.pdf", ContentFile(pdf_bytes), save=False)
        signature.save(update_fields=["pdf", "updated_at"])
        return success_response(
            NdaSignatureSerializer(signature, context={"request": request}).data,
            message="保密协议已签署",
            status=status.HTTP_201_CREATED,
            request=request,
        )
