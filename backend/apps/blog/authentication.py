"""博客 MCP 机器 API Key 认证（环境变量，无 DB 表）。"""

from __future__ import annotations

import secrets

from django.conf import settings
from django.contrib.auth import get_user_model
from rest_framework.authentication import BaseAuthentication
from rest_framework.exceptions import AuthenticationFailed

ADMIN_ROLES = frozenset({"super_admin", "operator", "sales"})


class BlogMcpKeyInvalid(AuthenticationFailed):
    status_code = 401
    default_code = "BLOG_MCP_KEY_INVALID"
    default_detail = "博客 MCP API Key 无效"


class BlogMcpAuthorInvalid(AuthenticationFailed):
    status_code = 401
    default_code = "BLOG_MCP_AUTHOR_INVALID"
    default_detail = "博客 MCP 作者账号无效"


def _keys_equal(left: str, right: str) -> bool:
    if not left or not right or len(left) != len(right):
        return False
    return secrets.compare_digest(left, right)


def _extract_api_key(request) -> tuple[str | None, bool]:
    """返回 (key, require_match)。

    X-Api-Key 存在时必须匹配；Bearer 仅在与配置 Key 全等时认领，否则交 JWT。
    """
    x_api_key = (request.META.get("HTTP_X_API_KEY") or "").strip()
    if x_api_key:
        return x_api_key, True

    auth_header = (request.META.get("HTTP_AUTHORIZATION") or "").strip()
    if auth_header.lower().startswith("bearer "):
        return auth_header[7:].strip(), False
    return None, False


class BlogMcpApiKeyAuthentication(BaseAuthentication):
    """用 BLOG_MCP_API_KEY 认证，并映射为 BLOG_MCP_AUTHOR_EMAIL 用户。"""

    def authenticate(self, request):
        configured = (getattr(settings, "BLOG_MCP_API_KEY", None) or "").strip()
        if not configured:
            return None

        provided, require_match = _extract_api_key(request)
        if not provided:
            return None

        if not _keys_equal(provided, configured):
            if require_match:
                raise BlogMcpKeyInvalid()
            return None

        author_email = (getattr(settings, "BLOG_MCP_AUTHOR_EMAIL", None) or "").strip().lower()
        if not author_email:
            raise BlogMcpAuthorInvalid("未配置 BLOG_MCP_AUTHOR_EMAIL")

        User = get_user_model()
        user = User.objects.filter(email__iexact=author_email).first()
        if (
            user is None
            or not user.is_active
            or getattr(user, "role", None) not in ADMIN_ROLES
        ):
            raise BlogMcpAuthorInvalid()

        return (user, "blog_mcp_api_key")
