"""调用 OEM Django admin blog / media API。"""

from __future__ import annotations

import json
import os
from typing import Any
from urllib.parse import urljoin

import httpx


class DjangoApiError(Exception):
    def __init__(self, message: str, *, status_code: int | None = None, payload: Any = None):
        super().__init__(message)
        self.status_code = status_code
        self.payload = payload


class DjangoBlogClient:
    def __init__(
        self,
        base_url: str | None = None,
        api_key: str | None = None,
        timeout: float = 60.0,
    ):
        self.base_url = (base_url or os.environ.get("OEM_API_BASE_URL") or "http://backend:8000/api").rstrip(
            "/"
        ) + "/"
        self.api_key = (api_key or os.environ.get("BLOG_MCP_API_KEY") or "").strip()
        self.timeout = timeout
        if not self.api_key:
            raise DjangoApiError("未配置 BLOG_MCP_API_KEY")

    def _headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Accept": "application/json",
        }

    def _url(self, path: str) -> str:
        return urljoin(self.base_url, path.lstrip("/"))

    def _parse(self, response: httpx.Response) -> Any:
        try:
            payload = response.json()
        except Exception as exc:  # noqa: BLE001
            raise DjangoApiError(
                f"Django 返回非 JSON（HTTP {response.status_code}）",
                status_code=response.status_code,
                payload=response.text[:500],
            ) from exc

        if response.status_code >= 400:
            message = ""
            if isinstance(payload, dict):
                message = str(payload.get("message") or payload.get("code") or payload)
            raise DjangoApiError(
                message or f"Django 请求失败（HTTP {response.status_code}）",
                status_code=response.status_code,
                payload=payload,
            )
        if isinstance(payload, dict) and payload.get("code") not in (None, "OK"):
            raise DjangoApiError(
                str(payload.get("message") or payload.get("code")),
                status_code=response.status_code,
                payload=payload,
            )
        if isinstance(payload, dict) and "data" in payload:
            return payload["data"]
        return payload

    def get(self, path: str, params: dict[str, Any] | None = None) -> Any:
        with httpx.Client(timeout=self.timeout, follow_redirects=True) as client:
            response = client.get(self._url(path), headers=self._headers(), params=params or {})
            return self._parse(response)

    def post_json(self, path: str, body: dict[str, Any]) -> Any:
        headers = {**self._headers(), "Content-Type": "application/json"}
        with httpx.Client(timeout=self.timeout, follow_redirects=True) as client:
            response = client.post(self._url(path), headers=headers, content=json.dumps(body))
            return self._parse(response)

    def patch_json(self, path: str, body: dict[str, Any]) -> Any:
        headers = {**self._headers(), "Content-Type": "application/json"}
        with httpx.Client(timeout=self.timeout, follow_redirects=True) as client:
            response = client.patch(self._url(path), headers=headers, content=json.dumps(body))
            return self._parse(response)

    def upload_file(self, path: str, filename: str, content: bytes, content_type: str = "application/octet-stream") -> Any:
        with httpx.Client(timeout=self.timeout, follow_redirects=True) as client:
            response = client.post(
                self._url(path),
                headers=self._headers(),
                files={"file": (filename, content, content_type)},
            )
            return self._parse(response)


def dump_result(data: Any) -> str:
    return json.dumps(data, ensure_ascii=False, indent=2, default=str)
