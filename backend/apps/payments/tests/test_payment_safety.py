"""A buyer is charged at most once per course, and an unclear answer from ZarinPal is never
turned into "failed" or "paid" (PAY-01, PAY-02).

ZarinPal returns the money of any payment that is never *verified*, so a duplicate payment is
handled by simply not verifying it. The concurrency tests run on real Postgres transactions
(`transaction=True`) with threads, because row locks only mean something across connections.
"""
import threading
import time
from datetime import timedelta
from unittest import mock

import pytest
import requests
from django.db import connection
from django.utils import timezone
from rest_framework.test import APIClient

from apps.accounts.models import User
from apps.courses.models import Course
from apps.enrollments.models import Enrollment
from apps.payments import views
from apps.payments.gateways.base import (
    PaymentGateway,
    PaymentGatewayUnavailable,
    PaymentRequestResult,
    PaymentVerifyResult,
)
from apps.payments.gateways.zarinpal import ZarinPalGateway
from apps.payments.models import Order, Payment
from apps.payments.tasks import reconcile_pending_payments


class Gateway(PaymentGateway):
    """Hands out a new authority per request; `paid` authorities verify, `down` ones raise."""

    def __init__(self, delay=0.0):
        self.delay = delay
        self.issued = 0
        self.paid, self.down, self.unclear = set(), set(), set()
        self.verified = []
        self.lock = threading.Lock()

    def create_payment_request(self, order, callback_url):
        time.sleep(self.delay)
        with self.lock:
            self.issued += 1
            authority = f"A{self.issued}"
        return PaymentRequestResult(redirect_url=self.redirect_url(authority), authority=authority)

    def redirect_url(self, authority):
        return f"https://pay.example/{authority}"

    def verify(self, authority, amount):
        time.sleep(self.delay)
        with self.lock:
            self.verified.append(authority)
        if authority in self.down:
            raise PaymentGatewayUnavailable("zarinpal unreachable")
        if authority in self.unclear:
            return PaymentVerifyResult(success=False, definite=False, raw_response={"errors": {"code": -12}})
        if authority in self.paid:
            return PaymentVerifyResult(success=True, ref_id=f"ref-{authority}", raw_response={"data": {"code": 100}})
        return PaymentVerifyResult(success=False, definite=True, raw_response={"errors": {"code": -51}})


@pytest.fixture
def gateway(monkeypatch):
    fake = Gateway()
    monkeypatch.setattr(views, "get_gateway", lambda: fake)
    return fake


@pytest.fixture
def paid_course(course):
    course.price = 200000
    course.save(update_fields=["price"])
    return course


@pytest.fixture
def student(db):
    return User.objects.create_user(email="s@example.com", password="x")


def client_for(user):
    client = APIClient()
    client.force_authenticate(user)
    return client


def create_order(user, *courses):
    return client_for(user).post("/api/v1/payments/orders/", {"course_ids": [c.id for c in courses]}, format="json")


def initiate(user, order_id):
    return client_for(user).post(f"/api/v1/payments/initiate/{order_id}/")


def callback(authority, status="OK"):
    return APIClient().get("/api/v1/payments/callback/", {"Authority": authority, "Status": status})


def outcome(response):
    return response["Location"].rsplit("status=", 1)[-1]


def run_together(*calls):
    """Start every call at the same moment on its own DB connection; return their results."""
    barrier = threading.Barrier(len(calls))
    results = [None] * len(calls)

    def worker(i, call):
        try:
            barrier.wait()
            results[i] = call()
        finally:
            connection.close()

    threads = [threading.Thread(target=worker, args=(i, c)) for i, c in enumerate(calls)]
    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=30)
    return results


def second_course(paid_course, title="Go"):
    return Course.objects.create(
        instructor=paid_course.instructor, category=paid_course.category, title=title,
        status=Course.Status.PUBLISHED, price=100000,
    )


# ---------- PAY-01: one order, one live payment ----------

@pytest.mark.django_db
def test_paying_again_while_a_payment_is_open_reuses_it(student, paid_course, gateway):
    order_id = create_order(student, paid_course).data["id"]

    first, second = initiate(student, order_id), initiate(student, order_id)

    assert first.status_code == second.status_code == 200
    assert first.data["redirect_url"] == second.data["redirect_url"]
    assert Payment.objects.filter(order_id=order_id).count() == 1
    assert gateway.issued == 1


@pytest.mark.django_db
def test_an_expired_payment_is_replaced_by_a_new_one(student, paid_course, gateway):
    order_id = create_order(student, paid_course).data["id"]
    initiate(student, order_id)
    Payment.objects.update(created_at=timezone.now() - timedelta(minutes=20))

    assert initiate(student, order_id).data["redirect_url"].endswith("/A2")
    assert Payment.objects.filter(order_id=order_id).count() == 2


