from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import status
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.permissions import AllowAny
from rest_framework.views import APIView

from apps.accounts.models import User
from apps.subscription.models import (
    PlanVersion,
    Subscription,
    SubscriptionOrder,
    UsageLedger,
)
from apps.subscription.serializers import (
    PlanVersionSerializer,
    SubscriptionOrderSerializer,
    SubscriptionSerializer,
    UsageLedgerSerializer,
)
from apps.subscription.services import (
    activate_subscription,
    confirm_subscription_order,
    entitlements_summary,
)
from core.pagination import StandardPagination
from core.permissions import IsAdminRole, IsMemberOrFactoryRole
from core.responses import error_response, success_response


class PublicSubscriptionExplainView(APIView):
    """订阅说明：仅返回已发布方案的非价格营销字段；未定价不暴露购买价。"""

    authentication_classes = []
    permission_classes = [AllowAny]

    def get(self, request):
        qs = PlanVersion.objects.filter(status=PlanVersion.STATUS_PUBLISHED).order_by("code", "-id")
        items = []
        for p in qs:
            row = {
                "id": p.id,
                "code": p.code,
                "name": p.name,
                "billing_period": p.billing_period,
                "description": p.description,
                "features_json": p.features_json or {},
                "is_orderable": p.is_orderable,
            }
            # 仅已确认定价时暴露价格
            if p.is_orderable:
                row["price_amount"] = p.price_amount
                row["currency"] = p.currency
            items.append(row)
        return success_response(
            {
                "items": items,
                "note": "价格未确认的方案仅展示能力说明，不提供购买价或成功态。",
            },
            request=request,
        )


class MemberEntitlementsView(APIView):
    permission_classes = [IsMemberOrFactoryRole]

    def get(self, request):
        return success_response(entitlements_summary(request.user), request=request)


class MemberUsageLedgerListView(APIView):
    permission_classes = [IsMemberOrFactoryRole]
    pagination_class = StandardPagination

    def get(self, request):
        qs = UsageLedger.objects.filter(user=request.user).order_by("-created_at")
        feature = request.query_params.get("feature_code")
        if feature:
            qs = qs.filter(feature_code=feature)
        paginator = self.pagination_class()
        page = paginator.paginate_queryset(qs, request)
        return paginator.get_paginated_response(UsageLedgerSerializer(page, many=True).data)


class MemberSubscriptionOrderView(APIView):
    permission_classes = [IsMemberOrFactoryRole]
    parser_classes = [MultiPartParser, FormParser]
    pagination_class = StandardPagination

    def get(self, request):
        qs = SubscriptionOrder.objects.filter(user=request.user).select_related("plan_version")
        paginator = self.pagination_class()
        page = paginator.paginate_queryset(qs, request)
        return paginator.get_paginated_response(
            SubscriptionOrderSerializer(page, many=True, context={"request": request}).data
        )

    def post(self, request):
        plan_id = request.data.get("plan_version_id") or request.data.get("plan_id")
        plan = PlanVersion.objects.filter(pk=plan_id).first()
        if not plan:
            return error_response("SUBSCRIPTION_PLAN_NOT_FOUND", "方案不存在", request=request)
        if not plan.is_orderable:
            return error_response(
                "SUBSCRIPTION_PLAN_NOT_ORDERABLE",
                "该方案未开放自助开通（未发布或未定价），请联系运营",
                request=request,
            )
        pending = SubscriptionOrder.objects.filter(
            user=request.user,
            plan_version=plan,
            status=SubscriptionOrder.STATUS_PENDING,
        ).exists()
        if pending:
            return error_response(
                "SUBSCRIPTION_ORDER_PENDING",
                "已有待核对的开通申请",
                request=request,
            )
        order = SubscriptionOrder.objects.create(
            order_no=SubscriptionOrder.generate_no(),
            user=request.user,
            plan_version=plan,
            status=SubscriptionOrder.STATUS_PENDING,
            price_amount=plan.price_amount,
            currency=plan.currency or "KRW",
            proof=request.FILES.get("proof"),
            note=(request.data.get("note") or "")[:255],
        )
        return success_response(
            SubscriptionOrderSerializer(order, context={"request": request}).data,
            message="开通申请已提交，等待管理员核对",
            status=status.HTTP_201_CREATED,
            request=request,
        )


