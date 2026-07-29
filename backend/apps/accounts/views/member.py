from django.contrib.auth import authenticate
from rest_framework import status
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.permissions import AllowAny
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
    user_login_payload,
)
from core.file_validation import validate_upload_file
from core.permissions import IsBuyerRole
from core.responses import error_response, success_response


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
