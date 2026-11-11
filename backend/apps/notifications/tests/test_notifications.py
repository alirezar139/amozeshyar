"""Notifications reach the channels each event allows, never break the caller, and never put
secrets or full addresses in the logs."""
import logging

import pytest
from django.core import mail
from django.db import transaction

from apps.accounts.models import User
from apps.courses.models import Category, Course
from apps.instructors.models import InstructorProfile
from apps.messaging.models import Message
from apps.notifications import channels
from apps.notifications.service import deliver, notify
from apps.payments.models import Order, OrderItem
from apps.payments.services import fulfil_order

pytestmark = pytest.mark.django_db(transaction=True)


@pytest.fixture
def site():
    teacher = User.objects.create_user(email="t@example.com", password="x", role=User.Role.ADMIN)
    InstructorProfile.objects.create(user=teacher, is_site_owner=True, site_name="کلاس سارا")
    category = Category.objects.create(name="c", slug="c")
    return Course.objects.create(instructor=teacher.instructor_profile, category=category, title="پایتون", status=Course.Status.PUBLISHED)


@pytest.fixture
def student():
    return User.objects.create_user(email="reza.karimi@gmail.com", password="x", phone_number="09121234567")


def test_a_paid_order_sends_a_receipt_in_the_chat_and_by_email(site, student):
    order = Order.objects.create(user=student, total_amount=250000)
    OrderItem.objects.create(order=order, course=site, price_at_purchase=250000)
    with transaction.atomic():
        fulfil_order(order, ref_id="REF77")

    receipt = Message.objects.get(bot="notify")
    assert "«پایتون»" in receipt.text and "REF77" in receipt.text and "250٬000 تومان" in receipt.text
    assert mail.outbox and mail.outbox[0].to == [student.email] and "کلاس سارا" in mail.outbox[0].subject


def test_nothing_is_sent_when_the_transaction_rolls_back(site, student):
    order = Order.objects.create(user=student, total_amount=1000)
    OrderItem.objects.create(order=order, course=site, price_at_purchase=1000)
    with pytest.raises(RuntimeError), transaction.atomic():
        fulfil_order(order)
        raise RuntimeError("payment rolled back")
    assert not Message.objects.filter(bot="notify").exists() and mail.outbox == []


def test_sensitive_events_never_go_to_the_chat(site, student):
    assert deliver(student.id, "password_reset", {"link": "https://x/secret-token", "minutes": 30}) == ["email"]
    assert not Message.objects.filter(text__contains="secret-token").exists()


def test_disabled_channels_are_skipped(site, student, settings):
    settings.NOTIFICATION_CHANNELS = ["inbox"]
    assert deliver(student.id, "refund_completed", {"order_id": 1, "amount": 1000}) == ["inbox"]
    assert mail.outbox == []


def test_a_failing_channel_is_logged_masked_and_the_rest_still_go(site, student, settings, caplog, monkeypatch):
    def broken(*args, **kwargs):
        raise ConnectionRefusedError("smtp down")

    monkeypatch.setattr(channels, "send_mail", broken)
    with caplog.at_level(logging.INFO):
        sent = deliver(student.id, "payment_succeeded", {"order_id": 9, "courses": ["پایتون"], "amount": 1000})

    assert sent == ["inbox"]
    logged = " ".join(r.getMessage() for r in caplog.records)
    assert "reza.karimi@gmail.com" not in logged and "r***@g***" in logged


def test_masks():
    assert channels.mask_email("reza.karimi@gmail.com") == "r***@g***"
    assert channels.mask_phone("09121234567") == "0912***67"


def test_unknown_events_are_a_programming_error(student):
    with pytest.raises(ValueError):
        notify(student, "no_such_event")
