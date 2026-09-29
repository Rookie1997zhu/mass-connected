from rest_framework.test import APIClient


class SecureClient(APIClient):
    """生产配置开启了 HTTPS 跳转，测试请求必须走 secure。"""

    def generic(self, method, path, data="", content_type="application/octet-stream", secure=True, **extra):
        return super().generic(method, path, data, content_type, secure=secure, **extra)
