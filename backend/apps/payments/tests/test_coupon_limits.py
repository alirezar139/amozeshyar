"""A coupon is never used more than `max_uses` times, overall or per buyer, even under
simultaneous checkouts (PAY-03).

An order that is waiting to be paid holds one use of its coupon for COUPON_HOLD, so two buyers
can't both be sent to the gateway for the last use and then both get it.
"""
import threading
from datetime import timedelta

import pytest
from django.db import connection
from django.utils import timezone
from rest_framework.test import APIClient

from apps.accounts.models import User
from apps.courses.models import Course
from apps.payments import views
from apps.payments.models import Coupon, Order, Payment
from apps.payments.services import COUPON_HOLD

from .test_payment_safety import Gateway, callback, outcome


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


def make_coupon(**kwargs):
    now = timezone.now()
    return Coupon.objects.create(code="OFF", valid_from=now - timedelta(days=1), valid_to=now + timedelta(days=1), **kwargs)


def buyer(n):
    return User.objects.create_user(email=f"b{n}@example.com", password="x")


def order_with_coupon(user, *courses, code="OFF"):
    client = APIClient()
    client.force_authenticate(user)
    return client.post("/api/v1/payments/orders/", {"course_ids": [c.id for c in courses], "coupon_code": code}, format="json")


def pay(user, order_id, gateway):
    client = APIClient()
    client.force_authenticate(user)
    authority = client.post(f"/api/v1/payments/initiate/{order_id}/").data["redirect_url"].rsplit("/", 1)[-1]
    gateway.paid.add(authority)
    return callback(authority)


@pytest.mark.django_db
def test_an_unpaid_order_holds_the_last_use(paid_course, gateway):
    make_coupon(discount_percent=50, max_uses=1)

    assert order_with_coupon(buyer(1), paid_course).status_code == 201
    second = order_with_coupon(buyer(2), paid_course)

    assert second.status_code == 400 and "coupon_code" in second.data


@pytest.mark.django_db
def test_a_hold_expires_and_frees_the_use(paid_course, gateway):
    make_coupon(discount_percent=50, max_uses=1)
    order_with_coupon(buyer(1), paid_course)
    Order.objects.update(updated_at=timezone.now() - COUPON_HOLD - timedelta(minutes=1))

    assert order_with_coupon(buyer(2), paid_course).status_code == 201


@pytest.mark.django_db
def test_paying_counts_the_use_once(paid_course, gateway):
    coupon = make_coupon(discount_percent=50, max_uses=2)
    student = buyer(1)
    order_id = order_with_coupon(student, paid_course).data["id"]

    assert outcome(pay(student, order_id, gateway)) == "paid"
    callback("A1")  # a repeated callback

    coupon.refresh_from_db()
    assert coupon.used_count == 1


@pytest.mark.django_db
def test_a_late_payment_cannot_push_a_coupon_past_its_limit(paid_course, gateway):
    """Buyer 1's hold expired and buyer 2 used the last slot; buyer 1 then pays anyway.
    That payment is not verified (ZarinPal refunds it) instead of exceeding max_uses."""
    coupon = make_coupon(discount_percent=50, max_uses=1)
    late, quick = buyer(1), buyer(2)
    late_order = order_with_coupon(late, paid_course).data["id"]
    client = APIClient()
    client.force_authenticate(late)
    client.post(f"/api/v1/payments/initiate/{late_order}/")  # authority A1
    Order.objects.update(updated_at=timezone.now() - COUPON_HOLD - timedelta(minutes=1))
    Payment.objects.update(created_at=timezone.now() - COUPON_HOLD - timedelta(minutes=1))
    quick_order = order_with_coupon(quick, paid_course).data["id"]
    assert outcome(pay(quick, quick_order, gateway)) == "paid"

    gateway.paid.add("A1")
    assert outcome(callback("A1")) == "canceled"

    coupon.refresh_from_db()
    assert coupon.used_count == 1 and "A1" not in gateway.verified


@pytest.mark.django_db
def test_per_buyer_limit(paid_course, gateway):
    other = Course.objects.create(instructor=paid_course.instructor, category=paid_course.category, title="Go",
                                  status=Course.Status.PUBLISHED, price=100000)
    make_coupon(discount_percent=50, max_uses_per_user=1)
    student = buyer(1)
    order_id = order_with_coupon(student, paid_course).data["id"]
    pay(student, order_id, gateway)

    again = order_with_coupon(student, other)

    assert again.status_code == 400 and "coupon_code" in again.data
    assert order_with_coupon(buyer(2), other).status_code == 201  # others are unaffected


@pytest.mark.django_db(transaction=True)
@pytest.mark.parametrize("percent", [50, 100])  # 100%: the order is fulfilled right away, no gateway
def test_simultaneous_buyers_for_the_last_use(paid_course, gateway, percent):
    coupon = make_coupon(discount_percent=percent, max_uses=1)
    buyers = [buyer(n) for n in range(5)]
    barrier = threading.Barrier(len(buyers))
    codes = []

    def checkout(user):
        try:
            barrier.wait()
            codes.append(order_with_coupon(user, paid_course).status_code)
        finally:
            connection.close()

    threads = [threading.Thread(target=checkout, args=(u,)) for u in buyers]
    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=30)

    assert sorted(codes) == [201, 400, 400, 400, 400]
    coupon.refresh_from_db()
    assert coupon.used_count == (1 if percent == 100 else 0)
    assert Order.objects.filter(coupon=coupon).exclude(status=Order.Status.CANCELED).count() == 1
