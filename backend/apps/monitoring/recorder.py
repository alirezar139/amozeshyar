"""Write ErrorEvents without ever breaking the request that triggered them."""
import logging
import random
from datetime import timedelta

from django.utils import timezone

from .models import ErrorEvent

logger = logging.getLogger(__name__)

KEEP_DAYS = 14
MAX_EVENTS = 5000
MESSAGE_CHARS = 1000
DETAIL_CHARS = 8000


def user_fields(user) -> dict:
    if getattr(user, "is_authenticated", False):
        return {"user": user, "user_label": user.email}
    return {"user": None, "user_label": ""}


def record(**fields) -> ErrorEvent | None:
    fields["message"] = str(fields.get("message", ""))[:MESSAGE_CHARS]
    fields["detail"] = str(fields.get("detail") or "")[:DETAIL_CHARS]
    try:
        event = ErrorEvent.objects.create(**fields)
    except Exception:  # monitoring must never take a request down with it
        logger.exception("could not record error event")
        return None
    if random.random() < 0.02:
        prune()
    return event


def prune():
    try:
        ErrorEvent.objects.filter(created_at__lt=timezone.now() - timedelta(days=KEEP_DAYS)).delete()
        cutoff = ErrorEvent.objects.values_list("id", flat=True)[MAX_EVENTS:MAX_EVENTS + 1].first()
        if cutoff:
            ErrorEvent.objects.filter(id__lte=cutoff, reports__isnull=True).delete()
    except Exception:
        logger.exception("could not prune error events")
