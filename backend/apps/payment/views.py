from django.http import FileResponse
from django.shortcuts import get_object_or_404
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.views import APIView

from apps.notification.services import notify_staff
from apps.payment.models import Payment
from apps.payment.serializers import AdminPaymentSerializer, PaymentSerializer
from apps.payment.services import PaymentConfirmError, confirm_payment
from core.file_validation import validate_upload_file
from core.pagination import StandardPagination
from core.permissions import IsAdminRole, IsBuyerRole, IsSupplierRole
from core.responses import error_response, success_response


def _proof_file_response(payment):
    if not payment.proof:
        return error_response("PAYMENT_PROOF_MISSING", "付款凭证不存在")
    name = (payment.proof.name or "").rsplit("/", 1)[-1] or "proof"
    return FileResponse(payment.proof.open("rb"), as_attachment=False, filename=name)


class MemberPaymentListView(APIView):
    permission_classes = [IsBuyerRole]
    pagination_class = StandardPagination

    def get(self, request):
        qs = Payment.objects.filter(buyer=request.user).select_related(
            "contract",
            "contract__rfq",
            "contract__quote",
            "contract__production_order",
            "contract__production_order__quote",
        ).order_by("-created_at")
        paginator = self.pagination_class()
        page = paginator.paginate_queryset(qs, request)
        return paginator.get_paginated_response(
            PaymentSerializer(page, many=True, context={"request": request}).data
        )


class MemberPaymentDetailView(APIView):
    permission_classes = [IsBuyerRole]

    def get(self, request, pk):
        payment = get_object_or_404(Payment, pk=pk, buyer=request.user)
        return success_response(
            PaymentSerializer(payment, context={"request": request}).data, request=request
        )


class MemberPaymentProofView(APIView):
    """会员上传付款凭证，进入待确认。"""

    permission_classes = [IsBuyerRole]
    parser_classes = [MultiPartParser, FormParser]

    def post(self, request, pk):
        payment = get_object_or_404(Payment, pk=pk, buyer=request.user)
        if payment.status == "confirmed":
            return error_response("PAYMENT_ALREADY_CONFIRMED", "该付款已确认", request=request)
        proof = request.FILES.get("proof")
        if proof:
            err_code, err_or_ext = validate_upload_file(proof)
            if err_code:
                return error_response(
                    "PAYMENT_PROOF_INVALID",
                    err_or_ext,
                    request=request,
                )
            # 付款凭证仅允许图片与 PDF
            if err_or_ext not in {"jpg", "jpeg", "png", "gif", "webp", "pdf"}:
                return error_response(
                    "PAYMENT_PROOF_INVALID",
                    "付款凭证仅支持图片或 PDF",
                    request=request,
                )
            payment.proof = proof
        payment.method = request.data.get("method", payment.method)
        payment.note = request.data.get("note", payment.note)
        payment.status = "pending_confirm"
        payment.save(update_fields=["proof", "method", "note", "status", "updated_at"])
        notify_staff(
            "payment",
            "付款凭证待审核",
            f"付款单 {payment.payment_no} 已提交凭证，请审核确认。",
            related_type="payment",
            related_id=payment.id,
        )
        return success_response(
            PaymentSerializer(payment, context={"request": request}).data,
            message="付款凭证已提交，等待确认",
            request=request,
        )


class MemberPaymentProofDownloadView(APIView):
    permission_classes = [IsBuyerRole]

    def get(self, request, pk):
        payment = get_object_or_404(Payment, pk=pk, buyer=request.user)
        return _proof_file_response(payment)


class AdminPaymentListView(APIView):
    permission_classes = [IsAdminRole]
    pagination_class = StandardPagination

    def get(self, request):
        qs = Payment.objects.select_related("buyer", "contract").order_by("-created_at")
        status_filter = request.query_params.get("status")
        if status_filter:
            qs = qs.filter(status=status_filter)
        paginator = self.pagination_class()
        page = paginator.paginate_queryset(qs, request)
        return paginator.get_paginated_response(
            AdminPaymentSerializer(page, many=True, context={"request": request}).data
        )


class AdminPaymentProofDownloadView(APIView):
    permission_classes = [IsAdminRole]

    def get(self, request, pk):
        payment = get_object_or_404(Payment, pk=pk)
        return _proof_file_response(payment)


class AdminPaymentConfirmView(APIView):
    """管理员确认付款，确认后签署合同并转为项目。"""

    permission_classes = [IsAdminRole]

    def post(self, request, pk):
        try:
            payment, project, already = confirm_payment(pk, actor=request.user, require_proof=False)
        except PaymentConfirmError as e:
            status_code = 404 if e.code == "PAYMENT_NOT_FOUND" else 400
            return error_response(e.code, e.message, status=status_code, request=request)

        data = AdminPaymentSerializer(payment, context={"request": request}).data
        if project:
            data["project_id"] = project.id
            data["project_no"] = project.project_no
        message = "付款已确认" if not already else "付款此前已确认"
        return success_response(data, message=message, request=request)


class SupplierPaymentConfirmView(APIView):
    """关联卖家确认收款：须已上传凭证且状态为 pending_confirm。"""

    permission_classes = [IsSupplierRole]

    def post(self, request, pk):
        payment = get_object_or_404(
            Payment.objects.select_related("contract"),
            pk=pk,
            contract__supplier=request.user,
        )
        try:
            payment, project, already = confirm_payment(
                payment.id, actor=request.user, require_proof=True
            )
        except PaymentConfirmError as e:
            return error_response(e.code, e.message, status=400, request=request)

        from apps.rfq.serializers import SupplierPaymentSummarySerializer

        data = SupplierPaymentSummarySerializer(
            payment,
            context={
                "request": request,
                "production_order": getattr(payment.contract, "production_order", None)
                if payment.contract_id
                else None,
            },
        ).data
        if project:
            data["project_id"] = project.id
            data["project_no"] = project.project_no
        message = "付款已确认，项目已启动" if not already else "付款此前已确认"
        return success_response(data, message=message, request=request)


class SupplierPaymentProofDownloadView(APIView):
    permission_classes = [IsSupplierRole]

    def get(self, request, pk):
        payment = get_object_or_404(
            Payment.objects.select_related("contract"),
            pk=pk,
            contract__supplier=request.user,
        )
        return _proof_file_response(payment)
