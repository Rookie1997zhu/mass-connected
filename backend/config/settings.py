import os
from datetime import timedelta
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

_INSECURE_SECRET_KEYS = frozenset(
    {
        "",
        "dev-insecure-change-me",
        "change-me-in-production",
    }
)

SECRET_KEY = os.environ.get("DJANGO_SECRET_KEY", "dev-insecure-change-me")
DEBUG = os.environ.get("DJANGO_DEBUG", "false").lower() == "true"

if not DEBUG and SECRET_KEY in _INSECURE_SECRET_KEYS:
    raise RuntimeError(
        "DJANGO_SECRET_KEY must be set to a strong unique value when DJANGO_DEBUG=false"
    )

ALLOWED_HOSTS = [
    h.strip()
    for h in os.environ.get("DJANGO_ALLOWED_HOSTS", "localhost,127.0.0.1,backend").split(",")
    if h.strip()
]

# 仅当反向代理终止 TLS 且 DJANGO_SECURE_SSL=true 时启用（本地/局域网 HTTP 保持关闭）
SECURE_SSL = os.environ.get("DJANGO_SECURE_SSL", "false").lower() == "true"
if SECURE_SSL:
    SECURE_SSL_REDIRECT = True
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SECURE_HSTS_SECONDS = int(os.environ.get("DJANGO_SECURE_HSTS_SECONDS", "31536000"))
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = True
    SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
    SECURE_REDIRECT_EXEMPT = [r"^api/health$"]

INSTALLED_APPS = [
    "daphne",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "corsheaders",
    "rest_framework",
    "rest_framework_simplejwt",
    "rest_framework_simplejwt.token_blacklist",
    "channels",
    "core",
    "apps.accounts",
    "apps.i18n",
    "apps.content",
    "apps.inquiry",
    "apps.rfq",
    "apps.catalog",
    "apps.order",
    "apps.notification",
    "apps.points",
    "apps.simplequote",
    "apps.project",
    "apps.contract",
    "apps.payment",
    "apps.chat",
    "apps.blog",
    "apps.content_pipeline",
    "apps.ops",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "core.middleware.RequestIdMiddleware",
]

ROOT_URLCONF = "config.urls"
WSGI_APPLICATION = "config.wsgi.application"
ASGI_APPLICATION = "config.asgi.application"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.mysql",
        "NAME": os.environ.get("DB_NAME", "oem_db"),
        "USER": os.environ.get("DB_USER", "oem_user"),
        "PASSWORD": os.environ.get("DB_PASSWORD", "oem_pass"),
        "HOST": os.environ.get("DB_HOST", "mysql"),
        "PORT": os.environ.get("DB_PORT", "3306"),
        "OPTIONS": {"charset": "utf8mb4"},
    }
}

AUTH_USER_MODEL = "accounts.User"

AUTHENTICATION_BACKENDS = [
    "apps.accounts.backends.EmailAuthBackend",
    "django.contrib.auth.backends.ModelBackend",
]

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LANGUAGE_CODE = os.environ.get("DEFAULT_LANGUAGE", "ko")
TIME_ZONE = "Asia/Seoul"
USE_I18N = True
USE_TZ = True

STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
MEDIA_URL = os.environ.get("MEDIA_URL", "/media/")
# 即使 USE_OSS=true 仍保留：preview_cache、tmp/parse、OSS 临时落盘等本地目录
MEDIA_ROOT = os.environ.get("MEDIA_ROOT", str(BASE_DIR / "media"))

