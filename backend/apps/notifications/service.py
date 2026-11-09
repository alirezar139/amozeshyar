"""`notify(user, event, **context)`: tell a user something, through every channel that event
allows and the site has configured.

Delivery happens after the surrounding transaction commits (a rolled-back payment never sends
a receipt) and inline rather than through Celery: the single worker can spend an hour on a
video, and a password reset link can't wait that long. Channels have their own timeouts and
never raise, so a mail server outage can't break the request that triggered it.
"""
import logging

from django.contrib.auth import get_user_model
from django.db import transaction

from .channels import CHANNELS
from .events import EVENTS, enabled_channels

logger = logging.getLogger(__name__)


def deliver(user_id: int, event_name: str, context: dict) -> list[str]:
    """Send now; returns the channels that accepted it."""
    event = EVENTS[event_name]
    user = get_user_model().objects.filter(pk=user_id).first()
    if user is None:
        return []
    message = event.build(user, **context)
    sent = [name for name in enabled_channels(event) if CHANNELS[name].available_for(user) and CHANNELS[name].send(user, message)]
    # Never the text or the context: for sensitive events they hold a secret link.
    logger.info("notification %s to user %s via %s", event_name, user_id, ",".join(sent) or "nothing")
    return sent


def notify(user, event_name: str, **context) -> None:
    if event_name not in EVENTS:
        raise ValueError(f"unknown notification {event_name}")
    transaction.on_commit(lambda: deliver(user.pk, event_name, context))
