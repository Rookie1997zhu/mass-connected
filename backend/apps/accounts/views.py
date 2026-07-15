from django.contrib.auth import authenticate
from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken

from apps.accounts.models import FactoryProfile, SupplierAttachment, SupplierTag, User
from apps.accounts.serializers import (
    AdminFactorySerializer,
    AdminMemberSerializer,
    AdminSupplierCreateSerializer,
    AdminSupplierUpdateSerializer,
    AdminUserSerializer,
    FactoryProfileSerializer,
    FactoryRegisterSerializer,
    MemberEnterpriseProfileSerializer,
    MemberRegisterSerializer,
    PUBLIC_SUPPLIER_ATTACHMENT_CATEGORIES,
    PublicPartnerSerializer,
    SupplierAttachmentSerializer,
    SupplierProfileUpdateSerializer,
    SupplierTagSerializer,
    UserSerializer,
)
from core.file_validation import validate_upload_file
from core.exceptions import AppAPIException
from core.pagination import StandardPagination
from core.permissions import IsAdminRole, IsBuyerRole, IsSupplierRole
from core.responses import error_response, success_response
from django.http import FileResponse


def issue_tokens(user):
    refresh = RefreshToken.for_user(user)
    return {"access": str(refresh.access_token), "refresh": str(refresh)}


def get_lang(request):
    return request.query_params.get("lang") or request.headers.get("Accept-Language", "ko")[:2]


def user_login_payload(user):
    payload = {"user": UserSerializer(user).data, "tokens": issue_tokens(user)}
    profile = getattr(user, "factory_profile", None)
    if profile:
        payload["profile"] = FactoryProfileSerializer(profile).data
    return payload


class MemberRegisterView(APIView):
    def post(self, request):
        if User.objects.filter(email=request.data.get("email")).exists():
            return error_response(
                "MEMBER_EMAIL_EXISTS",
                "邮箱已注册",
                status=status.HTTP_409_CONFLICT,
                request=request,
            )
        serializer = MemberRegisterSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        try:
            from apps.points.services import grant_register_bonus

            grant_register_bonus(user)
        except Exception:  # noqa: BLE001 - 积分赠送失败不阻断注册
            pass
        return success_response(
            user_login_payload(user),
            message="注册成功",
            status=status.HTTP_201_CREATED,
            request=request,
        )


class FactoryRegisterView(APIView):
    def post(self, request):
        return error_response(
            "FACTORY_REGISTER_DEPRECATED",
            "请使用企业会员注册（member_type=enterprise）",
            status=status.HTTP_410_GONE,
            request=request,
        )


class MemberLoginView(APIView):
    def post(self, request):
        email = request.data.get("email")
        password = request.data.get("password")
        user = authenticate(request, username=email, password=password)
        if not user or user.role not in {"member", "factory"}:
            return error_response(
                "AUTH_CREDENTIALS_INVALID",
                "账号或密码错误",
                status=status.HTTP_401_UNAUTHORIZED,
                request=request,
            )
        if not user.is_active:
            return error_response(
                "MEMBER_INACTIVE",
                "账号已禁用",
                status=status.HTTP_403_FORBIDDEN,
                request=request,
            )
        return success_response(user_login_payload(user), request=request)


class AdminLoginView(APIView):
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
        return success_response({"user": UserSerializer(user).data, "tokens": tokens}, request=request)