USE_OSS = os.environ.get("USE_OSS", "false").lower() == "true"
if USE_OSS:
    _oss_access_key = os.environ.get("OSS_ACCESS_KEY_ID", "").strip()
    _oss_secret_key = os.environ.get("OSS_ACCESS_KEY_SECRET", "").strip()
    _oss_bucket = os.environ.get("OSS_BUCKET_NAME", "").strip()
    _oss_endpoint = os.environ.get(
        "OSS_ENDPOINT", "https://oss-ap-northeast-2.aliyuncs.com"
    ).strip()
    _oss_region = os.environ.get("OSS_REGION", "ap-northeast-2").strip()
    _oss_expire = int(os.environ.get("OSS_QUERYSTRING_EXPIRE", "3600"))
    if not _oss_access_key or not _oss_secret_key or not _oss_bucket:
        raise RuntimeError(
            "USE_OSS=true requires OSS_ACCESS_KEY_ID, OSS_ACCESS_KEY_SECRET, OSS_BUCKET_NAME"
        )
    STORAGES = {
        "default": {
            "BACKEND": "storages.backends.s3.S3Storage",
            "OPTIONS": {
                "access_key": _oss_access_key,
                "secret_key": _oss_secret_key,
                "bucket_name": _oss_bucket,
                "endpoint_url": _oss_endpoint,
                "region_name": _oss_region,
                "signature_version": "s3v4",
                "addressing_style": "virtual",
                "default_acl": None,
                "querystring_auth": True,
                "querystring_expire": _oss_expire,
                "file_overwrite": False,
            },
        },
        "staticfiles": {
            "BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage",
        },
    }

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

CORS_ALLOWED_ORIGINS = [
    o.strip()
    for o in os.environ.get(
        "CORS_ALLOWED_ORIGINS",
        "http://localhost,http://127.0.0.1,http://localhost:5173,http://localhost:5174",
    ).split(",")
    if o.strip()
]
CORS_ALLOW_CREDENTIALS = True

# Redis 分库：DB0 cache、DB1 Celery、DB2 Channels
REDIS_URL = os.environ.get("REDIS_URL", "redis://redis:6379/0")
REDIS_CELERY_URL = os.environ.get("REDIS_CELERY_URL", "redis://redis:6379/1")
REDIS_CHANNELS_URL = os.environ.get("REDIS_CHANNELS_URL", "redis://redis:6379/2")

CACHES = {
    "default": {
        "BACKEND": "django_redis.cache.RedisCache",
        "LOCATION": REDIS_URL,
        "OPTIONS": {"CLIENT_CLASS": "django_redis.client.DefaultClient"},
    }
}

CHANNEL_LAYERS = {
    "default": {
        "BACKEND": "channels_redis.core.RedisChannelLayer",
        "CONFIG": {
            "hosts": [REDIS_CHANNELS_URL],
            "capacity": 1500,
            "expiry": 60,
        },
    }
}

# Celery（print3d 切片 Worker）；独立 DB1，避免与 cache/channels 键冲突
CELERY_BROKER_URL = os.environ.get("CELERY_BROKER_URL", REDIS_CELERY_URL)
CELERY_RESULT_BACKEND = os.environ.get("CELERY_RESULT_BACKEND", REDIS_CELERY_URL)

CHAT_RATE_LIMIT_PER_MINUTE = int(os.environ.get("CHAT_RATE_LIMIT_PER_MINUTE", "30"))
CHAT_MESSAGE_MAX_LENGTH = int(os.environ.get("CHAT_MESSAGE_MAX_LENGTH", "4000"))
CHAT_ONLINE_TTL_SECONDS = int(os.environ.get("CHAT_ONLINE_TTL_SECONDS", "60"))
CELERY_TASK_TRACK_STARTED = True
CELERY_ACCEPT_CONTENT = ["json"]
CELERY_TASK_SERIALIZER = "json"
CELERY_RESULT_SERIALIZER = "json"
CELERY_WORKER_PREFETCH_MULTIPLIER = 1
CELERY_TASK_ACKS_LATE = True
CELERY_TASK_ALWAYS_EAGER = os.environ.get("CELERY_TASK_ALWAYS_EAGER", "false").lower() == "true"
CELERY_TASK_ROUTES = {
    "simplequote.run_stp_parse": {"queue": "heavy"},
    "simplequote.run_drawing_parse": {"queue": "heavy"},
    "simplequote.run_preview_convert": {"queue": "heavy"},
    "simplequote.send_notification_email": {"queue": "heavy"},
    "accounts.send_verification_email": {"queue": "heavy"},
    "chat.run_message_translate": {"queue": "translate"},
    "content_pipeline.run_daily_batch": {"queue": "heavy"},
    "content_pipeline.process_video_item": {"queue": "heavy"},
    "content_pipeline.finalize_daily_run": {"queue": "heavy"},
}
PRUSA_SLICER_PATH = os.environ.get("PRUSA_SLICER_PATH", "prusa-slicer")
PRINT3D_SLICE_JOB_TTL_HOURS = int(os.environ.get("PRINT3D_SLICE_JOB_TTL_HOURS", "24"))
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")
GEMINI_MODEL = os.environ.get("GEMINI_MODEL", "gemini-2.5-flash")

