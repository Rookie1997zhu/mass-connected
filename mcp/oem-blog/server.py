"""OEM 博客远程 HTTP MCP（streamable-http）。"""

from __future__ import annotations

import base64
import binascii
import json
import os
from typing import Any

import uvicorn
from mcp.server.fastmcp import FastMCP

from auth_middleware import ApiKeyAuthMiddleware
from django_client import DjangoApiError, DjangoBlogClient, dump_result
from markdown_html import markdown_to_html

MCP_PATH = "/mcp/blog"
HOST = os.environ.get("BLOG_MCP_HOST", "0.0.0.0")
PORT = int(os.environ.get("BLOG_MCP_PORT", "3100"))

mcp = FastMCP(
    "oem-blog",
    host=HOST,
    port=PORT,
    streamable_http_path=MCP_PATH,
    # 无会话粘滞，适合 Caddy 反代 + Claude Code 远程 HTTP
    stateless_http=True,
)


def _client() -> DjangoBlogClient:
    return DjangoBlogClient()


def _tool_error(exc: Exception) -> str:
    if isinstance(exc, DjangoApiError):
        payload = {
            "ok": False,
            "message": str(exc),
            "status_code": exc.status_code,
            "payload": exc.payload,
        }
        return dump_result(payload)
    return dump_result({"ok": False, "message": str(exc)})


def _boolish(value: Any, default: bool = False) -> bool:
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return bool(value)
    text = str(value).strip().lower()
    if text in {"1", "true", "yes", "y", "on"}:
        return True
    if text in {"0", "false", "no", "n", "off", ""}:
        return False
    return default


def _build_post_body(
    *,
    title: str | None = None,
    summary: str | None = None,
    content_markdown: str | None = None,
    cover_image: str | None = None,
    category_id: int | None = None,
    tags: list[str] | None = None,
    language: str | None = None,
    is_pinned: bool | None = None,
    is_featured: bool | None = None,
    publish_now: bool | None = None,
    include_status: bool = False,
) -> dict[str, Any]:
    body: dict[str, Any] = {}
    if title is not None:
        body["title"] = title
    if summary is not None:
        body["summary"] = summary
    if content_markdown is not None:
        body["content"] = markdown_to_html(content_markdown)
    if cover_image is not None:
        body["cover_image"] = cover_image
    if category_id is not None:
        body["category"] = category_id
    if tags is not None:
        body["tags"] = tags
    if language is not None:
        body["language"] = language
    if is_pinned is not None:
        body["is_pinned"] = _boolish(is_pinned)
    if is_featured is not None:
        body["is_featured"] = _boolish(is_featured)
    if include_status and publish_now is not None:
        body["status"] = "published" if _boolish(publish_now) else "draft"
    return body


@mcp.tool()
def blog_list_categories() -> str:
    """列出博客分类（id / name / slug）。"""
    try:
        data = _client().get("admin/blog/categories", params={"page_size": 100})
        return dump_result({"ok": True, "data": data})
    except Exception as exc:  # noqa: BLE001
        return _tool_error(exc)


@mcp.tool()
def blog_list_posts(
    status: str = "",
    language: str = "",
    q: str = "",
    page: int = 1,
    page_size: int = 20,
) -> str:
    """列出博客文章。可按 status（draft/published）、language、关键词 q 筛选。"""
    try:
        params: dict[str, Any] = {"page": page, "page_size": page_size}
        if status:
            params["status"] = status
        if language:
            params["language"] = language
        if q:
            params["q"] = q
        data = _client().get("admin/blog/posts", params=params)
        return dump_result({"ok": True, "data": data})
    except Exception as exc:  # noqa: BLE001
        return _tool_error(exc)


