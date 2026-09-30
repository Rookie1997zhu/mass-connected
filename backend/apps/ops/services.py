"""超级管理员运行监控：即时资源、存储扫描、现有业务表汇总。"""

import logging
import os
import socket
import time
from datetime import datetime, timedelta
from pathlib import Path

from django.apps import apps
from django.conf import settings
from django.db import connection
from django.db.models import Count, FileField, Sum
from django.db.models.functions import TruncDate
from django.utils import timezone

logger = logging.getLogger("apps.ops")

STORAGE_CACHE_KEY = "ops:storage:snapshot"
STORAGE_CACHE_SECONDS = 600
PROBE_TIMEOUT_SECONDS = 2
ORPHAN_MIN_AGE = timedelta(hours=24)
WORKER_QUEUES = (
    ("slicer", "celery"),
    ("heavy", "heavy"),
    ("translate", "translate"),
)


def collect_runtime():
    metrics = _read_host_metrics()
    return {
        "cpu": metrics["cpu"],
        "memory": metrics["memory"],
        "disk": metrics["disk"],
        "services": _probe_services(),
        "history": [],
    }


def _read_host_metrics():
    empty = {"cpu": None, "memory": None, "disk": None}
    try:
        import psutil
    except ImportError:
        logger.exception("ops host metrics unavailable: psutil is not installed")
        return empty

    cpu = None
    memory = None
    disk = None
    try:
        load_1m = None
        if hasattr(psutil, "getloadavg"):
            load_1m = round(psutil.getloadavg()[0], 2)
        cpu = {
            "percent": round(psutil.cpu_percent(interval=0.2), 1),
            "load_1m": load_1m,
        }
    except Exception:
        logger.exception("ops cpu metrics failed")

    try:
        virt = psutil.virtual_memory()
        memory = {"used_bytes": int(virt.used), "total_bytes": int(virt.total)}
    except Exception:
        logger.exception("ops memory metrics failed")

    try:
        target = Path(settings.MEDIA_ROOT)
        if not target.exists():
            target = target.parent
        usage = psutil.disk_usage(str(target))
        disk = {
            "used_bytes": int(usage.used),
            "total_bytes": int(usage.total),
            "path": str(target),
        }
    except Exception:
        logger.exception("ops disk metrics failed", extra={"path": str(settings.MEDIA_ROOT)})

    return {"cpu": cpu, "memory": memory, "disk": disk}


def _probe_services():
    return [
        _probe_database(),
        _probe_redis(),
        _probe_chat(),
        *_probe_workers(),
        _probe_oss(),
    ]


def _elapsed_ms(started):
    return int((time.perf_counter() - started) * 1000)


def _probe_database():
    started = time.perf_counter()
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            cursor.fetchone()
    except Exception:
        logger.exception("ops database probe failed")
        return {"key": "mysql", "status": "error", "latency_ms": None}
    return {"key": "mysql", "status": "ok", "latency_ms": _elapsed_ms(started)}


def _probe_redis():
    started = time.perf_counter()
    try:
        from django.core.cache import cache

        cache.set("ops:probe", "1", 5)
        if cache.get("ops:probe") != "1":
            logger.error("ops redis probe read mismatch")
            return {"key": "redis", "status": "error", "latency_ms": None}
    except Exception:
        logger.exception("ops redis probe failed")
        return {"key": "redis", "status": "error", "latency_ms": None}
    return {"key": "redis", "status": "ok", "latency_ms": _elapsed_ms(started)}


def _probe_chat():
    host = os.environ.get("CHAT_WS_HOST", "chat-ws")
    port = int(os.environ.get("CHAT_WS_PORT", "8001"))
    started = time.perf_counter()
    try:
        with socket.create_connection((host, port), timeout=PROBE_TIMEOUT_SECONDS):
            pass
    except Exception:
        logger.exception("ops chat probe failed", extra={"host": host, "port": port})
        return {"key": "chat_ws", "status": "error", "latency_ms": None}
    return {"key": "chat_ws", "status": "ok", "latency_ms": _elapsed_ms(started)}