# 博客 MCP 机器凭证（环境变量；空则仅 JWT 可用）
BLOG_MCP_API_KEY = os.environ.get("BLOG_MCP_API_KEY", "")
BLOG_MCP_AUTHOR_EMAIL = os.environ.get("BLOG_MCP_AUTHOR_EMAIL", "")

# 每日 YouTube→博客 内容流水线
CONTENT_PIPELINE_ENABLED = os.environ.get("CONTENT_PIPELINE_ENABLED", "false").lower() == "true"
CONTENT_PIPELINE_DAILY_COUNT = int(os.environ.get("CONTENT_PIPELINE_DAILY_COUNT", "10"))
CONTENT_PIPELINE_KEYWORDS = os.environ.get("CONTENT_PIPELINE_KEYWORDS", "")
CONTENT_PIPELINE_LANGUAGES = os.environ.get("CONTENT_PIPELINE_LANGUAGES", "zh,ko")
CONTENT_PIPELINE_SCHEDULE_CRON = os.environ.get("CONTENT_PIPELINE_SCHEDULE_CRON", "0 9 * * *")
CONTENT_PIPELINE_TIMEZONE = os.environ.get("CONTENT_PIPELINE_TIMEZONE", "Asia/Shanghai")
CONTENT_PIPELINE_AUTHOR_EMAIL = os.environ.get("CONTENT_PIPELINE_AUTHOR_EMAIL", "") or BLOG_MCP_AUTHOR_EMAIL
YOUTUBE_API_KEY = os.environ.get("YOUTUBE_API_KEY", "")
CELERY_TIMEZONE = os.environ.get("CELERY_TIMEZONE", TIME_ZONE)


def _content_pipeline_cron_parts():
    raw = (CONTENT_PIPELINE_SCHEDULE_CRON or "0 9 * * *").strip().split()
    minute = 0
    hour = 9
    try:
        if len(raw) >= 1 and raw[0].isdigit():
            minute = int(raw[0])
        if len(raw) >= 2 and raw[1].isdigit():
            hour = int(raw[1])
    except ValueError:
        minute, hour = 0, 9
    return minute, hour


from celery.schedules import crontab  # noqa: E402

_cp_minute, _cp_hour = _content_pipeline_cron_parts()
CELERY_BEAT_SCHEDULE = {
    "content-pipeline-daily": {
        "task": "content_pipeline.run_daily_batch",
        "schedule": crontab(minute=_cp_minute, hour=_cp_hour),
        "options": {"queue": "heavy"},
    },
}

# 工作台参考汇率（exchangerate.host）；密钥仅环境变量，不进仓库
EXCHANGERATE_HOST_ACCESS_KEY = os.environ.get("EXCHANGERATE_HOST_ACCESS_KEY", "")
EXCHANGERATE_HOST_BASE_URL = os.environ.get(
    "EXCHANGERATE_HOST_BASE_URL", "https://api.exchangerate.host"
).rstrip("/")
EXCHANGERATE_CACHE_TTL_SECONDS = int(os.environ.get("EXCHANGERATE_CACHE_TTL_SECONDS", "86400"))

