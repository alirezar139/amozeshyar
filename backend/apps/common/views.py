import logging

from django.core.cache import cache
from django.db import connection
from drf_spectacular.utils import extend_schema, inline_serializer
from rest_framework import permissions, serializers
from rest_framework.response import Response
from rest_framework.views import APIView

logger = logging.getLogger(__name__)


def _database_ok() -> bool:
    with connection.cursor() as cursor:
        cursor.execute("SELECT 1")
        return cursor.fetchone() == (1,)


def _cache_ok() -> bool:
    # The cache is Redis in production; login puzzles and throttles stop working without it.
    cache.set("healthcheck", "1", timeout=10)
    return cache.get("healthcheck") == "1"


CHECKS = {"database": _database_ok, "cache": _cache_ok}


class HealthView(APIView):
    """Liveness check for uptime monitors: 200 when every dependency answers, 503 otherwise.

    Public and unthrottled on purpose: throttling itself lives in the cache,
    so a throttled health check would fail with the wrong error exactly when
    the cache is down. nginx still rate-limits it like the rest of /api/.
    Only names which check failed, never the underlying error.
    """

    permission_classes = (permissions.AllowAny,)
    authentication_classes = ()
    throttle_classes = ()

    @extend_schema(
        responses=inline_serializer(
            "Health", {"status": serializers.CharField(), "checks": serializers.DictField(child=serializers.CharField())}
        )
    )
    def get(self, request):
        checks = {}
        for name, check in CHECKS.items():
            try:
                checks[name] = "ok" if check() else "failed"
            except Exception:
                logger.exception("Health check %s failed", name)
                checks[name] = "failed"
        healthy = all(result == "ok" for result in checks.values())
        return Response({"status": "ok" if healthy else "failed", "checks": checks}, status=200 if healthy else 503)
