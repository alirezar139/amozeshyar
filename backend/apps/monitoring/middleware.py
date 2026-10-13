import logging

from .recorder import record, user_fields

logger = logging.getLogger("live")

BODY_CHARS = 2000
# 401: expired access token, the frontend refreshes and retries. 429: throttling, which would
# otherwise let anyone flood the log. The refresh probe 401s on every visitor's first load.
SKIP_STATUSES = {401, 429}
QUIET_PATHS = ("/api/v1/auth/refresh/", "/api/v1/monitoring/client-log/")


class APIErrorLogMiddleware:
    """Records every /api/ response with status >= 400 together with what the server said, so
    "nothing happens when I click" can be traced to the exact validation error or permission."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        status = response.status_code
        if (
            status < 400 or status in SKIP_STATUSES
            or not request.path.startswith("/api/") or request.path in QUIET_PATHS
            or getattr(request, "_monitoring_crash_recorded", False)
        ):
            return response
        body = getattr(response, "content", b"")[:BODY_CHARS * 4].decode("utf-8", "replace")[:BODY_CHARS]
        level = "error" if status >= 500 else "warning"
        who = user_fields(getattr(request, "user", None))
        logger.log(
            logging.ERROR if level == "error" else logging.WARNING, "API %s %s -> %s (%s) %s",
            request.method, request.path, status, who["user_label"] or "anon", body,
        )
        record(
            source="api", level=level, method=request.method, path=request.path[:300], status=status,
            message=f"{request.method} {request.path} → {status}", detail=body, **who,
        )
        return response
