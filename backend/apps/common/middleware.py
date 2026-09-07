"""Temporary diagnostic middleware for tracking down the admin-calendar
"freezes on click" report — logs method, path, user, status, and wall-clock
duration for every request to logs/requests.log, so a hang shows up as
either a request that never logs a finish line at all (frontend/browser
issue, request never reached or never returned) or one with an unusually
large duration (a genuine slow view)."""

import logging
import time

logger = logging.getLogger("requests")


class RequestTimingMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        start = time.monotonic()
        logger.info("START %s %s", request.method, request.path)
        response = self.get_response(request)
        duration_ms = (time.monotonic() - start) * 1000
        user = getattr(request, "user", None)
        user_label = user.email if getattr(user, "is_authenticated", False) else "anon"
        logger.info(
            "DONE  %s %s -> %s (%s) in %.1fms",
            request.method, request.path, response.status_code, user_label, duration_ms,
        )
        return response
