from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import status
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.views import APIView

from apps.notification.services import notify, notify_staff
from apps.payment.models import Payment
from apps.payment.serializers import AdminPaymentSerializer, PaymentSerializer
from apps.project.services import create_project_from_production_order
from core.pagination import StandardPagination
from core.permissions import IsAdminRole, IsBuyerRole
from core.responses import error_response, success_response


class MemberPaymentListView(APIView):
    permission_classes = [IsBuyerRole]
    pagination_class = StandardPagination

    def get(self, request):
        qs = Payment.objects.filter(buyer=request.user).order_by("-created_at")
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


class AdminPaymentConfirmView(APIView):
    """管理员确认付款，确认后签署合同并转为项目。"""

    permission_classes = [IsAdminRole]

    def post(self, request, pk):
        payment = get_object_or_404(Payment, pk=pk)
        if payment.status == "confirmed":
            return error_response("PAYMENT_ALREADY_CONFIRMED", "该付款已确认", request=request)
        payment.status = "confirmed"
        payment.confirmed_by = request.user
        payment.confirmed_at = timezone.now()
        payment.save(update_fields=["status", "confirmed_by", "confirmed_at", "updated_at"])

        contract = payment.contract
        project = None
        if contract:
            if contract.status != "signed":
                contract.status = "signed"
                contract.signed_at = timezone.now()
                contract.save(update_fields=["status", "signed_at", "updated_at"])
            if contract.production_order_id:
                project = create_project_from_production_order(contract.production_order)
        notify(payment.buyer, "payment", "付款已确认", f"付款单 {payment.payment_no} 已确认，项目将进入生产阶段。", send_email=True)
        if contract and contract.supplier_id:
            notify(
                contract.supplier,
                "payment",
                "客户付款已确认",
                f"付款单 {payment.payment_no} 已确认，合同 {contract.contract_no} 进入履约阶段。",
                related_type="payment",
                related_id=payment.id,
                send_email=True,
            )
        data = AdminPaymentSerializer(payment, context={"request": request}).data
        if project:
            data["project_id"] = project.id
            data["project_no"] = project.project_no
        return success_response(data, message="付款已确认", request=request)
