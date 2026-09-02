from datetime import date

from django.contrib.auth import authenticate
from rest_framework import status
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView

from apps.accounts.models import User
from apps.accounts.serializers import (
    MemberEnterpriseProfileSerializer,
    MemberRegisterSerializer,
    UserSerializer,
)
from apps.accounts.views._helpers import (
    _auth_success_with_refresh_cookie,
    get_lang,
    user_login_payload,
)
from apps.accounts.services.email_verification import (
    can_resend_verification,
    confirm_verification_token,
    enqueue_verification_email,
)
from core.file_validation import validate_upload_file
from core.permissions import IsBuyerRole, IsMemberOrFactoryRole
from core.responses import error_response, success_response

ACTION_RFQ_STATUSES = ("quoted", "comparing", "customer_confirming", "negotiating")
PROJECT_TERMINAL_STATUSES = ("completed", "cancelled")


class MemberRegisterView(APIView):
    permission_classes = [AllowAny]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "register"

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
        try:
            enqueue_verification_email(user, lang=get_lang(request))
        except Exception:  # noqa: BLE001 - 验证邮件失败不阻断注册
            pass
        return _auth_success_with_refresh_cookie(
            request,
            user_login_payload(user),
            kind="member",
            message="注册成功",
            status_code=status.HTTP_201_CREATED,
        )


class FactoryRegisterView(APIView):
    permission_classes = [AllowAny]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "register"

    def post(self, request):
        return error_response(
            "FACTORY_REGISTER_DEPRECATED",
            "请使用企业会员注册（member_type=enterprise）",
            status=status.HTTP_410_GONE,
            request=request,
        )


class MemberLoginView(APIView):
    permission_classes = [AllowAny]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "login"

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
        return _auth_success_with_refresh_cookie(
            request, user_login_payload(user), kind="member"
        )


class VerifyEmailConfirmView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        token = (request.data.get("token") or "").strip()
        if not token:
            return error_response(
                "EMAIL_VERIFY_TOKEN_INVALID",
                "验证链接无效",
                status=status.HTTP_400_BAD_REQUEST,
                request=request,
            )
        user, result = confirm_verification_token(token)
        if result == "expired":
            return error_response(
                "EMAIL_VERIFY_TOKEN_EXPIRED",
                "验证链接已过期",
                status=status.HTTP_400_BAD_REQUEST,
                request=request,
            )
        if result == "invalid":
            return error_response(
                "EMAIL_VERIFY_TOKEN_INVALID",
                "验证链接无效",
                status=status.HTTP_400_BAD_REQUEST,
                request=request,
            )
        message = "邮箱已验证" if result == "verified" else "邮箱已验证"
        return success_response(
            {"user": UserSerializer(user).data},
            message=message,
            request=request,
        )


class VerifyEmailResendView(APIView):
    permission_classes = [IsAuthenticated]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "verify_email"

    def post(self, request):
        user = request.user
        if user.is_verified:
            return error_response(
                "EMAIL_ALREADY_VERIFIED",
                "邮箱已验证",
                status=status.HTTP_400_BAD_REQUEST,
                request=request,
            )
        if not can_resend_verification(user.id):
            return error_response(
                "RATE_LIMIT_EXCEEDED",
                "发送过于频繁，请稍后再试",
                status=status.HTTP_429_TOO_MANY_REQUESTS,
                request=request,
            )
        enqueue_verification_email(user, lang=get_lang(request))
        return success_response({}, message="验证邮件已发送", request=request)


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


class BuyerWorkbenchView(APIView):
    """买家工作台聚合：身份信息、待办计数、临近截止、最近通知。"""

    permission_classes = [IsMemberOrFactoryRole]

    def get(self, request):
        user = request.user
        today = date.today()

        company_name = ""
        factory_profile = getattr(user, "factory_profile", None)
        if factory_profile:
            company_name = factory_profile.company_name or ""

        profile = {
            "display_name": user.name or "",
            "email": user.email or "",
            "member_type": user.member_type or "",
            "company_name": company_name,
        }

        action_rfqs = 0
        pending_payments = 0
        active_projects = 0
        unread_notifications = 0
        upcoming_deadlines = []
        recent_notifications = []

        try:
            from apps.rfq.models import RFQ
            from apps.i18n.fields import resolve_i18n

            action_rfqs = RFQ.objects.filter(
                buyer=user,
                status__in=ACTION_RFQ_STATUSES,
            ).count()

            lang = (request.headers.get("Accept-Language") or "ko").split(",")[0].strip()
            lang = lang.split("-")[0].strip()[:2] or "ko"

            rfq_rows = (
                RFQ.objects.filter(
                    buyer=user,
                    target_delivery_date__isnull=False,
                    target_delivery_date__gte=today,
                )
                .select_related("service_category")
                .order_by("target_delivery_date")[:20]
            )
            for rfq in rfq_rows:
                cat = getattr(rfq, "service_category", None)
                subtitle = resolve_i18n(cat.name, lang) if cat else ""
                upcoming_deadlines.append(
                    {
                        "kind": "rfq",
                        "id": rfq.id,
                        "title": rfq.rfq_no or f"RFQ-{rfq.id}",
                        "subtitle": subtitle,
                        "deadline": rfq.target_delivery_date.isoformat(),
                        "status": rfq.status,
                    }
                )
        except Exception:  # noqa: BLE001
            pass

        try:
            from apps.payment.models import Payment

            pending_payments = Payment.objects.filter(
                buyer=user, status__in=["unpaid", "pending_confirm"]
            ).count()
        except Exception:  # noqa: BLE001
            pass

        try:
            from apps.project.models import Project

            active_projects = (
                Project.objects.filter(buyer=user)
                .exclude(status__in=PROJECT_TERMINAL_STATUSES)
                .count()
            )
            project_rows = (
                Project.objects.filter(
                    buyer=user,
                    expected_delivery_date__isnull=False,
                    expected_delivery_date__gte=today,
                )
                .order_by("expected_delivery_date")[:20]
            )
            for prj in project_rows:
                upcoming_deadlines.append(
                    {
                        "kind": "project",
                        "id": prj.id,
                        "title": prj.project_no or prj.title or f"PRJ-{prj.id}",
                        "subtitle": prj.title or "",
                        "deadline": prj.expected_delivery_date.isoformat(),
                        "status": prj.status,
                    }
                )
        except Exception:  # noqa: BLE001
            pass

        upcoming_deadlines.sort(key=lambda x: x["deadline"])
        upcoming_deadlines = upcoming_deadlines[:8]

        try:
            from apps.notification.models import Notification
            from apps.notification.serializers import NotificationSerializer

            unread_notifications = Notification.objects.filter(
                user=user, is_read=False
            ).count()
            recent_qs = Notification.objects.filter(user=user).order_by("-created_at")[:5]
            recent_notifications = NotificationSerializer(recent_qs, many=True).data
        except Exception:  # noqa: BLE001
            pass

        from apps.accounts.services.workbench import (
            build_buyer_action_items,
            build_unread_chats,
        )
        from core.fx_rate import get_cny_krw_rate

        data = {
            "profile": profile,
            "counts": {
                "action_rfqs": action_rfqs,
                "pending_payments": pending_payments,
                "active_projects": active_projects,
                "unread_notifications": unread_notifications,
            },
            "action_items": build_buyer_action_items(user),
            "unread_chats": build_unread_chats(user),
            "upcoming_deadlines": upcoming_deadlines,
            "recent_notifications": recent_notifications,
            "fx": get_cny_krw_rate(),
        }
        return success_response(data, request=request)