@pytest.mark.django_db(transaction=True)
def test_simultaneous_pay_clicks_create_one_payment(student, paid_course, monkeypatch):
    slow = Gateway(delay=0.3)
    monkeypatch.setattr(views, "get_gateway", lambda: slow)
    order_id = create_order(student, paid_course).data["id"]

    responses = run_together(*[lambda: initiate(student, order_id)] * 4)

    assert {r.status_code for r in responses} == {200}
    assert len({r.data["redirect_url"] for r in responses}) == 1
    assert Payment.objects.filter(order_id=order_id).count() == 1


@pytest.mark.django_db
def test_second_paid_payment_of_an_order_is_not_verified(student, paid_course, gateway):
    """Both of an order's payments were paid at ZarinPal: only the first is verified, so the
    second one's money goes back to the buyer automatically."""
    order_id = create_order(student, paid_course).data["id"]
    initiate(student, order_id)
    Payment.objects.update(created_at=timezone.now() - timedelta(minutes=20))
    initiate(student, order_id)
    gateway.paid |= {"A1", "A2"}

    assert outcome(callback("A1")) == "paid"
    assert outcome(callback("A2")) == "canceled"

    assert gateway.verified == ["A1"]
    assert Payment.objects.get(authority="A1").status == Payment.Status.VERIFIED
    duplicate = Payment.objects.get(authority="A2")
    assert duplicate.status == Payment.Status.CANCELED and duplicate.note
    assert Enrollment.objects.filter(student=student).count() == 1


@pytest.mark.django_db(transaction=True)
def test_simultaneous_identical_callbacks_verify_and_enroll_once(student, paid_course, monkeypatch):
    slow = Gateway(delay=0.3)
    monkeypatch.setattr(views, "get_gateway", lambda: slow)
    order_id = create_order(student, paid_course).data["id"]
    initiate(student, order_id)
    slow.paid.add("A1")

    responses = run_together(*[lambda: callback("A1")] * 4)

    assert {outcome(r) for r in responses} == {"paid"}
    assert slow.verified == ["A1"]
    assert Enrollment.objects.filter(student=student, course=paid_course).count() == 1
    assert Order.objects.get(id=order_id).status == Order.Status.PAID


# ---------- PAY-01: one course, one order ----------

@pytest.mark.django_db
def test_ordering_the_same_courses_again_returns_the_open_order(student, paid_course, gateway):
    first = create_order(student, paid_course)
    second = create_order(student, paid_course)

    assert first.status_code == 201 and second.status_code == 200
    assert first.data["id"] == second.data["id"]
    assert Order.objects.filter(user=student).count() == 1


@pytest.mark.django_db
def test_a_new_order_cancels_an_abandoned_overlapping_one(student, paid_course, gateway):
    other = second_course(paid_course)
    old_id = create_order(student, paid_course).data["id"]

    new = create_order(student, paid_course, other)

    assert new.status_code == 201
    assert Order.objects.get(id=old_id).status == Order.Status.CANCELED


@pytest.mark.django_db
def test_no_new_order_while_another_one_for_the_course_is_being_paid(student, paid_course, gateway):
    other = second_course(paid_course)
    old_id = create_order(student, paid_course).data["id"]
    initiate(student, old_id)  # the buyer is on ZarinPal's page right now

    response = create_order(student, paid_course, other)

    assert response.status_code == 409
    assert Order.objects.get(id=old_id).status == Order.Status.PENDING


@pytest.mark.django_db
def test_initiate_refuses_an_order_for_a_course_already_bought(student, paid_course, gateway):
    order_id = create_order(student, paid_course).data["id"]
    Enrollment.objects.create(student=student, course=paid_course)  # e.g. enrolled by hand meanwhile

    response = initiate(student, order_id)

    assert response.status_code == 409
    assert gateway.issued == 0
    assert Order.objects.get(id=order_id).status == Order.Status.CANCELED


@pytest.mark.django_db
def test_late_payment_for_a_course_bought_through_another_order_is_not_verified(student, paid_course, gateway):
    a = create_order(student, paid_course).data["id"]
    initiate(student, a)
    Payment.objects.update(created_at=timezone.now() - timedelta(minutes=20))  # A1 looks abandoned
    b = create_order(student, paid_course).data["id"]  # same courses: the same order comes back
    assert a == b
    initiate(student, b)
    gateway.paid |= {"A1", "A2"}

    assert outcome(callback("A2")) == "paid"
    assert outcome(callback("A1")) == "canceled"
    assert gateway.verified == ["A2"]
    assert Enrollment.objects.filter(student=student).count() == 1


@pytest.mark.django_db(transaction=True)
def test_two_orders_paid_at_once_for_the_same_course_charge_once(student, paid_course, monkeypatch):
    """Payments on two different orders (an old abandoned one paid late, and a fresh one) whose
    callbacks arrive together: the buyer is locked, so only one is verified."""
    slow = Gateway(delay=0.3)
    monkeypatch.setattr(views, "get_gateway", lambda: slow)
    other = second_course(paid_course)
    first = create_order(student, paid_course).data["id"]
    initiate(student, first)
    Payment.objects.update(created_at=timezone.now() - timedelta(minutes=20))
    Order.objects.filter(id=first).update(created_at=timezone.now() - timedelta(minutes=20))
    second = create_order(student, paid_course, other).data["id"]  # cancels the abandoned one
    initiate(student, second)
    slow.paid |= {"A1", "A2"}

    results = run_together(lambda: callback("A1"), lambda: callback("A2"))

    assert sorted(outcome(r) for r in results) == ["canceled", "paid"]
    assert len(slow.verified) == 1
    assert Enrollment.objects.filter(student=student, course=paid_course).count() == 1


