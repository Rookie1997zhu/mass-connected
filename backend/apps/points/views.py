from django.http import FileResponse
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import status
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.views import APIView

from apps.points.models import PointRule, PointTransaction, PointWallet, RechargeOrder
from apps.points.serializers import (
    AdminRechargeOrderSerializer,
    PointRuleSerializer,
    PointTransactionSerializer,
    PointWalletSerializer,
    RechargeOrderSerializer,
)
from apps.points.services import add_points, ensure_wallet
from apps.accounts.models import User
from apps.notification.services import notify
from core.pagination import StandardPagination
from core.permissions import IsAdminRole, IsBuyerRole
from core.responses import error_response, success_response

VAT_RATE = 10


def _recharge_proof_response(order):
    if not order.proof:
        return error_response("RECHARGE_PROOF_MISSING", "充值凭证不存在")
    name = (order.proof.name or "").rsplit("/", 1)[-1] or "proof"
    return FileResponse(order.proof.open("rb"), as_attachment=False, filename=name)


class MemberPointWalletView(APIView):
    permission_classes = [IsBuyerRole]

    def get(self, request):
        wallet = ensure_wallet(request.user)
        return success_response(PointWalletSerializer(wallet).data, request=request)


class MemberPointTransactionListView(APIView):
    permission_classes = [IsBuyerRole]
    pagination_class = StandardPagination

    def get(self, request):
        qs = PointTransaction.objects.filter(user=request.user).order_by("-created_at")
        ttype = request.query_params.get("type")
        if ttype:
            qs = qs.filter(type=ttype)
        paginator = self.pagination_class()
        page = paginator.paginate_queryset(qs, request)
        return paginator.get_paginated_response(PointTransactionSerializer(page, many=True).data)


class MemberRechargeOrderView(APIView):
    permission_classes = [IsBuyerRole]
    parser_classes = [MultiPartParser, FormParser]
    pagination_class = StandardPagination

    def get(self, request):
        qs = RechargeOrder.objects.filter(user=request.user).order_by("-created_at")
        paginator = self.pagination_class()
        page = paginator.paginate_queryset(qs, request)
        return paginator.get_paginated_response(
            RechargeOrderSerializer(page, many=True, context={"request": request}).data
        )

    def post(self, request):
        try:
            amount_krw = int(request.data.get("amount_krw", 0))
        except (TypeError, ValueError):
            amount_krw = 0
        if amount_krw < 1000:
            return error_response(
                "RECHARGE_AMOUNT_INVALID",
                "充值金额至少 1,000 KRW",
                request=request,
            )
        vat_amount = round(amount_krw * VAT_RATE / 100)
        order = RechargeOrder.objects.create(
            recharge_no=RechargeOrder.generate_no(),
            user=request.user,
            amount_krw=amount_krw,
            vat_amount=vat_amount,
            total_pay_amount=amount_krw + vat_amount,
            point_amount=amount_krw,
            payment_method=request.data.get("payment_method", ""),
            proof=request.FILES.get("proof"),
            status="pending_confirm",
        )
        return success_response(
            RechargeOrderSerializer(order, context={"request": request}).data,
            message="充值申请已提交，等待管理员确认",
            status=status.HTTP_201_CREATED,
            request=request,
        )


class AdminPointRuleView(APIView):
    permission_classes = [IsAdminRole]

    def get(self, request):
        qs = PointRule.objects.all()
        return success_response({"items": PointRuleSerializer(qs, many=True).data}, request=request)

    def post(self, request):
        serializer = PointRuleSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return success_response(serializer.data, status=status.HTTP_201_CREATED, request=request)


class AdminPointRuleDetailView(APIView):
    permission_classes = [IsAdminRole]

    def patch(self, request, pk):
        rule = get_object_or_404(PointRule, pk=pk)
        serializer = PointRuleSerializer(rule, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return success_response(serializer.data, request=request)


class AdminUserPointAdjustView(APIView):
    permission_classes = [IsAdminRole]

    def get(self, request, user_id):
        user = get_object_or_404(User, pk=user_id)
        wallet = ensure_wallet(user)
        txns = PointTransaction.objects.filter(user=user).order_by("-created_at")[:50]
        return success_response(
            {
                "wallet": PointWalletSerializer(wallet).data,
                "transactions": PointTransactionSerializer(txns, many=True).data,
            },
            request=request,
        )

    def post(self, request, user_id):
        user = get_object_or_404(User, pk=user_id)
        try:
            amount = int(request.data.get("amount", 0))
        except (TypeError, ValueError):
            amount = 0
        if amount == 0:
            return error_response("POINT_AMOUNT_INVALID", "调整积分不能为 0", request=request)
        description = request.data.get("description", "管理员手动调整")
        txn = add_points(
            user,
            amount,
            "adjust",
            source_type="admin_adjust",
            description=description,
            admin=request.user,
        )
        notify(user, "point", "积分变动", f"{description}：{amount:+d} 积分")
        return success_response(PointTransactionSerializer(txn).data, request=request)


class AdminRechargeOrderListView(APIView):
    permission_classes = [IsAdminRole]
    pagination_class = StandardPagination

    def get(self, request):
        qs = RechargeOrder.objects.select_related("user").order_by("-created_at")
        status_filter = request.query_params.get("status")
        if status_filter:
            qs = qs.filter(status=status_filter)
        paginator = self.pagination_class()
        page = paginator.paginate_queryset(qs, request)
        return paginator.get_paginated_response(
            AdminRechargeOrderSerializer(page, many=True, context={"request": request}).data
        )


class AdminRechargeOrderConfirmView(APIView):
    permission_classes = [IsAdminRole]

    def post(self, request, pk):
        order = get_object_or_404(RechargeOrder, pk=pk)
        if order.status == "confirmed":
            return error_response("RECHARGE_ALREADY_CONFIRMED", "该充值已确认", request=request)
        order.status = "confirmed"
        order.confirmed_by = request.user
        order.confirmed_at = timezone.now()
        order.save(update_fields=["status", "confirmed_by", "confirmed_at"])
        add_points(
            order.user,
            order.point_amount,
            "recharge",
            source_type="recharge",
            source_id=order.id,
            description=f"充值到账 {order.recharge_no}",
            admin=request.user,
        )
        notify(order.user, "point", "积分充值已到账", f"充值单 {order.recharge_no} 已确认，{order.point_amount} 积分到账。")
        return success_response(
            AdminRechargeOrderSerializer(order, context={"request": request}).data,
            request=request,
        )


class MemberRechargeProofDownloadView(APIView):
    permission_classes = [IsBuyerRole]

    def get(self, request, pk):
        order = get_object_or_404(RechargeOrder, pk=pk, user=request.user)
        return _recharge_proof_response(order)


class AdminRechargeProofDownloadView(APIView):
    permission_classes = [IsAdminRole]

    def get(self, request, pk):
        order = get_object_or_404(RechargeOrder, pk=pk)
        return _recharge_proof_response(order)
