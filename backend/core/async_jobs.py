"""Redis-backed short-lived async job status for heavy Celery tasks."""

from __future__ import annotations

import uuid
from typing import Any

from django.core.cache import cache

JOB_KEY_PREFIX = "async_job:"
JOB_TTL_SECONDS = 3600
JOB_STATUSES = frozenset({"pending", "running", "done", "failed"})


def _key(job_id: str) -> str:
    return f"{JOB_KEY_PREFIX}{job_id}"


def create_job(kind: str, user_id: int, meta: dict | None = None) -> str:
    job_id = uuid.uuid4().hex
    payload: dict[str, Any] = {
        "job_id": job_id,
        "kind": kind,
        "user_id": int(user_id) if user_id is not None else None,
        "status": "pending",
        "result": None,
        "error_code": None,
        "error_message": None,
        "meta": meta or {},
    }
    cache.set(_key(job_id), payload, JOB_TTL_SECONDS)
    return job_id


def update_job(job_id: str, **fields) -> dict | None:
    key = _key(job_id)
    payload = cache.get(key)
    if not payload:
        return None
    if "status" in fields and fields["status"] not in JOB_STATUSES:
        raise ValueError(f"invalid job status: {fields['status']}")
    payload.update(fields)
    cache.set(key, payload, JOB_TTL_SECONDS)
    return payload


def get_job(job_id: str) -> dict | None:
    if not job_id:
        return None
    payload = cache.get(_key(job_id))
    return payload if isinstance(payload, dict) else None
