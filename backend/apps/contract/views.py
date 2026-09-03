from django.core.files.base import ContentFile
from django.http import FileResponse
from django.shortcuts import get_object_or_404
from django.utils import timezone
from datetime import timedelta
from rest_framework import status
from rest_framework.views import APIView

from apps.contract.models import Contract, NdaSignature, NdaTemplate
from apps.contract.serializers import (
    AdminContractSerializer,
    ContractSerializer,
    ContractSignSerializer,
    NdaSignSerializer,
    NdaSignatureSerializer,
    NdaTemplateSerializer,
    SupplierContractSerializer,
)
from core.pagination import StandardPagination
from core.pdf import build_nda_pdf
from core.permissions import IsAdminRole, IsBuyerRole, IsSupplierRole
from core.responses import error_response, success_response
from core.storage_utils import local_file_path


def _contract_file_response(field_file, default_name):
    if not field_file:
        return error_response("CONTRACT_FILE_MISSING", "文件不存在")
    name = (field_file.name or "").rsplit("/", 1)[-1] or default_name
    return FileResponse(field_file.open("rb"), as_attachment=False, filename=name)


class MemberContractListView(APIView):
    permission_classes = [IsBuyerRole]
    pagination_class = StandardPagination

    def get(self, request):
        qs = Contract.objects.filter(buyer=request.user).select_related(
            "rfq", "quote", "production_order", "production_order__quote", "supplier"
        ).order_by("-created_at")
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
    """会员在线签署保密协议（必填签名图与主体信息）。"""

    permission_classes = [IsBuyerRole]

    def post(self, request, pk):
        contract = get_object_or_404(Contract, pk=pk, buyer=request.user)
        if contract.status != "pending_sign":
            return error_response("CONTRACT_STATUS_INVALID", "当前状态不可签署", request=request)

        serializer = ContractSignSerializer(data=request.data)
        if not serializer.is_valid():
            errors = serializer.errors
            if "agree" in errors:
                return error_response(
                    "CONTRACT_AGREE_REQUIRED",
                    "须同意保密协议条款",
                    errors=errors,
                    request=request,
                )
            if "signature_image" in errors:
                detail = errors.get("signature_image")
                detail_text = " ".join(str(x) for x in detail) if detail else ""
                if "required" in detail_text.lower() or "必填" in detail_text or not request.FILES.get(
                    "signature_image"
                ):
                    return error_response(
                        "CONTRACT_SIGNATURE_REQUIRED",
                        "请上传签名图片",
                        errors=errors,
                        request=request,
                    )
                return error_response(
                    "CONTRACT_SIGNATURE_INVALID",
                    "签名图片无效，请上传 JPG / PNG / WEBP",
                    errors=errors,
                    request=request,
                )
            return error_response(
                "VALIDATION_ERROR",
                "校验失败",
                errors=errors,
                request=request,
            )

        data = serializer.validated_data
        from apps.contract.services import build_contract_context, render_contract_pdf, render_template_body

        now = timezone.now()
        contract.company_name = data["company_name"].strip()
        contract.business_reg_no = data["business_reg_no"].strip()
        contract.company_address = data["company_address"].strip()
        contract.signer_name = data["signer_name"].strip()
        contract.signature_image = data["signature_image"]
        contract.agree_at = now
        contract.signed_at = now
        contract.status = "signed"

        template_body = contract.template.body if contract.template_id else None
        if not template_body:
            from apps.contract.services import DEFAULT_CONTRACT_BODY

            template_body = DEFAULT_CONTRACT_BODY
        contract.rendered_body = render_template_body(
            template_body,
            build_contract_context(
                contract,
                overrides={
                    "company_name": contract.company_name,
                    "business_reg_no": contract.business_reg_no,
                    "company_address": contract.company_address,
                    "signer_name": contract.signer_name,
                },
            ),
        )
        contract.terms = contract.rendered_body
        contract.save()

        with local_file_path(contract.signature_image) as signature_path:
            render_contract_pdf(contract, signature_path=signature_path)
        contract.save(update_fields=["pdf", "updated_at"])

        return success_response(
            ContractSerializer(contract, context={"request": request}).data,
            message="保密协议已签署",
            request=request,
        )


class SupplierContractListView(APIView):
    permission_classes = [IsSupplierRole]
    pagination_class = StandardPagination

    def get(self, request):
        qs = Contract.objects.filter(supplier=request.user).select_related(
            "rfq", "quote", "production_order", "production_order__quote", "supplier"
        ).order_by("-created_at")
        paginator = self.pagination_class()
        page = paginator.paginate_queryset(qs, request)
        return paginator.get_paginated_response(
            SupplierContractSerializer(page, many=True, context={"request": request}).data
        )


class SupplierContractDetailView(APIView):
    permission_classes = [IsSupplierRole]

    def get(self, request, pk):
        contract = get_object_or_404(Contract, pk=pk, supplier=request.user)
        return success_response(
            SupplierContractSerializer(contract, context={"request": request}).data, request=request
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


class MemberContractPdfDownloadView(APIView):
    permission_classes = [IsBuyerRole]

    def get(self, request, pk):
        contract = get_object_or_404(Contract, pk=pk, buyer=request.user)
        return _contract_file_response(contract.pdf, "contract.pdf")


class MemberContractSignatureDownloadView(APIView):
    permission_classes = [IsBuyerRole]

    def get(self, request, pk):
        contract = get_object_or_404(Contract, pk=pk, buyer=request.user)
        return _contract_file_response(contract.signature_image, "signature.png")


class SupplierContractPdfDownloadView(APIView):
    permission_classes = [IsSupplierRole]

    def get(self, request, pk):
        contract = get_object_or_404(Contract, pk=pk, supplier=request.user)
        return _contract_file_response(contract.pdf, "contract.pdf")


class SupplierContractSignatureDownloadView(APIView):
    permission_classes = [IsSupplierRole]

    def get(self, request, pk):
        contract = get_object_or_404(Contract, pk=pk, supplier=request.user)
        return _contract_file_response(contract.signature_image, "signature.png")


class AdminContractPdfDownloadView(APIView):
    permission_classes = [IsAdminRole]

    def get(self, request, pk):
        contract = get_object_or_404(Contract, pk=pk)
        return _contract_file_response(contract.pdf, "contract.pdf")


class AdminContractSignatureDownloadView(APIView):
    permission_classes = [IsAdminRole]

    def get(self, request, pk):
        contract = get_object_or_404(Contract, pk=pk)
        return _contract_file_response(contract.signature_image, "signature.png")


class MemberNdaPdfDownloadView(APIView):
    permission_classes = [IsBuyerRole]

    def get(self, request, pk):
        signature = get_object_or_404(NdaSignature, pk=pk, buyer=request.user)
        return _contract_file_response(signature.pdf, "nda.pdf")