THROTTLE_ANON = os.environ.get("THROTTLE_ANON", "120/min")
THROTTLE_USER = os.environ.get("THROTTLE_USER", "600/min")
THROTTLE_LOGIN = os.environ.get("THROTTLE_LOGIN", "10/min")
THROTTLE_REGISTER = os.environ.get("THROTTLE_REGISTER", "5/min")
THROTTLE_INQUIRY = os.environ.get("THROTTLE_INQUIRY", "10/min")
THROTTLE_AI_TRANSLATE = os.environ.get("THROTTLE_AI_TRANSLATE", "20/min")
THROTTLE_WS_TICKET = os.environ.get("THROTTLE_WS_TICKET", "30/min")
THROTTLE_VERIFY_EMAIL = os.environ.get("THROTTLE_VERIFY_EMAIL", "3/min")
THROTTLE_BLOG_COMMENT = os.environ.get("THROTTLE_BLOG_COMMENT", "20/min")

FRONTEND_BASE_URL = os.environ.get("FRONTEND_BASE_URL", "http://localhost").rstrip("/")

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": (
        "rest_framework_simplejwt.authentication.JWTAuthentication",
    ),
    "DEFAULT_PERMISSION_CLASSES": ("rest_framework.permissions.IsAuthenticated",),
    "DEFAULT_THROTTLE_CLASSES": (
        "rest_framework.throttling.AnonRateThrottle",
        "rest_framework.throttling.UserRateThrottle",
    ),
    "DEFAULT_THROTTLE_RATES": {
        "anon": THROTTLE_ANON,
        "user": THROTTLE_USER,
        "login": THROTTLE_LOGIN,
        "register": THROTTLE_REGISTER,
        "inquiry": THROTTLE_INQUIRY,
        "ai_translate": THROTTLE_AI_TRANSLATE,
        "ws_ticket": THROTTLE_WS_TICKET,
        "verify_email": THROTTLE_VERIFY_EMAIL,
        "blog_comment": THROTTLE_BLOG_COMMENT,
    },
    "DEFAULT_PAGINATION_CLASS": "core.pagination.StandardPagination",
    "PAGE_SIZE": 20,
    "EXCEPTION_HANDLER": "core.exceptions.custom_exception_handler",
    "DEFAULT_RENDERER_CLASSES": ("rest_framework.renderers.JSONRenderer",),
    # Allow business query ?format=dxf|pdf on download APIs (not DRF renderer negotiation)
    "URL_FORMAT_OVERRIDE": None,
}

SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(
        minutes=int(os.environ.get("JWT_ACCESS_TOKEN_LIFETIME_MINUTES", "30"))
    ),
    "REFRESH_TOKEN_LIFETIME": timedelta(
        days=int(os.environ.get("JWT_REFRESH_TOKEN_LIFETIME_DAYS", "7"))
    ),
    "ROTATE_REFRESH_TOKENS": True,
    "BLACKLIST_AFTER_ROTATION": True,
    "AUTH_HEADER_TYPES": ("Bearer",),
}

EMAIL_BACKEND = os.environ.get(
    "EMAIL_BACKEND",
    "django.core.mail.backends.console.EmailBackend",
)
EMAIL_HOST = os.environ.get("EMAIL_HOST", "")
EMAIL_PORT = int(os.environ.get("EMAIL_PORT", "587"))
EMAIL_HOST_USER = os.environ.get("EMAIL_HOST_USER", "")
EMAIL_HOST_PASSWORD = os.environ.get("EMAIL_HOST_PASSWORD", "")
EMAIL_USE_TLS = os.environ.get("EMAIL_USE_TLS", "true").lower() == "true"
DEFAULT_FROM_EMAIL = os.environ.get("DEFAULT_FROM_EMAIL", "noreply@massconnected.local")

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "structured": {
            "format": "%(asctime)s %(levelname)s %(name)s request_id=%(request_id)s %(message)s",
        },
    },
    "filters": {
        "request_id": {"()": "core.logging.RequestIdFilter"},
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "structured",
            "filters": ["request_id"],
        },
    },
    "root": {"handlers": ["console"], "level": "INFO"},
}
