"""The notifications the site sends, their wording, and which channels each may use.

`sensitive` events (the password reset link) never go to the in-app chat, where anyone who
later opens the account could read them, and their text is never logged.
"""
from dataclasses import dataclass

from django.conf import settings


@dataclass
class Message:
    subject: str
    text: str
    sms: str = ""  # shorter text for SMS; falls back to `text`


@dataclass
class Event:
    channels: tuple[str, ...]
    build: object  # (user, **context) -> Message
    sensitive: bool = False


def _site_name() -> str:
    from apps.instructors.site import get_site_owner

    owner = get_site_owner()
    return (owner.site_name if owner and owner.site_name else "") or "آموزش‌یار"


def _amount(value) -> str:
    return f"{int(value):,} تومان".replace(",", "٬") if int(value) else "رایگان"


def password_reset(user, *, link: str, minutes: int) -> Message:
    site = _site_name()
    return Message(
        subject=f"بازیابی رمز عبور — {site}",
        text=(
            f"سلام {user.first_name or ''}\n\n"
            f"برای ساختن رمز تازه‌ی حساب‌تان در «{site}» این لینک را باز کنید:\n{link}\n\n"
            f"لینک تا {minutes} دقیقه و فقط یک بار کار می‌کند. اگر شما درخواست نداده‌اید، این پیام را نادیده بگیرید؛ "
            "رمز فعلی‌تان عوض نمی‌شود."
        ),
        sms=f"{site}: لینک بازیابی رمز ({minutes} دقیقه، یک‌بار مصرف):\n{link}",
    )


def password_changed(user) -> Message:
    site = _site_name()
    return Message(
        subject=f"رمز عبور شما عوض شد — {site}",
        text=(
            f"رمز عبور حساب شما در «{site}» همین حالا عوض شد و از همه‌ی دستگاه‌ها خارج شدید.\n"
            "اگر این کار را شما نکرده‌اید، فوراً به مدرس پیام دهید."
        ),
    )


def payment_succeeded(user, *, order_id: int, courses: list[str], amount, ref_id: str = "") -> Message:
    site = _site_name()
    titles = "، ".join(f"«{c}»" for c in courses)
    ref = f"\nکد پیگیری: {ref_id}" if ref_id else ""
    return Message(
        subject=f"رسید خرید سفارش {order_id} — {site}",
        text=(
            f"خرید شما ثبت شد و دسترسی به {titles} باز است.\n"
            f"شماره‌ی سفارش: {order_id}\nمبلغ: {_amount(amount)}{ref}"
        ),
    )


def refund_completed(user, *, order_id: int, amount, reference: str = "") -> Message:
    site = _site_name()
    ref = f"\nشناسه‌ی استرداد: {reference}" if reference else ""
    return Message(
        subject=f"استرداد وجه سفارش {order_id} — {site}",
        text=f"مبلغ {_amount(amount)} سفارش {order_id} به شما بازگردانده شد و دسترسی دوره‌های آن بسته شد.{ref}",
    )


def refund_rejected(user, *, order_id: int, note: str = "") -> Message:
    site = _site_name()
    reason = f"\nتوضیح مدرس: {note}" if note else ""
    return Message(
        subject=f"درخواست استرداد سفارش {order_id} — {site}",
        text=f"درخواست استرداد وجه سفارش {order_id} پذیرفته نشد.{reason}",
    )


EVENTS = {
    "password_reset": Event(channels=("email", "sms"), build=password_reset, sensitive=True),
    "password_changed": Event(channels=("email", "sms", "inbox"), build=password_changed),
    "payment_succeeded": Event(channels=("inbox", "email"), build=payment_succeeded),
    "refund_completed": Event(channels=("inbox", "email", "sms"), build=refund_completed),
    "refund_rejected": Event(channels=("inbox", "email"), build=refund_rejected),
}


def enabled_channels(event: Event) -> list[str]:
    return [c for c in event.channels if c in settings.NOTIFICATION_CHANNELS]
