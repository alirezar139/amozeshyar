"""Where a notification can go: the site's own messenger, email, SMS.

Each channel answers `available_for(user)` (configured, and the user has an address for it)
and `send(user, message) -> bool`. A channel never raises: a failed delivery is logged with
the recipient masked and the message body left out, and the caller carries on.

SMS has no provider built in. To connect one (Kavenegar, Ghasedak, Melipayamak...), write a
class with `send(phone: str, text: str) -> None` that raises on failure and point the
`SMS_PROVIDER` setting at it (dotted path). See docs/architecture.md, «اطلاع‌رسانی».
"""
import logging

from django.conf import settings
from django.core.mail import send_mail
from django.utils.module_loading import import_string

logger = logging.getLogger(__name__)


def mask_email(email: str) -> str:
    name, _, domain = (email or "").partition("@")
    return f"{name[:1]}***@{domain[:1]}***" if domain else "***"


def mask_phone(phone: str) -> str:
    return f"{phone[:4]}***{phone[-2:]}" if len(phone or "") >= 7 else "***"


class Channel:
    name = ""

    def available_for(self, user) -> bool:
        raise NotImplementedError

    def send(self, user, message) -> bool:
        raise NotImplementedError


class InboxChannel(Channel):
    """A message from the site's assistant in the user's direct chat with the instructor."""

    name = "inbox"

    def available_for(self, user) -> bool:
        return user.is_active and user.role == user.Role.STUDENT

    def send(self, user, message) -> bool:
        from apps.messaging.services import send_bot_message

        try:
            return send_bot_message(user, message.text, bot="notify") is not None
        except Exception:
            logger.exception("inbox notification to user %s failed", user.id)
            return False


class EmailChannel(Channel):
    name = "email"

    def available_for(self, user) -> bool:
        return settings.EMAIL_ENABLED and bool(user.email)

    def send(self, user, message) -> bool:
        try:
            send_mail(message.subject, message.text, settings.DEFAULT_FROM_EMAIL, [user.email])
            return True
        except Exception as exc:  # SMTP errors, timeouts...
            logger.warning("email to %s failed: %s", mask_email(user.email), type(exc).__name__)
            return False


class SmsChannel(Channel):
    name = "sms"

    def available_for(self, user) -> bool:
        return bool(settings.SMS_PROVIDER) and bool(user.phone_number)

    def send(self, user, message) -> bool:
        try:
            import_string(settings.SMS_PROVIDER)().send(user.phone_number, message.sms or message.text)
            return True
        except Exception as exc:
            logger.warning("sms to %s failed: %s", mask_phone(user.phone_number), type(exc).__name__)
            return False


CHANNELS = {c.name: c for c in (InboxChannel(), EmailChannel(), SmsChannel())}