def _inspect_worker_queues():
    from config.celery import app as celery_app

    started = time.perf_counter()
    inspector = celery_app.control.inspect(timeout=PROBE_TIMEOUT_SECONDS)
    queues = inspector.active_queues() or {}
    found = set()
    for queue_list in queues.values():
        for item in queue_list or []:
            name = item.get("name") if isinstance(item, dict) else None
            if name:
                found.add(name)
    return found, _elapsed_ms(started)


def _probe_workers():
    try:
        found, latency_ms = _inspect_worker_queues()
    except Exception:
        logger.exception("ops worker inspect failed")
        found, latency_ms = None, None
    services = []
    for key, queue_name in WORKER_QUEUES:
        if found is not None and queue_name in found:
            services.append({"key": key, "status": "ok", "latency_ms": latency_ms})
        else:
            services.append({"key": key, "status": "error", "latency_ms": None})
    return services


def _probe_oss():
    if not getattr(settings, "USE_OSS", False):
        return {"key": "oss", "status": "disabled", "latency_ms": None}
    started = time.perf_counter()
    try:
        client, bucket_name = _oss_client()
        client.head_bucket(Bucket=bucket_name)
    except Exception:
        logger.exception("ops oss probe failed")
        return {"key": "oss", "status": "error", "latency_ms": None}
    return {"key": "oss", "status": "ok", "latency_ms": _elapsed_ms(started)}


def _oss_client():
    from django.core.files.storage import default_storage

    client = default_storage.connection.meta.client
    bucket_name = default_storage.bucket_name
    return client, bucket_name


def read_storage(recount, page, page_size):
    from django.core.cache import cache

    snapshot = None if recount else cache.get(STORAGE_CACHE_KEY)
    if recount:
        snapshot = _scan_storage()
        cache.set(STORAGE_CACHE_KEY, snapshot, STORAGE_CACHE_SECONDS)
    elif snapshot is None:
        return _empty_storage(page, page_size)

    orphans = snapshot.get("orphans") or []
    start = (page - 1) * page_size
    page_items = orphans[start : start + page_size]
    return {
        "cached": True,
        "counted_at": snapshot.get("counted_at"),
        "local": snapshot.get("local"),
        "oss": snapshot.get("oss"),
        "orphan_total": len(orphans),
        "orphans": {
            "items": page_items,
            "page": page,
            "page_size": page_size,
            "total": len(orphans),
        },
    }


def _empty_storage(page, page_size):
    enabled = bool(getattr(settings, "USE_OSS", False))
    return {
        "cached": False,
        "counted_at": None,
        "local": None,
        "oss": {
            "enabled": enabled,
            "status": "disabled" if not enabled else "unknown",
            "bytes": None,
            "file_count": None,
        },
        "orphan_total": 0,
        "orphans": {"items": [], "page": page, "page_size": page_size, "total": 0},
    }


def _scan_storage():
    referenced = _referenced_storage_keys()
    cutoff = timezone.now() - ORPHAN_MIN_AGE
    local_bytes, local_count, local_orphans = _scan_local(referenced, cutoff)
    oss = _scan_oss(referenced, cutoff)
    orphans = local_orphans + oss.pop("orphans")
    orphans.sort(key=lambda item: item["modified_at"])
    return {
        "counted_at": timezone.now().isoformat(),
        "local": {"bytes": local_bytes, "file_count": local_count},
        "oss": oss,
        "orphans": orphans,
    }


def _normalize_storage_key(value):
    return str(value).replace("\\", "/").lstrip("/")


def _referenced_storage_keys():
    keys = set()
    for model in apps.get_models():
        fields = [
            field
            for field in model._meta.get_fields()
            if getattr(field, "concrete", False) and isinstance(field, FileField)
        ]
        if not fields:
            continue
        names = [field.attname for field in fields]
        for row in model.objects.values_list(*names).iterator():
            for value in row:
                if value:
                    keys.add(_normalize_storage_key(value))
    return keys


