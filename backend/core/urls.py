from django.conf import settings
from django.conf.urls.static import static
from django.db import connection
from django.urls import include, path
from rest_framework.views import APIView

from core.responses import success_response


from rest_framework.permissions import AllowAny


class HealthView(APIView):
    authentication_classes = []
    permission_classes = [AllowAny]

    def get(self, request):
        db_ok = "ok"
        redis_ok = "ok"
        try:
            connection.ensure_connection()
        except Exception:
            db_ok = "error"
        try:
            from django.core.cache import cache

            cache.set("health_check", "1", 5)
            if cache.get("health_check") != "1":
                redis_ok = "error"
        except Exception:
            redis_ok = "error"
        status_value = "healthy" if db_ok == "ok" and redis_ok == "ok" else "degraded"
        return success_response(
            {"status": status_value, "database": db_ok, "redis": redis_ok},
            request=request,
        )


urlpatterns = [
    path("health", HealthView.as_view()),
    path("", include("apps.accounts.urls")),
    path("", include("apps.content.urls")),
    path("", include("apps.inquiry.urls")),
    path("", include("apps.rfq.urls")),
    path("", include("apps.catalog.urls")),
    path("", include("apps.order.urls")),
    path("", include("apps.notification.urls")),
    path("", include("apps.points.urls")),
    path("", include("apps.simplequote.urls")),
    path("", include("apps.project.urls")),
    path("", include("apps.contract.urls")),
    path("", include("apps.payment.urls")),
    path("", include("apps.chat.urls")),
    path("", include("apps.blog.urls")),
    path("", include("apps.ops.urls")),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
