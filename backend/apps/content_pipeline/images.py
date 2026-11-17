"""封面与文内图：YouTube 缩略图转存（产品接受版权风险）。"""

from __future__ import annotations

import logging
import re
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from django.core.files.base import ContentFile
from django.core.files.storage import default_storage

logger = logging.getLogger(__name__)

_THUMB_CANDIDATES = (
    "maxresdefault.jpg",
    "sddefault.jpg",
    "hqdefault.jpg",
    "mqdefault.jpg",
)


def _download(url: str) -> bytes | None:
    req = Request(url, headers={"User-Agent": "OEMContentPipeline/1.0"})
    try:
        with urlopen(req, timeout=20) as resp:  # noqa: S310 — fixed YouTube thumbnail hosts
            return resp.read()
    except (HTTPError, URLError, TimeoutError) as exc:
        logger.warning("thumbnail_download_failed url=%s err=%s", url, exc)
        return None


def download_youtube_thumbnail(video_id: str) -> tuple[bytes, str] | None:
    video_id = (video_id or "").strip()
    if not video_id:
        return None
    for name in _THUMB_CANDIDATES:
        url = f"https://i.ytimg.com/vi/{video_id}/{name}"
        data = _download(url)
        if data and len(data) > 1000:
            return data, "image/jpeg"
    return None


def store_image_bytes(data: bytes, *, filename: str) -> str:
    """保存到 default_storage，返回可写入 BlogPost.cover_image 的 URL/路径。"""
    path = default_storage.save(f"uploads/pipeline/{filename}", ContentFile(data))
    try:
        return default_storage.url(path)
    except Exception:  # noqa: BLE001
        return path


def build_cover_image(video_id: str) -> str:
    packed = download_youtube_thumbnail(video_id)
    if not packed:
        return ""
    data, _ctype = packed
    return store_image_bytes(data, filename=f"{video_id}_cover.jpg")


def _insert_after_nth_paragraph(html: str, fragment: str, *, n: int = 2) -> str:
    matches = list(re.finditer(r"</p>", html, flags=re.I))
    if len(matches) < n:
        return html + fragment
    pos = matches[n - 1].end()
    return html[:pos] + fragment + html[pos:]


def inject_inline_images(content_html: str, video_id: str, slots: int) -> str:
    """将 <!--IMAGE_n--> 替换为图，或在第 2 段落后插入。失败则仅保留原文。"""
    html = content_html or ""
    if slots <= 0:
        return html

    urls: list[str] = []
    for idx, name in enumerate(("hqdefault.jpg", "mqdefault.jpg", "sddefault.jpg")):
        if len(urls) >= slots:
            break
        data = _download(f"https://i.ytimg.com/vi/{video_id}/{name}")
        if not data or len(data) <= 1000:
            continue
        url = store_image_bytes(data, filename=f"{video_id}_inline_{idx}.jpg")
        urls.append(url)

    if not urls:
        return re.sub(r"<!--IMAGE_\d+-->", "", html)

    for i, url in enumerate(urls, start=1):
        figure = f'<figure class="pipeline-inline"><img src="{url}" alt="" /></figure>'
        placeholder = f"<!--IMAGE_{i}-->"
        if placeholder in html:
            html = html.replace(placeholder, figure, 1)
        else:
            html = _insert_after_nth_paragraph(html, figure, n=min(i + 1, 3))

    return re.sub(r"<!--IMAGE_\d+-->", "", html)
