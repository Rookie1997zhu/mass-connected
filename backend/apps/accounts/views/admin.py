from django.contrib.auth import authenticate
from django.http import FileResponse
from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.permissions import AllowAny
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView

from apps.accounts.models import FactoryProfile, SupplierAttachment, SupplierTag, User
from apps.accounts.serializers import (
    AdminFactorySerializer,
    AdminMemberSerializer,
    AdminSupplierCreateSerializer,
    AdminSupplierUpdateSerializer,
    AdminUserSerializer,
    SupplierAttachmentSerializer,
    SupplierTagSerializer,
    UserSerializer,
)
from apps.accounts.views._helpers import _auth_success_with_refresh_cookie, issue_tokens
from core.exceptions import AppAPIException
from core.file_validation import validate_upload_file
from core.pagination import StandardPagination
from core.permissions import IsAdminRole
from core.responses import error_response, success_response


class AdminLoginView(APIView):
    permission_classes = [AllowAny]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "login"

    def post(self, request):
        email = request.data.get("email")
        password = request.data.get("password")
        user = authenticate(request, username=email, password=password)
        if not user or user.role not in {"super_admin", "operator", "sales"}:
            return error_response(
                "AUTH_CREDENTIALS_INVALID",
                "账号或密码错误",
                status=status.HTTP_401_UNAUTHORIZED,
                request=request,
            )
        tokens = issue_tokens(user)
        return _auth_success_with_refresh_cookie(
            request,
            {"user": UserSerializer(user).data, "tokens": tokens},
            kind="admin",
        )


class AdminSupplierLicenseDownloadView(APIView):
    permission_classes = [IsAdminRole]

    def get(self, request, pk):
        profile = get_object_or_404(FactoryProfile, pk=pk)
        if not profile.business_license:
            return error_response("SUPPLIER_LICENSE_MISSING", "营业执照不存在", request=request)
        name = (profile.business_license.name or "").rsplit("/", 1)[-1] or "license"
        return FileResponse(
            profile.business_license.open("rb"), as_attachment=False, filename=name
        )


class AdminSupplierAttachmentDownloadView(APIView):
    permission_classes = [IsAdminRole]

    def get(self, request, pk, file_id):
        profile = get_object_or_404(FactoryProfile, pk=pk, user__role="factory")
        att = get_object_or_404(SupplierAttachment, pk=file_id, profile=profile)
        if not att.file:
            return error_response("SUPPLIER_ATTACHMENT_MISSING", "文件不存在", request=request)
        return FileResponse(att.file.open("rb"), as_attachment=False, filename=att.file_name)


class AdminSupplierListCreateView(APIView):
    """管理员管理供应商账号（role=factory）。"""

    permission_classes = [IsAdminRole]

    def get(self, request):
        qs = (
            FactoryProfile.objects.select_related("user")
            .filter(user__role="factory")
            .prefetch_related("processes", "tags", "attachments")
        )
        status_filter = request.query_params.get("status")
        if status_filter:
            qs = qs.filter(status=status_filter)
        tag_filter = request.query_params.get("tag")
        if tag_filter:
            qs = qs.filter(tags__tag_name=tag_filter).distinct()
        return success_response(
            {"items": AdminFactorySerializer(qs, many=True, context={"request": request}).data},
            request=request,
        )

    def post(self, request):
        serializer = AdminSupplierCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        return success_response(
            AdminFactorySerializer(user.factory_profile).data,
            message="供应商账号已创建",
            status=status.HTTP_201_CREATED,
            request=request,
        )


class AdminMemberListView(APIView):
    """管理员查看买家会员列表（含积分余额）。"""

    permission_classes = [IsAdminRole]
    pagination_class = StandardPagination

    def get(self, request):
        qs = User.objects.filter(role="member").order_by("-created_at")
        search = (request.query_params.get("search") or "").strip()
        if search:
            from django.db.models import Q

            qs = qs.filter(Q(email__icontains=search) | Q(name__icontains=search))
        paginator = self.pagination_class()
        page = paginator.paginate_queryset(qs, request)
        return paginator.get_paginated_response(AdminMemberSerializer(page, many=True).data)


