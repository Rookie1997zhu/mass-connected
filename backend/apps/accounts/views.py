from django.contrib.auth import authenticate
from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken

from apps.accounts.models import FactoryProfile, User
from apps.accounts.serializers import (
    AdminFactorySerializer,
    AdminUserSerializer,
    FactoryProfileSerializer,
    FactoryRegisterSerializer,
    MemberRegisterSerializer,
    UserSerializer,
)
from core.exceptions import AppAPIException
from core.permissions import IsAdminRole, IsFactoryRole, IsMemberRole
from core.responses import error_response, success_response


def issue_tokens(user):
    refresh = RefreshToken.for_user(user)
    return {"access": str(refresh.access_token), "refresh": str(refresh)}


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
        tokens = issue_tokens(user)
        return success_response(
            {"user": UserSerializer(user).data, "tokens": tokens},
            message="注册成功",
            status=status.HTTP_201_CREATED,
            request=request,
        )


class FactoryRegisterView(APIView):
    def post(self, request):
        if User.objects.filter(email=request.data.get("email")).exists():
            return error_response(
                "FACTORY_EMAIL_EXISTS",
                "邮箱已注册",
                status=status.HTTP_409_CONFLICT,
                request=request,
            )
        serializer = FactoryRegisterSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        return success_response(
            {
                "user": UserSerializer(user).data,
                "profile": FactoryProfileSerializer(user.factory_profile).data,
            },
            message="入驻申请已提交，请等待审核",
            status=status.HTTP_201_CREATED,
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
        if user.role == "factory":
            profile = getattr(user, "factory_profile", None)
            if not profile:
                return error_response(
                    "FACTORY_PROFILE_NOT_FOUND",
                    "工厂资料不存在",
                    status=status.HTTP_403_FORBIDDEN,
                    request=request,
                )
            if profile.status == "pending" or not user.is_active:
                return error_response(
                    "FACTORY_PENDING_REVIEW",
                    "工厂账号审核中，请等待管理员批准",
                    status=status.HTTP_403_FORBIDDEN,
                    request=request,
                )
            if profile.status == "rejected":
                return error_response(
                    "FACTORY_REJECTED",
                    "工厂入驻申请已被拒绝",
                    status=status.HTTP_403_FORBIDDEN,
                    request=request,
                )
        elif not user.is_active:
            return error_response(
                "MEMBER_INACTIVE",
                "账号已禁用",
                status=status.HTTP_403_FORBIDDEN,
                request=request,
            )
        tokens = issue_tokens(user)
        payload = {"user": UserSerializer(user).data, "tokens": tokens}
        if user.role == "factory":
            payload["profile"] = FactoryProfileSerializer(user.factory_profile).data
        return success_response(payload, request=request)


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
    permission_classes = [IsMemberRole]

    def get(self, request):
        return success_response(UserSerializer(request.user).data, request=request)

    def patch(self, request):
        serializer = UserSerializer(request.user, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return success_response(serializer.data, request=request)


class FactoryProfileView(APIView):
    permission_classes = [IsFactoryRole]

    def get(self, request):
        profile = request.user.factory_profile
        return success_response(FactoryProfileSerializer(profile).data, request=request)


class LogoutView(APIView):
    def post(self, request):
        return success_response({}, message="已登出", request=request)


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
        if new_status == "approved":
            profile.user.is_active = True
            profile.user.save(update_fields=["is_active", "updated_at"])
        elif new_status == "rejected":
            profile.user.is_active = False
            profile.user.save(update_fields=["is_active", "updated_at"])
        return success_response(AdminFactorySerializer(profile).data, request=request)