def _scan_local(referenced, cutoff):
    root = Path(settings.MEDIA_ROOT)
    total_bytes = 0
    file_count = 0
    orphans = []
    if not root.exists():
        return total_bytes, file_count, orphans
    for path in root.rglob("*"):
        if not path.is_file():
            continue
        stat = path.stat()
        file_count += 1
        total_bytes += stat.st_size
        key = _normalize_storage_key(path.relative_to(root).as_posix())
        modified = datetime.fromtimestamp(stat.st_mtime, tz=timezone.get_current_timezone())
        if key not in referenced and modified < cutoff:
            orphans.append(
                {
                    "key": key,
                    "bytes": int(stat.st_size),
                    "modified_at": modified.isoformat(),
                    "location": "local",
                }
            )
    return total_bytes, file_count, orphans


def _scan_oss(referenced, cutoff):
    enabled = bool(getattr(settings, "USE_OSS", False))
    payload = {
        "enabled": enabled,
        "status": "disabled" if not enabled else "ok",
        "bytes": None,
        "file_count": None,
        "orphans": [],
    }
    if not enabled:
        return payload
    try:
        client, bucket_name = _oss_client()
        paginator = client.get_paginator("list_objects_v2")
        total_bytes = 0
        file_count = 0
        orphans = []
        for page in paginator.paginate(Bucket=bucket_name):
            for obj in page.get("Contents") or []:
                key = _normalize_storage_key(obj.get("Key") or "")
                if not key or key.endswith("/"):
                    continue
                size = int(obj.get("Size") or 0)
                file_count += 1
                total_bytes += size
                modified = obj.get("LastModified")
                if modified is not None and timezone.is_naive(modified):
                    modified = timezone.make_aware(modified, timezone.get_current_timezone())
                if key not in referenced and modified is not None and modified < cutoff:
                    orphans.append(
                        {
                            "key": key,
                            "bytes": size,
                            "modified_at": modified.isoformat(),
                            "location": "oss",
                        }
                    )
        payload["bytes"] = total_bytes
        payload["file_count"] = file_count
        payload["orphans"] = orphans
    except Exception:
        logger.exception("ops oss listing failed")
        payload["status"] = "error"
        payload["orphans"] = []
    return payload


def read_behavior(days):
    start_dt = _period_start(days)
    today = timezone.localdate()
    dates = [today - timedelta(days=offset) for offset in range(days - 1, -1, -1)]

    from apps.accounts.models import User
    from apps.blog.models import BlogPost
    from apps.inquiry.models import Inquiry
    from apps.order.models import Order
    from apps.rfq.models import RFQ

    series = {
        "new_members": _daily_counts(User.objects.filter(role="member"), start_dt),
        "rfqs": _daily_counts(RFQ.objects.all(), start_dt),
        "orders": _daily_counts(Order.objects.all(), start_dt),
        "inquiries": _daily_counts(Inquiry.objects.all(), start_dt),
    }
    daily = []
    for day in dates:
        key = day.isoformat()
        daily.append(
            {
                "date": key,
                "new_members": series["new_members"].get(key, 0),
                "rfqs": series["rfqs"].get(key, 0),
                "orders": series["orders"].get(key, 0),
                "inquiries": series["inquiries"].get(key, 0),
            }
        )
    blog_views = BlogPost.objects.aggregate(total=Sum("view_count")).get("total") or 0
    return {
        "days": days,
        "totals": {
            "new_members": sum(series["new_members"].values()),
            "rfqs": sum(series["rfqs"].values()),
            "orders": sum(series["orders"].values()),
            "inquiries": sum(series["inquiries"].values()),
            "blog_views": int(blog_views),
            "members_logged_in": User.objects.filter(
                role="member", last_login__gte=start_dt
            ).count(),
        },
        "daily": daily,
    }


def _period_start(days):
    today = timezone.localdate()
    start_date = today - timedelta(days=days - 1)
    start_clock = datetime.combine(start_date, datetime.min.time())
    return timezone.make_aware(start_clock, timezone.get_current_timezone())


def _daily_counts(queryset, start_dt):
    rows = (
        queryset.filter(created_at__gte=start_dt)
        .annotate(day=TruncDate("created_at"))
        .values("day")
        .annotate(total=Count("id"))
    )
    counts = {}
    for row in rows:
        day = row["day"]
        if day is None:
            continue
        if isinstance(day, datetime):
            day = timezone.localtime(day).date() if timezone.is_aware(day) else day.date()
        counts[day.isoformat()] = row["total"]
    return counts
