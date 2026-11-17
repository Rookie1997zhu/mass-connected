"""入站 Bearer / X-Api-Key 校验（与 Django BLOG_MCP_API_KEY 共用）。"""

from __future__ import annotations

import json
import secrets
from typing import Callable


def _keys_equal(left: str, right: str) -> bool:
    if not left or not right or len(left) != len(right):
        return False
    return secrets.compare_digest(left, right)


def _header_map(scope: dict) -> dict[str, str]:
    result: dict[str, str] = {}
    for key, value in scope.get("headers") or []:
        result[key.decode("latin-1").lower()] = value.decode("latin-1")
    return result


def _extract_key(headers: dict[str, str]) -> str:
    x_api_key = (headers.get("x-api-key") or "").strip()
    if x_api_key:
        return x_api_key
    auth = (headers.get("authorization") or "").strip()
    if auth.lower().startswith("bearer "):
        return auth[7:].strip()
    return ""


class ApiKeyAuthMiddleware:
    """ASGI 中间件：除探活路径外要求有效 API Key。"""

    def __init__(self, app: Callable, api_key: str, *, public_paths: set[str] | None = None):
        self.app = app
        self.api_key = (api_key or "").strip()
        self.public_paths = public_paths or {"/healthz"}

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        path = scope.get("path") or ""
        if path in self.public_paths:
            await self.app(scope, receive, send)
            return

        if not self.api_key:
            await self._reject(send, 503, "BLOG_MCP_API_KEY 未配置")
            return

        provided = _extract_key(_header_map(scope))
        if not _keys_equal(provided, self.api_key):
            await self._reject(send, 401, "博客 MCP API Key 无效")
            return

        await self.app(scope, receive, send)

    async def _reject(self, send, status_code: int, message: str) -> None:
        body = json.dumps(
            {"error": "unauthorized", "message": message},
            ensure_ascii=False,
        ).encode("utf-8")
        await send(
            {
                "type": "http.response.start",
                "status": status_code,
                "headers": [
                    (b"content-type", b"application/json; charset=utf-8"),
                    (b"content-length", str(len(body)).encode("ascii")),
                    (b"www-authenticate", b'Bearer error="invalid_token"'),
                ],
            }
        )
        await send({"type": "http.response.body", "body": body})
