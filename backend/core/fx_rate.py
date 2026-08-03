"""CNY→KRW 参考汇率：exchangerate.host + Redis 24h 缓存。"""

from __future__ import annotations

import json
import logging
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone

from django.conf import settings
from django.core.cache import cache

logger = logging.getLogger(__name__)

FALLBACK_CNY_TO_KRW = 190.0
CACHE_KEY = "fx:cny_krw:v1"
SOFT_CACHE_KEY = "fx:cny_krw:last_ok:v1"
SOFT_CACHE_TTL_SECONDS = 7 * 24 * 3600
HTTP_TIMEOUT_SECONDS = 8


def _now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _from_unix(ts) -> str:
    try:
        return (
            datetime.fromtimestamp(int(ts), tz=timezone.utc)
            .replace(microsecond=0)
            .isoformat()
            .replace("+00:00", "Z")
        )
    except (TypeError, ValueError, OSError):
        return _now_iso()


def _payload(rate: float, as_of: str, source: str, stale: bool = False) -> dict:
    return {
        "cny_to_krw": round(float(rate), 4),
        "as_of": as_of,
        "source": source,
        "pair": "CNY/KRW",
        "stale": bool(stale),
    }


def _fallback(stale: bool = False) -> dict:
    soft = cache.get(SOFT_CACHE_KEY)
    if isinstance(soft, dict) and soft.get("cny_to_krw"):
        out = dict(soft)
        out["source"] = "cache"
        out["stale"] = True
        out["pair"] = "CNY/KRW"
        return out
    return _payload(FALLBACK_CNY_TO_KRW, _now_iso(), "fallback", stale=stale)


def _http_get_json(url: str) -> dict:
    req = urllib.request.Request(url, headers={"Accept": "application/json", "User-Agent": "oemco-fx/1.0"})
    with urllib.request.urlopen(req, timeout=HTTP_TIMEOUT_SECONDS) as resp:
        raw = resp.read().decode("utf-8")
    data = json.loads(raw)
    if not isinstance(data, dict):
        raise ValueError("invalid JSON object")
    return data


def _fetch_via_convert(base: str, access_key: str) -> dict | None:
    qs = urllib.parse.urlencode(
        {"access_key": access_key, "from": "CNY", "to": "KRW", "amount": "1"}
    )
    data = _http_get_json(f"{base}/convert?{qs}")
    if data.get("success") is False:
        return None
    rate = data.get("result")
    if rate is None and isinstance(data.get("info"), dict):
        rate = data["info"].get("rate")
    try:
        rate_f = float(rate)
    except (TypeError, ValueError):
        return None
    if rate_f <= 0:
        return None
    ts = None
    if isinstance(data.get("info"), dict):
        ts = data["info"].get("timestamp")
    as_of = _from_unix(ts) if ts is not None else _now_iso()
    return _payload(rate_f, as_of, "exchangerate.host")


def _fetch_via_live(base: str, access_key: str) -> dict | None:
    qs = urllib.parse.urlencode({"access_key": access_key, "currencies": "CNY,KRW"})
    data = _http_get_json(f"{base}/live?{qs}")
    if data.get("success") is False:
        return None
    quotes = data.get("quotes") or {}
    try:
        usd_cny = float(quotes.get("USDCNY"))
        usd_krw = float(quotes.get("USDKRW"))
    except (TypeError, ValueError):
        return None
    if usd_cny <= 0 or usd_krw <= 0:
        return None
    rate_f = usd_krw / usd_cny
    as_of = _from_unix(data.get("timestamp"))
    return _payload(rate_f, as_of, "exchangerate.host")


def _fetch_remote() -> dict | None:
    access_key = (getattr(settings, "EXCHANGERATE_HOST_ACCESS_KEY", None) or "").strip()
    if not access_key:
        return None
    base = (getattr(settings, "EXCHANGERATE_HOST_BASE_URL", None) or "https://api.exchangerate.host").rstrip(
        "/"
    )
    try:
        converted = _fetch_via_convert(base, access_key)
        if converted:
            return converted
    except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, ValueError, json.JSONDecodeError) as exc:
        logger.warning("fx convert failed: %s", type(exc).__name__)
    try:
        live = _fetch_via_live(base, access_key)
        if live:
            return live
    except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, ValueError, json.JSONDecodeError) as exc:
        logger.warning("fx live failed: %s", type(exc).__name__)
    return None


def get_cny_krw_rate() -> dict:
    """返回工作台参考汇率；优先 Redis 24h 缓存，失败则软缓存或 190。"""
    cached = cache.get(CACHE_KEY)
    if isinstance(cached, dict) and cached.get("cny_to_krw"):
        out = dict(cached)
        out["source"] = "cache"
        out["pair"] = "CNY/KRW"
        out["stale"] = False
        return out

    remote = _fetch_remote()
    if remote:
        ttl = int(getattr(settings, "EXCHANGERATE_CACHE_TTL_SECONDS", 86400) or 86400)
        cache.set(CACHE_KEY, remote, ttl)
        cache.set(SOFT_CACHE_KEY, remote, SOFT_CACHE_TTL_SECONDS)
        return remote

    return _fallback(stale=True)