class MemberProfileView(APIView):
    permission_classes = [IsBuyerRole]
    parser_classes = [MultiPartParser, FormParser]

    def get(self, request):
        return success_response(
            UserSerializer(request.user, context={"request": request}).data,
            request=request,
        )

    def patch(self, request):
        user = request.user
        serializer = UserSerializer(user, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        if user.member_type == "enterprise":
            profile = getattr(user, "factory_profile", None)
            if profile:
                ent_serializer = MemberEnterpriseProfileSerializer(
                    profile, data=request.data, partial=True
                )
                ent_serializer.is_valid(raise_exception=True)
                ent_serializer.save()
                license_file = request.FILES.get("business_license")
                if license_file:
                    code, msg = validate_upload_file(license_file)
                    if code:
                        return error_response(code, msg, request=request)
                    profile.business_license = license_file
                    profile.save(update_fields=["business_license", "updated_at"])
        return success_response(
            UserSerializer(user, context={"request": request}).data,
            request=request,
        )


class FactoryProfileView(APIView):
    permission_classes = [IsSupplierRole]
    parser_classes = [MultiPartParser, FormParser, JSONParser]

    def get(self, request):
        profile = (
            FactoryProfile.objects.select_related("user")
            .prefetch_related("processes", "tags", "attachments")
            .get(pk=request.user.factory_profile.pk)
        )
        return success_response(
            FactoryProfileSerializer(profile, context={"request": request}).data,
            request=request,
        )

    def patch(self, request):
        profile = get_object_or_404(FactoryProfile, user=request.user)
        serializer = SupplierProfileUpdateSerializer(profile, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        user = request.user
        user_changed = False
        if "name" in request.data:
            user.name = request.data.get("name") or ""
            user_changed = True
        if "phone" in request.data:
            user.phone = request.data.get("phone") or ""
            user_changed = True
        if user_changed:
            user.save(update_fields=["name", "phone", "updated_at"])
        profile = (
            FactoryProfile.objects.select_related("user")
            .prefetch_related("processes", "tags", "attachments")
            .get(pk=profile.pk)
        )
        return success_response(
            FactoryProfileSerializer(profile, context={"request": request}).data,
            message="企业资料已更新",
            request=request,
        )


class SupplierProfileAttachmentView(APIView):
    """供应商维护自己的企业资料附件（可标记是否对买家公开）。"""

    permission_classes = [IsSupplierRole]
    parser_classes = [MultiPartParser, FormParser, JSONParser]

    def post(self, request):
        profile = get_object_or_404(FactoryProfile, user=request.user)
        file_obj = request.FILES.get("file")
        code, msg = validate_upload_file(file_obj)
        if code:
            return error_response(code, msg, request=request)
        category = (request.data.get("category") or "company_profile").strip()
        allowed = {c[0] for c in SupplierAttachment.CATEGORY_CHOICES}
        if category not in allowed:
            return error_response(
                "SUPPLIER_ATTACHMENT_CATEGORY_INVALID",
                "无效的附件分类",
                errors={"category": list(allowed)},
                request=request,
            )
        is_public_raw = request.data.get("is_public", "true")
        if isinstance(is_public_raw, bool):
            is_public = is_public_raw
        else:
            is_public = str(is_public_raw).lower() in {"1", "true", "yes", "on"}
        if is_public and category not in PUBLIC_SUPPLIER_ATTACHMENT_CATEGORIES:
            return error_response(
                "SUPPLIER_ATTACHMENT_NOT_PUBLICABLE",
                "该类附件不可设为公开",
                request=request,
            )
        att = SupplierAttachment.objects.create(
            profile=profile,
            file=file_obj,
            file_name=file_obj.name,
            category=category,
            is_public=is_public,
        )
        return success_response(
            SupplierAttachmentSerializer(att, context={"request": request}).data,
            message="企业资料附件已上传",
            status=status.HTTP_201_CREATED,
            request=request,
        )

    def delete(self, request):
        profile = get_object_or_404(FactoryProfile, user=request.user)
        att_id = request.data.get("attachment_id") or request.query_params.get("attachment_id")
        att = get_object_or_404(SupplierAttachment, pk=att_id, profile=profile)
        if att.file:
            att.file.delete(save=False)
        att.delete()
        return success_response({}, message="附件已删除", request=request)


class SupplierProfileAttachmentDownloadView(APIView):
    permission_classes = [IsSupplierRole]

    def get(self, request, file_id):
        profile = get_object_or_404(FactoryProfile, user=request.user)
        att = get_object_or_404(SupplierAttachment, pk=file_id, profile=profile)
        if not att.file:
            return error_response("SUPPLIER_ATTACHMENT_MISSING", "文件不存在", request=request)
        return FileResponse(att.file.open("rb"), as_attachment=False, filename=att.file_name)


class AdminSupplierAttachmentDownloadView(APIView):
    permission_classes = [IsAdminRole]

    def get(self, request, pk, file_id):
        profile = get_object_or_404(FactoryProfile, pk=pk, user__role="factory")
        att = get_object_or_404(SupplierAttachment, pk=file_id, profile=profile)
        if not att.file:
            return error_response("SUPPLIER_ATTACHMENT_MISSING", "文件不存在", request=request)
        return FileResponse(att.file.open("rb"), as_attachment=False, filename=att.file_name)


class PublicPartnerListView(APIView):
    def get(self, request):
        qs = (
            FactoryProfile.objects.filter(status="approved")
            .prefetch_related("processes")
            .order_by("-created_at")
        )
        category_id = request.query_params.get("service_category_id")
        if category_id:
            qs = qs.filter(processes__id=category_id).distinct()
        return success_response(
            {"items": PublicPartnerSerializer(qs, many=True, context={"lang": get_lang(request)}).data},
            request=request,
        )


class LogoutView(APIView):
    def post(self, request):
        return success_response({}, message="已登出", request=request)


class MemberDashboardView(APIView):
    """MY PAGE 概览聚合。"""

    permission_classes = [IsBuyerRole]

    def get(self, request):
        user = request.user
        data = {
            "profile": UserSerializer(user).data,
            "simple_quotes_count": 0,
            "rfqs_count": 0,
            "projects_count": 0,
            "contracts_count": 0,
            "pending_payments_count": 0,
            "points_balance": 0,
            "unread_notifications": 0,
        }
        try:
            from apps.simplequote.models import SimpleQuote

            data["simple_quotes_count"] = SimpleQuote.objects.filter(buyer=user).count()
        except Exception:  # noqa: BLE001
            pass
        try:
            from apps.rfq.models import RFQ

            data["rfqs_count"] = RFQ.objects.filter(buyer=user).count()
        except Exception:  # noqa: BLE001
            pass
        try:
            from apps.project.models import Project

            data["projects_count"] = Project.objects.filter(buyer=user).count()
        except Exception:  # noqa: BLE001
            pass
        try:
            from apps.contract.models import Contract

            data["contracts_count"] = Contract.objects.filter(buyer=user).count()
        except Exception:  # noqa: BLE001
            pass
        try:
            from apps.payment.models import Payment

            data["pending_payments_count"] = Payment.objects.filter(
                buyer=user, status__in=["unpaid", "pending_confirm"]
            ).count()
        except Exception:  # noqa: BLE001
            pass
        try:
            from apps.points.services import ensure_wallet

            data["points_balance"] = ensure_wallet(user).balance
        except Exception:  # noqa: BLE001
            pass
        try:
            from apps.notification.models import Notification

            data["unread_notifications"] = Notification.objects.filter(
                user=user, is_read=False
            ).count()
        except Exception:  # noqa: BLE001
            pass
        return success_response(data, request=request)


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
            "inquiries_new": Inquiry.objects.filter(status="new").count(),
            "members_total": User.objects.filter(role="member").count(),
            "suppliers_approved": FactoryProfile.objects.filter(
                user__role="factory", status="approved"
            ).count(),
        }
        return success_response(data, request=request)
