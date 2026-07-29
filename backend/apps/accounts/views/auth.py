from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.views import APIView
from rest_framework_simplejwt.exceptions import InvalidToken, TokenError
from rest_framework_simplejwt.serializers import TokenRefreshSerializer
from rest_framework_simplejwt.tokens import RefreshToken

from apps.accounts.auth_cookies import (
    clear_refresh_cookie,
    detect_auth_kind,
    read_refresh_token,
    set_refresh_cookie,
)
from core.responses import error_response, success_response


class CookieTokenRefreshView(APIView):
    """从 Cookie（优先）或 body 读取 refresh，返回统一 {code,data.access}，并轮换 Cookie。"""

    authentication_classes = []
    permission_classes = [AllowAny]

    def post(self, request):
        kind = detect_auth_kind(request)
        refresh_str = read_refresh_token(request, kind=kind)
        if not refresh_str:
            return error_response(
                "AUTH_REFRESH_MISSING",
                "缺少 refresh token",
                status=status.HTTP_401_UNAUTHORIZED,
                request=request,
            )
        serializer = TokenRefreshSerializer(data={"refresh": refresh_str})
        try:
            valid = serializer.is_valid()
            err_payload = serializer.errors if not valid else {}
        except TokenError:
            valid = False
            err_payload = {}
        if not valid:
            response = error_response(
                "AUTH_REFRESH_INVALID",
                "refresh token 无效或已失效",
                errors=err_payload if isinstance(err_payload, dict) else {},
                status=status.HTTP_401_UNAUTHORIZED,
                request=request,
            )
            clear_refresh_cookie(response, kind=kind)
            return response

        data = serializer.validated_data
        response = success_response({"access": data["access"]}, request=request)
        new_refresh = data.get("refresh")
        if new_refresh:
            set_refresh_cookie(response, new_refresh, kind=kind)
        return response


# 兼容旧引用名
AllowAnyTokenRefreshView = CookieTokenRefreshView


class LogoutView(APIView):
    """允许未认证调用：凭 Cookie/body 拉黑 refresh 并清 Cookie（access 过期时仍可登出）。"""

    authentication_classes = []
    permission_classes = [AllowAny]

    def post(self, request):
        kind = detect_auth_kind(request)
        refresh_str = read_refresh_token(request, kind=kind)
        if refresh_str:
            try:
                RefreshToken(refresh_str).blacklist()
            except (TokenError, InvalidToken, Exception):  # noqa: BLE001
                pass
        response = success_response({}, message="已登出", request=request)
        clear_refresh_cookie(response, kind=kind)
        return response
