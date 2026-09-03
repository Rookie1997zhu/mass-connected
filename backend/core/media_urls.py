"""Build absolute URLs for media and authenticated download APIs."""


def api_absolute_uri(request, path: str) -> str:
    """path 形如 /api/member/payments/1/proof/download。"""
    if not path:
        return ""
    if request is None:
        return path
    return request.build_absolute_uri(path)


def absolute_media_url(request, url: str) -> str:
    """Return a usable absolute URL; do not re-prefix already-absolute (signed) URLs."""
    if not url:
        return ""
    if url.startswith("http://") or url.startswith("https://"):
        return url
    if request is None:
        return url
    return request.build_absolute_uri(url)


def absolute_file_url(request, field_file) -> str:
    """Absolute URL for a FieldFile / Storage path (supports OSS signed URLs)."""
    if not field_file:
        return ""
    try:
        url = field_file.url
    except ValueError:
        return ""
    return absolute_media_url(request, url)