@mcp.tool()
def blog_create_post(
    title: str,
    content_markdown: str = "",
    summary: str = "",
    language: str = "zh",
    category_id: int | None = None,
    tags: list[str] | None = None,
    cover_image: str = "",
    is_pinned: bool = False,
    is_featured: bool = False,
    publish_now: bool = False,
) -> str:
    """创建博客文章。content_markdown 会转为 HTML。publish_now=true 时直接发布上线。"""
    try:
        body = _build_post_body(
            title=title,
            summary=summary,
            content_markdown=content_markdown,
            cover_image=cover_image or None,
            category_id=category_id,
            tags=tags or [],
            language=language,
            is_pinned=is_pinned,
            is_featured=is_featured,
            publish_now=publish_now,
            include_status=True,
        )
        data = _client().post_json("admin/blog/posts", body)
        return dump_result({"ok": True, "data": data})
    except Exception as exc:  # noqa: BLE001
        return _tool_error(exc)


@mcp.tool()
def blog_update_post(
    post_id: int,
    title: str | None = None,
    content_markdown: str | None = None,
    summary: str | None = None,
    language: str | None = None,
    category_id: int | None = None,
    tags: list[str] | None = None,
    cover_image: str | None = None,
    is_pinned: bool | None = None,
    is_featured: bool | None = None,
    publish_now: bool | None = None,
) -> str:
    """更新博客文章。传入的字段才会修改；publish_now=true 可改为已发布。"""
    try:
        body = _build_post_body(
            title=title,
            summary=summary,
            content_markdown=content_markdown,
            cover_image=cover_image,
            category_id=category_id,
            tags=tags,
            language=language,
            is_pinned=is_pinned,
            is_featured=is_featured,
            publish_now=publish_now,
            include_status=publish_now is not None,
        )
        if not body:
            return dump_result({"ok": False, "message": "未提供任何可更新字段"})
        data = _client().patch_json(f"admin/blog/posts/{post_id}", body)
        return dump_result({"ok": True, "data": data})
    except Exception as exc:  # noqa: BLE001
        return _tool_error(exc)


@mcp.tool()
def blog_publish_post(post_id: int) -> str:
    """将指定文章状态设为 published（首次发布会写入 published_at）。"""
    try:
        data = _client().patch_json(f"admin/blog/posts/{post_id}", {"status": "published"})
        return dump_result({"ok": True, "data": data})
    except Exception as exc:  # noqa: BLE001
        return _tool_error(exc)


@mcp.tool()
def blog_upload_cover(
    filename: str,
    content_base64: str,
    content_type: str = "image/png",
) -> str:
    """上传封面图（Base64）。返回 url，可填入 create/update 的 cover_image。"""
    try:
        raw = base64.b64decode(content_base64, validate=True)
    except (binascii.Error, ValueError) as exc:
        return dump_result({"ok": False, "message": f"content_base64 无效: {exc}"})
    if not filename.strip():
        return dump_result({"ok": False, "message": "filename 不能为空"})
    try:
        data = _client().upload_file(
            "admin/media/upload",
            filename=filename.strip(),
            content=raw,
            content_type=content_type or "application/octet-stream",
        )
        return dump_result({"ok": True, "data": data})
    except Exception as exc:  # noqa: BLE001
        return _tool_error(exc)


class HealthAndAuthApp:
    """在 FastMCP ASGI 外包一层：/healthz 探活 + API Key 校验。"""

    def __init__(self, mcp_app, api_key: str):
        self.mcp_app = ApiKeyAuthMiddleware(mcp_app, api_key, public_paths={"/healthz"})
        self.api_key = (api_key or "").strip()

    async def __call__(self, scope, receive, send):
        if scope["type"] == "http" and (scope.get("path") or "") == "/healthz":
            body = json.dumps({"status": "ok", "service": "oem-blog-mcp"}).encode("utf-8")
            await send(
                {
                    "type": "http.response.start",
                    "status": 200,
                    "headers": [
                        (b"content-type", b"application/json; charset=utf-8"),
                        (b"content-length", str(len(body)).encode("ascii")),
                    ],
                }
            )
            await send({"type": "http.response.body", "body": body})
            return
        await self.mcp_app(scope, receive, send)


def create_app():
    api_key = (os.environ.get("BLOG_MCP_API_KEY") or "").strip()
    return HealthAndAuthApp(mcp.streamable_http_app(), api_key)


def main() -> None:
    app = create_app()
    uvicorn.run(app, host=HOST, port=PORT, log_level=os.environ.get("BLOG_MCP_LOG_LEVEL", "info"))


if __name__ == "__main__":
    main()
