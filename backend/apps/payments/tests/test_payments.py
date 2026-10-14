from datetime import timedelta

import pytest
from django.utils import timezone
from rest_framework.test import APIClient

from apps.accounts.models import User
from apps.courses.models import Category, Course
from apps.enrollments.models import Enrollment
from apps.instructors.models import InstructorProfile
from apps.payments import views
from apps.payments.gateways.base import PaymentGateway, PaymentVerifyResult
from apps.payments.models import Order, OrderItem, Payment
from apps.payments.tasks import reconcile_pending_payments

pytestmark = pytest.mark.django_db


class FakeGateway(PaymentGateway):
    """Answers verify() from a dict of authority -> paid?, and counts the calls."""

    def __init__(self, paid=None, broken=()):
        self.paid = paid or {}
        self.broken = set(broken)
        self.calls = []

    def verify(self, authority, amount):
        self.calls.append(authority)
        if authority in self.broken:
            raise ConnectionError("gateway down")
        if self.paid.get(authority):
            return PaymentVerifyResult(success=True, ref_id=f"ref-{authority}", raw_response={"data": {"code": 100}})
        return PaymentVerifyResult(success=False, raw_response={"data": {"code": -51}})


@pytest.fixture
def gateway(monkeypatch):
    fake = FakeGateway()
    monkeypatch.setattr(views, "get_gateway", lambda: fake)
    return fake


@pytest.fixture
def course():
    teacher = User.objects.create_user(email="t@example.com", password="x", role=User.Role.ADMIN)
    InstructorProfile.objects.create(user=teacher, is_site_owner=True)
    category = Category.objects.create(name="c", slug="c")
    return Course.objects.create(
        instructor=teacher.instructor_profile, category=category, title="Python", status=Course.Status.PUBLISHED
    )


def make_payment(course, authority, minutes_ago=0, email=None):
    student = User.objects.create_user(email=email or f"{authority}@example.com", password="x")
    order = Order.objects.create(user=student, total_amount=100000)
    OrderItem.objects.create(order=order, course=course, price_at_purchase=100000)
    payment = Payment.objects.create(order=order, authority=authority)
    Payment.objects.filter(id=payment.id).update(created_at=timezone.now() - timedelta(minutes=minutes_ago))
    payment.refresh_from_db()
    return payment


def callback(authority):
    return APIClient().get("/api/v1/payments/callback/", {"Authority": authority})


def is_enrolled(payment):
    return Enrollment.objects.filter(student=payment.order.user).count()


def test_callback_enrolls_once_even_when_hit_twice(course, gateway):
    payment = make_payment(course, "A1")
    gateway.paid["A1"] = True

    first, second = callback("A1"), callback("A1")

    assert first.status_code == second.status_code == 302
    assert first["Location"].endswith("status=paid") and second["Location"].endswith("status=paid")
    payment.refresh_from_db()
    assert payment.status == Payment.Status.VERIFIED and payment.ref_id == "ref-A1"
    assert payment.order.status == Order.Status.PAID
    assert is_enrolled(payment) == 1
    assert gateway.calls == ["A1"]  # the repeat hit doesn't ask the gateway again


def test_unpaid_callback_fails_without_enrolling(course, gateway):
    payment = make_payment(course, "A2")

    response = callback("A2")

    assert response["Location"].endswith("status=failed")
    payment.refresh_from_db()
    assert payment.status == Payment.Status.FAILED
    assert is_enrolled(payment) == 0


def test_reconcile_enrolls_a_buyer_who_never_came_back(course, gateway):
    payment = make_payment(course, "B1", minutes_ago=20)
    gateway.paid["B1"] = True

    assert reconcile_pending_payments() == 1
    assert reconcile_pending_payments() == 0  # second run finds nothing left to do

    payment.refresh_from_db()
    assert payment.status == Payment.Status.VERIFIED
    assert is_enrolled(payment) == 1
    assert callback("B1")["Location"].endswith("status=paid")  # a late callback still shows success


def test_reconcile_leaves_recent_payments_alone_and_fails_only_old_ones(course, gateway):
    fresh = make_payment(course, "C1", minutes_ago=5)  # buyer may still be paying
    unsure = make_payment(course, "C2", minutes_ago=30)  # unpaid so far, but not given up on
    old = make_payment(course, "C3", minutes_ago=90)  # unpaid for long enough to call it failed

    assert reconcile_pending_payments() == 0

    assert "C1" not in gateway.calls
    for payment, expected in ((fresh, "initiated"), (unsure, "initiated"), (old, "failed")):
        payment.refresh_from_db()
        assert payment.status == expected


def test_reconcile_keeps_going_when_the_gateway_errors_on_one_payment(course, gateway):
    make_payment(course, "D1", minutes_ago=20)
    good = make_payment(course, "D2", minutes_ago=20)
    gateway.broken.add("D1")
    gateway.paid["D2"] = True

    assert reconcile_pending_payments() == 1
    assert is_enrolled(good) == 1