class AdminSupplierDetailView(APIView):
    permission_classes = [IsAdminRole]

    def get(self, request, pk):
        profile = get_object_or_404(
            FactoryProfile.objects.select_related("user").prefetch_related("processes", "tags", "attachments"),
            pk=pk,
            user__role="factory",
        )
        return success_response(
            AdminFactorySerializer(profile, context={"request": request}).data,
            request=request,
        )

    def patch(self, request, pk):
        profile = get_object_or_404(FactoryProfile, pk=pk, user__role="factory")
        serializer = AdminSupplierUpdateSerializer(profile, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return success_response(
            AdminFactorySerializer(profile, context={"request": request}).data,
            request=request,
        )


class AdminSupplierTagView(APIView):
    permission_classes = [IsAdminRole]

    def post(self, request, pk):
        profile = get_object_or_404(FactoryProfile, pk=pk, user__role="factory")
        tag_name = (request.data.get("tag_name") or "").strip()
        if not tag_name:
            return error_response("TAG_NAME_REQUIRED", "标签名不能为空", request=request)
        tag, _ = SupplierTag.objects.get_or_create(profile=profile, tag_name=tag_name)
        return success_response(
            SupplierTagSerializer(tag).data,
            status=status.HTTP_201_CREATED,
            request=request,
        )

    def delete(self, request, pk):
        profile = get_object_or_404(FactoryProfile, pk=pk, user__role="factory")
        tag_id = request.data.get("tag_id")
        SupplierTag.objects.filter(profile=profile, pk=tag_id).delete()
        return success_response({}, message="标签已删除", request=request)


class AdminSupplierAttachmentView(APIView):
    permission_classes = [IsAdminRole]
    parser_classes = [MultiPartParser, FormParser]

    def post(self, request, pk):
        profile = get_object_or_404(FactoryProfile, pk=pk, user__role="factory")
        file_obj = request.FILES.get("file")
        code, msg = validate_upload_file(file_obj)
        if code:
            return error_response(code, msg, request=request)
        category = request.data.get("category", "qualification")
        is_public_raw = request.data.get("is_public", False)
        if isinstance(is_public_raw, bool):
            is_public = is_public_raw
        else:
            is_public = str(is_public_raw).lower() in {"1", "true", "yes", "on"}
        att = SupplierAttachment.objects.create(
            profile=profile,
            file=file_obj,
            file_name=file_obj.name,
            category=category,
            is_public=is_public,
        )
        return success_response(
            SupplierAttachmentSerializer(att, context={"request": request}).data,
            status=status.HTTP_201_CREATED,
            request=request,
        )

    def delete(self, request, pk):
        profile = get_object_or_404(FactoryProfile, pk=pk, user__role="factory")
        att_id = request.data.get("attachment_id")
        att = get_object_or_404(SupplierAttachment, pk=att_id, profile=profile)
        att.file.delete(save=False)
        att.delete()
        return success_response({}, message="附件已删除", request=request)


class AdminUserListCreateView(APIView):
    permission_classes = [IsAdminRole]

    def get(self, request):
        users = User.objects.exclude(role__in={"member", "factory"}).order_by("-created_at")
        return success_response(
            {"items": AdminUserSerializer(users, many=True).data},
            request=request,
        )

    def post(self, request):
        if request.user.role != "super_admin":
            raise AppAPIException("仅超级管理员可创建管理员", code="AUTH_PERMISSION_DENIED")
        serializer = AdminUserSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        return success_response(
            AdminUserSerializer(user).data,
            status=status.HTTP_201_CREATED,
            request=request,
        )


class AdminFactoryListView(APIView):
    permission_classes = [IsAdminRole]

    def get(self, request):
        status_filter = request.query_params.get("status")
        qs = FactoryProfile.objects.select_related("user").prefetch_related("processes")
        if status_filter:
            qs = qs.filter(status=status_filter)
        return success_response(
            {"items": AdminFactorySerializer(qs, many=True).data},
            request=request,
        )


class AdminFactoryDetailView(APIView):
    permission_classes = [IsAdminRole]

    def get(self, request, pk):
        profile = get_object_or_404(
            FactoryProfile.objects.select_related("user").prefetch_related("processes"),
            pk=pk,
        )
        return success_response(AdminFactorySerializer(profile).data, request=request)

    def patch(self, request, pk):
        profile = get_object_or_404(FactoryProfile.objects.select_related("user"), pk=pk)
        new_status = request.data.get("status")
        if new_status not in {"pending", "approved", "rejected"}:
            return error_response(
                "FACTORY_STATUS_INVALID",
                "无效的状态",
                request=request,
            )
        profile.status = new_status
        profile.save(update_fields=["status", "updated_at"])
        profile.user.is_active = True
        profile.user.save(update_fields=["is_active", "updated_at"])
        return success_response(AdminFactorySerializer(profile).data, request=request)


class AdminStatsView(APIView):
    """管理后台仪表盘聚合统计。"""

    permission_classes = [IsAdminRole]

    def get(self, request):
        from apps.inquiry.models import Inquiry
        from apps.payment.models import Payment
        from apps.project.models import Project
        from apps.rfq.models import RFQ

        from apps.chat.models import Conversation
        from apps.project.models import ProjectIssue
        from apps.rfq.models import ProductionOrder

        data = {
            "rfqs_total": RFQ.objects.count(),
            "rfqs_pending_review": RFQ.objects.filter(
                status__in={"submitted", "pending_review"}
            ).count(),
            "projects_active": Project.objects.filter(
                status__in={"pending", "in_progress"}
            ).count(),
            "payments_pending_confirm": Payment.objects.filter(
                status="pending_confirm"
            ).count(),
            "orders_pending_confirm": ProductionOrder.objects.filter(
                status="pending_confirm"
            ).count(),
            "disputes_open": Conversation.objects.filter(
                dispute_status=Conversation.DISPUTE_OPEN
            ).count(),
            "project_issues_open": ProjectIssue.objects.filter(status="open").count(),
            "inquiries_new": Inquiry.objects.filter(status="new").count(),
            "members_total": User.objects.filter(role="member").count(),
            "suppliers_approved": FactoryProfile.objects.filter(
                user__role="factory", status="approved"
            ).count(),
        }
        return success_response(data, request=request)


class AdminOpsQueueView(APIView):
    """运营例外队列聚合：争议、待确认付款/接单、开放项目问题。"""

    permission_classes = [IsAdminRole]

    def get(self, request):
        from apps.chat.models import Conversation
        from apps.payment.models import Payment
        from apps.project.models import ProjectIssue
        from apps.rfq.models import ProductionOrder

        limit = 20
        disputes = (
            Conversation.objects.filter(dispute_status=Conversation.DISPUTE_OPEN)
            .select_related("quote_request", "buyer", "supplier")
            .order_by("-disputed_at", "-id")[:limit]
        )
        payments = (
            Payment.objects.filter(status="pending_confirm")
            .select_related("buyer", "contract")
            .order_by("-created_at")[:limit]
        )
        orders = (
            ProductionOrder.objects.filter(status="pending_confirm")
            .select_related("buyer", "supplier", "rfq")
            .order_by("-created_at")[:limit]
        )
        issues = (
            ProjectIssue.objects.filter(status="open")
            .select_related("project", "project__buyer", "project__supplier")
            .order_by("-created_at")[:limit]
        )

        return success_response(
            {
                "counts": {
                    "disputes_open": Conversation.objects.filter(
                        dispute_status=Conversation.DISPUTE_OPEN
                    ).count(),
                    "payments_pending_confirm": Payment.objects.filter(
                        status="pending_confirm"
                    ).count(),
                    "orders_pending_confirm": ProductionOrder.objects.filter(
                        status="pending_confirm"
                    ).count(),
                    "project_issues_open": ProjectIssue.objects.filter(status="open").count(),
                },
                "disputes": [
                    {
                        "id": c.id,
                        "quote_request_id": c.quote_request_id,
                        "quote_request_no": getattr(c.quote_request, "request_no", "") or "",
                        "buyer_email": getattr(c.buyer, "email", "") or "",
                        "supplier_email": getattr(c.supplier, "email", "") or "",
                        "disputed_at": c.disputed_at.isoformat() if c.disputed_at else None,
                        "dispute_reason": (c.dispute_reason or "")[:200],
                        "href": f"/chat-disputes?conversation={c.id}",
                    }
                    for c in disputes
                ],
                "payments": [
                    {
                        "id": p.id,
                        "payment_no": p.payment_no,
                        "amount": p.amount,
                        "currency": p.currency,
                        "buyer_email": getattr(p.buyer, "email", "") or "",
                        "created_at": p.created_at.isoformat() if p.created_at else None,
                        "href": "/payments",
                    }
                    for p in payments
                ],
                "orders": [
                    {
                        "id": o.id,
                        "order_no": o.order_no,
                        "rfq_no": getattr(o.rfq, "rfq_no", "") or "",
                        "buyer_email": getattr(o.buyer, "email", "") or "",
                        "supplier_email": getattr(o.supplier, "email", "") or "",
                        "created_at": o.created_at.isoformat() if o.created_at else None,
                        "href": "/production-orders",
                    }
                    for o in orders
                ],
                "project_issues": [
                    {
                        "id": i.id,
                        "title": i.title,
                        "severity": i.severity,
                        "project_id": i.project_id,
                        "project_no": getattr(i.project, "project_no", "") or "",
                        "created_at": i.created_at.isoformat() if i.created_at else None,
                        "href": f"/projects?id={i.project_id}",
                    }
                    for i in issues
                ],
            },
            request=request,
        )
