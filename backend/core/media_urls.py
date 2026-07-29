"""Build absolute API paths for authenticated media downloads (not raw /media URLs)."""


def api_absolute_uri(request, path: str) -> str:
    """path 形如 /api/member/payments/1/proof/download。"""
    if not path:
        return ""
    if request is None:
        return path
    return request.build_absolute_uri(path)
