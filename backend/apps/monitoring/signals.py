"""Server crashes (unhandled exceptions), with the traceback."""
import traceback

from django.core.signals import got_request_exception
from django.dispatch import receiver

from .recorder import record, user_fields


@receiver(got_request_exception)
def record_crash(sender, request=None, **kwargs):
    if request is None:
        return
    # Sent from inside Django's except block, so the exception is still current.
    tb = traceback.format_exc()
    last_line = tb.strip().splitlines()[-1] if tb.strip() else "Unhandled exception"
    record(
        source="server", level="error", method=request.method, path=request.path[:300], status=500,
        message=last_line, detail=tb, **user_fields(getattr(request, "user", None)),
    )
    request._monitoring_crash_recorded = True
