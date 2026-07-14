try:
    from .celery import app as celery_app
except ImportError:  # pragma: no cover - web image without celery extras
    celery_app = None

__all__ = ("celery_app",)