class AdminPlanVersionListCreateView(APIView):
    permission_classes = [IsAdminRole]

    def get(self, request):
        qs = PlanVersion.objects.all()
        st = request.query_params.get("status")
        if st:
            qs = qs.filter(status=st)
        return success_response(
            {"items": PlanVersionSerializer(qs, many=True).data},
            request=request,
        )

    def post(self, request):
        serializer = PlanVersionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        plan = serializer.save()
        return success_response(
            PlanVersionSerializer(plan).data,
            status=status.HTTP_201_CREATED,
            request=request,
        )


class AdminPlanVersionDetailView(APIView):
    permission_classes = [IsAdminRole]

    def patch(self, request, pk):
        plan = get_object_or_404(PlanVersion, pk=pk)
        serializer = PlanVersionSerializer(plan, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        plan = serializer.save()
        if plan.status == PlanVersion.STATUS_PUBLISHED and not plan.published_at:
            plan.published_at = timezone.now()
            plan.save(update_fields=["published_at", "updated_at"])
        return success_response(PlanVersionSerializer(plan).data, request=request)


class AdminSubscriptionGrantView(APIView):
    """手动为用户开通订阅。"""

    permission_classes = [IsAdminRole]

    def post(self, request):
        user_id = request.data.get("user_id")
        plan_id = request.data.get("plan_version_id") or request.data.get("plan_id")
        user = User.objects.filter(pk=user_id).first()
        plan = PlanVersion.objects.filter(pk=plan_id).first()
        if not user:
            return error_response("SUBSCRIPTION_USER_NOT_FOUND", "用户不存在", request=request)
        if not plan:
            return error_response("SUBSCRIPTION_PLAN_NOT_FOUND", "方案不存在", request=request)
        sub = activate_subscription(
            user=user,
            plan_version=plan,
            source=Subscription.SOURCE_ADMIN_GRANT,
            granted_by=request.user,
            note=(request.data.get("note") or "")[:255],
        )
        return success_response(
            SubscriptionSerializer(sub).data,
            status=status.HTTP_201_CREATED,
            request=request,
        )


class AdminSubscriptionListView(APIView):
    permission_classes = [IsAdminRole]
    pagination_class = StandardPagination

    def get(self, request):
        qs = Subscription.objects.select_related("plan_version", "user").prefetch_related(
            "entitlements"
        )
        user_id = request.query_params.get("user_id")
        st = request.query_params.get("status")
        if user_id:
            qs = qs.filter(user_id=user_id)
        if st:
            qs = qs.filter(status=st)
        paginator = self.pagination_class()
        page = paginator.paginate_queryset(qs, request)
        return paginator.get_paginated_response(SubscriptionSerializer(page, many=True).data)


class AdminSubscriptionOrderListView(APIView):
    permission_classes = [IsAdminRole]
    pagination_class = StandardPagination

    def get(self, request):
        qs = SubscriptionOrder.objects.select_related("plan_version", "user")
        st = request.query_params.get("status")
        if st:
            qs = qs.filter(status=st)
        paginator = self.pagination_class()
        page = paginator.paginate_queryset(qs, request)
        return paginator.get_paginated_response(
            SubscriptionOrderSerializer(page, many=True, context={"request": request}).data
        )


class AdminSubscriptionOrderConfirmView(APIView):
    permission_classes = [IsAdminRole]

    def post(self, request, pk):
        order = get_object_or_404(SubscriptionOrder, pk=pk)
        order = confirm_subscription_order(order, request.user)
        return success_response(
            SubscriptionOrderSerializer(order, context={"request": request}).data,
            request=request,
        )


class AdminUsageLedgerListView(APIView):
    permission_classes = [IsAdminRole]
    pagination_class = StandardPagination

    def get(self, request):
        qs = UsageLedger.objects.select_related("user", "subscription")
        user_id = request.query_params.get("user_id")
        feature = request.query_params.get("feature_code")
        if user_id:
            qs = qs.filter(user_id=user_id)
        if feature:
            qs = qs.filter(feature_code=feature)
        paginator = self.pagination_class()
        page = paginator.paginate_queryset(qs, request)
        return paginator.get_paginated_response(UsageLedgerSerializer(page, many=True).data)