# ---------- PAY-02: an unclear answer is not an answer ----------

@pytest.mark.django_db
def test_callback_when_zarinpal_is_unreachable_keeps_the_payment_open(student, paid_course, gateway, caplog):
    order_id = create_order(student, paid_course).data["id"]
    initiate(student, order_id)
    gateway.down.add("A1")

    response = callback("A1")

    assert response.status_code == 302 and outcome(response) == "pending"
    assert Payment.objects.get(authority="A1").status == Payment.Status.INITIATED
    assert Order.objects.get(id=order_id).status == Order.Status.PENDING
    assert not Enrollment.objects.exists()
    assert any("A1" in r.getMessage() for r in caplog.records)


@pytest.mark.django_db
def test_unclear_gateway_answer_is_pending_not_failed(student, paid_course, gateway):
    order_id = create_order(student, paid_course).data["id"]
    initiate(student, order_id)
    gateway.unclear.add("A1")

    assert outcome(callback("A1")) == "pending"
    assert Payment.objects.get(authority="A1").status == Payment.Status.INITIATED


@pytest.mark.django_db
def test_reconcile_finishes_a_payment_the_callback_could_not_verify(student, paid_course, gateway):
    order_id = create_order(student, paid_course).data["id"]
    initiate(student, order_id)
    gateway.down.add("A1")
    gateway.paid.add("A1")
    callback("A1")

    gateway.down.clear()
    Payment.objects.update(created_at=timezone.now() - timedelta(minutes=20))
    assert reconcile_pending_payments() == 1
    assert Enrollment.objects.filter(student=student, course=paid_course).exists()
    assert outcome(callback("A1")) == "paid"


@pytest.mark.django_db
def test_reconcile_never_fails_a_payment_it_could_not_ask_about(student, paid_course, gateway):
    order_id = create_order(student, paid_course).data["id"]
    initiate(student, order_id)
    Payment.objects.update(created_at=timezone.now() - timedelta(hours=3))
    gateway.down.add("A1")

    reconcile_pending_payments()

    assert Payment.objects.get(authority="A1").status == Payment.Status.INITIATED


@pytest.mark.django_db
def test_definite_refusal_still_fails(student, paid_course, gateway):
    order_id = create_order(student, paid_course).data["id"]
    initiate(student, order_id)

    assert outcome(callback("A1", status="NOK")) == "failed"
    assert Payment.objects.get(authority="A1").status == Payment.Status.FAILED
    assert outcome(callback("A1", status="NOK")) == "failed"  # a repeat is answered the same way


def zarinpal_answer(status_code, body=None, invalid_json=False):
    response = mock.Mock(status_code=status_code)
    response.json = mock.Mock(side_effect=ValueError("no json")) if invalid_json else mock.Mock(return_value=body)
    response.raise_for_status = mock.Mock(side_effect=requests.HTTPError("5xx") if status_code >= 500 else None)
    return response


@pytest.mark.parametrize(
    "failure",
    [
        {"side_effect": requests.Timeout("slow")},
        {"side_effect": requests.ConnectionError("down")},
        {"return_value": zarinpal_answer(502, {})},
        {"return_value": zarinpal_answer(200, invalid_json=True)},
    ],
)
def test_zarinpal_verify_reports_outages_as_unavailable(failure):
    with mock.patch("apps.payments.gateways.zarinpal.requests.post", **failure):
        with pytest.raises(PaymentGatewayUnavailable):
            ZarinPalGateway().verify("A", 1000)


@pytest.mark.parametrize(
    ("body", "success", "definite"),
    [
        ({"data": {"code": 100, "ref_id": 7}, "errors": []}, True, True),
        ({"data": {"code": 101, "ref_id": 7}, "errors": []}, True, True),  # verified before
        ({"data": [], "errors": {"code": -51, "message": "not paid"}}, False, True),
        ({"data": [], "errors": {"code": -54, "message": "invalid authority"}}, False, True),
        ({"data": [], "errors": {"code": -12, "message": "too many attempts"}}, False, False),
        ({"data": [], "errors": {"code": -10, "message": "terminal not valid"}}, False, False),
        ({"unexpected": True}, False, False),
    ],
)
def test_zarinpal_verify_tells_a_refusal_from_an_unclear_answer(body, success, definite):
    with mock.patch("apps.payments.gateways.zarinpal.requests.post", return_value=zarinpal_answer(400 if not success else 200, body)):
        result = ZarinPalGateway().verify("A", 1000)
    assert (result.success, result.definite) == (success, definite)
