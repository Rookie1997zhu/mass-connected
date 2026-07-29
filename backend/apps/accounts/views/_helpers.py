from rest_framework_simplejwt.tokens import RefreshToken

from apps.accounts.auth_cookies import set_refresh_cookie
from apps.accounts.serializers import FactoryProfileSerializer, UserSerializer
from core.responses import success_response


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


def _auth_success_with_refresh_cookie(request, payload, *, kind: str, message="成功", status_code=200):
    """统一登录/注册响应：access 在 body，refresh 写入 httpOnly Cookie（body 暂保留兼容）。"""
    response = success_response(payload, message=message, status=status_code, request=request)
    refresh = (payload.get("tokens") or {}).get("refresh")
    if refresh:
        set_refresh_cookie(response, refresh, kind=kind)
    return response
