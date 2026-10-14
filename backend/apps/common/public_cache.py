"""Short-lived cache for the public pages every visitor loads the same way.

The homepage, the course catalog and the category list are identical for
every anonymous visitor, and they're what a traffic spike hits first. Each
answer is kept for PUBLIC_CACHE_SECONDS under a shared version number that
any write to the underlying models bumps, so the instructor sees their own
edit at once instead of after the timeout.

Only cache answers that don't depend on who is asking.
"""
import time

from django.core.cache import cache
from django.db import transaction
from rest_framework.response import Response

PUBLIC_CACHE_SECONDS = 30
VERSION_KEY = "public:version"


def _fresh() -> int:
    # Time-based, so a lost and recreated version never matches entries cached under an old one.
    return time.time_ns() // 1000


def _version() -> int:
    version = cache.get(VERSION_KEY)
    if version is None:
        cache.add(VERSION_KEY, _fresh(), None)
        version = cache.get(VERSION_KEY, 0)
    return int(version)


def _bump() -> None:
    try:
        cache.incr(VERSION_KEY)
    except ValueError:
        cache.set(VERSION_KEY, _fresh(), None)


def invalidate(**kwargs) -> None:
    """Signal receiver: forget every cached public answer.

    Bumped right away and again after the commit: a request that rebuilt the
    cache from the not-yet-committed (old) rows in between would otherwise
    keep serving them until the timeout.
    """
    _bump()
    transaction.on_commit(_bump)


def cached_response(request, build) -> Response:
    """``build()`` returns the response data; it runs only on a cache miss.

    Keyed by host and full path (query string included), so filters and
    pages are cached separately and absolute URLs never leak across hosts.
    """
    key = f"public:{_version()}:{request.get_host()}:{request.get_full_path()}"
    data = cache.get(key)
    if data is None:
        data = build()
        cache.set(key, data, PUBLIC_CACHE_SECONDS)
    return Response(data)
