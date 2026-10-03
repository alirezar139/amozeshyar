"""Development-only live error log (logs/live.log).

Collects in one place, as they happen:
  - every API response with status >= 400, with its (truncated) body, so a
    "nothing happens when I click" can be traced to the exact validation
    error or permission denial;
  - server tracebacks (via the `django.request` logger, see dev settings);
  - errors reported by the browser (JS errors, Vue errors, failed fetches)
    through `client_log`.

Wired up only in config/settings/dev.py and when DEBUG is on.
"""
import json
import logging

from rest_framework import permissions
from rest_framework.decorators import api_view, authentication_classes, permission_classes, throttle_classes
from rest_framework.response import Response

logger = logging.getLogger("live")
client_logger = logging.getLogger("live.client")

MAX_BODY_CHARS = 800
# Expected 401s: the frontend probes the refresh cookie on every page load.
QUIET_PATHS = ("/api/v1/auth/refresh/",)


def _user_label(request) -> str:
    user = getattr(request, "user", None)
    return user.email if getattr(user, "is_authenticated", False) else "anon"


class APIErrorLogMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        # An expired access token (401) is routine: the frontend refreshes it and retries.
        if response.status_code == 401:
            return response
        if response.status_code >= 400 and request.path.startswith("/api/") and request.path not in QUIET_PATHS:
            body = getattr(response, "content", b"")[:MAX_BODY_CHARS * 4].decode("utf-8", "replace")
            level = logging.ERROR if response.status_code >= 500 else logging.WARNING
            logger.log(
                level, "API %s %s -> %s (%s) %s",
                request.method, request.path, response.status_code, _user_label(request), body[:MAX_BODY_CHARS],
            )
        return response


@api_view(["POST"])
@authentication_classes([])
@permission_classes([permissions.AllowAny])
@throttle_classes([])
def client_log(request):
    """Browser-side errors: {level, kind, message, url, detail, user}."""
    data = request.data if isinstance(request.data, dict) else {}
    level = logging.WARNING if data.get("level") == "warning" else logging.ERROR
    detail = data.get("detail")
    if detail and not isinstance(detail, str):
        detail = json.dumps(detail, ensure_ascii=False)
    client_logger.log(
        level, "BROWSER %s on %s (%s): %s%s",
        str(data.get("kind", "error"))[:40],
        str(data.get("url", "?"))[:300],
        str(data.get("user") or "anon")[:120],
        str(data.get("message", ""))[:MAX_BODY_CHARS],
        f"\n    {detail[:2000]}" if detail else "",
    )
    return Response(status=204)
