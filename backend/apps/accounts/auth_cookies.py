"""httpOnly refresh cookie helpers for member / admin auth."""

from django.conf import settings

MEMBER_REFRESH_COOKIE = "oem_refresh"
ADMIN_REFRESH_COOKIE = "oem_admin_refresh"


def _refresh_max_age() -> int:
    lifetime = settings.SIMPLE_JWT.get("REFRESH_TOKEN_LIFETIME")
    if lifetime is None:
        return 7 * 24 * 3600
    return int(lifetime.total_seconds())


def cookie_name(kind: str) -> str:
    return ADMIN_REFRESH_COOKIE if kind == "admin" else MEMBER_REFRESH_COOKIE


def cookie_path(kind: str) -> str:
    return "/api/admin/auth" if kind == "admin" else "/api/member/auth"


def detect_auth_kind(request) -> str:
    path = getattr(request, "path", "") or ""
    return "admin" if "/admin/" in path else "member"


def set_refresh_cookie(response, refresh_token: str, *, kind: str = "member"):
    secure = bool(getattr(settings, "SECURE_SSL", False))
    response.set_cookie(
        cookie_name(kind),
        refresh_token,
        max_age=_refresh_max_age(),
        httponly=True,
        secure=secure,
        samesite="Lax",
        path=cookie_path(kind),
    )
    return response


def clear_refresh_cookie(response, *, kind: str = "member"):
    response.delete_cookie(cookie_name(kind), path=cookie_path(kind))
    return response


def read_refresh_token(request, *, kind: str | None = None) -> str:
    kind = kind or detect_auth_kind(request)
    cookie_val = request.COOKIES.get(cookie_name(kind)) or ""
    if cookie_val:
        return cookie_val
    body = getattr(request, "data", None) or {}
    if isinstance(body, dict):
        return (body.get("refresh") or "").strip()
    return ""
