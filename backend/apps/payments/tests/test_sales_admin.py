"""The instructor's sales panel: orders, payments, revenue and coupons, without the Django admin
(PAY-04). Only the site's own courses count, and only admins get in."""
from datetime import timedelta

import pytest
from django.utils import timezone
from rest_framework.test import APIClient

from apps.accounts.models import User
from apps.courses.models import Course
from apps.instructors.models import InstructorProfile
from apps.payments.models import Coupon, Order, OrderItem, Payment, RefundRequest

pytestmark = pytest.mark.django_db

BASE = "/api/v1/payments/admin"


def as_(user):
    client = APIClient()
    client.force_authenticate(user)
    return client


def results(response):
    return response.data["results"] if isinstance(response.data, dict) and "results" in response.data else response.data


@pytest.fixture
def teacher(course):
    return course.instructor.user


@pytest.fixture
def buyer():
    return User.objects.create_user(email="ali@example.com", password="x", first_name="علی", phone_number="09120000000")


def paid_order(user, course, amount=150000, ref="R1", days_ago=0):
    order = Order.objects.create(user=user, total_amount=amount, status=Order.Status.PAID)
    OrderItem.objects.create(order=order, course=course, price_at_purchase=amount)
    Payment.objects.create(order=order, authority=f"A-{ref}", ref_id=ref, status=Payment.Status.VERIFIED)
    when = timezone.now() - timedelta(days=days_ago)
    Order.objects.filter(id=order.id).update(created_at=when, paid_at=when)
    return order


@pytest.fixture
def other_instructors_order(course):
    """An order for a course that isn't this site's instructor's: must stay invisible."""
    stranger = User.objects.create_user(email="other-teacher@example.com", password="x", role=User.Role.ADMIN)
    profile = InstructorProfile.objects.create(user=stranger)
    foreign = Course.objects.create(instructor=profile, category=course.category, title="Foreign", status=Course.Status.PUBLISHED)
    return paid_order(User.objects.create_user(email="x@example.com", password="x"), foreign, amount=999000, ref="FOREIGN")


ENDPOINTS = ["/summary/", "/orders/", "/payments/", "/coupons/", "/refunds/"]


@pytest.mark.parametrize("path", ENDPOINTS)
def test_students_and_visitors_are_kept_out(path, buyer):
    assert as_(buyer).get(BASE + path).status_code == 403
    assert APIClient().get(BASE + path).status_code == 401


def test_orders_list_shows_buyers_items_and_payments(teacher, buyer, course):
    order = paid_order(buyer, course)

    rows = results(as_(teacher).get(f"{BASE}/orders/"))

    assert [r["id"] for r in rows] == [order.id]
    row = rows[0]
    assert row["buyer"]["email"] == "ali@example.com" and row["buyer"]["phone_number"] == "09120000000"
    assert row["items"][0]["course_title"] == course.title
    assert row["payments"][0]["ref_id"] == "R1" and row["payments"][0]["status"] == "verified"


def test_orders_can_be_filtered(teacher, buyer, course):
    paid = paid_order(buyer, course)
    pending = Order.objects.create(user=User.objects.create_user(email="z@example.com", password="x"), total_amount=10)
    OrderItem.objects.create(order=pending, course=course, price_at_purchase=10)
    client = as_(teacher)

    assert [r["id"] for r in results(client.get(f"{BASE}/orders/", {"status": "paid"}))] == [paid.id]
    assert [r["id"] for r in results(client.get(f"{BASE}/orders/", {"search": "z@ex"}))] == [pending.id]
    assert [r["id"] for r in results(client.get(f"{BASE}/orders/", {"search": "علی"}))] == [paid.id]


def test_another_instructors_orders_are_invisible(teacher, buyer, course, other_instructors_order):
    paid_order(buyer, course)
    client = as_(teacher)

    assert other_instructors_order.id not in [r["id"] for r in results(client.get(f"{BASE}/orders/"))]
    assert client.get(f"{BASE}/orders/{other_instructors_order.id}/").status_code == 404
    assert client.post(f"{BASE}/orders/{other_instructors_order.id}/refund/", {"reference": "x"}).status_code == 404
    assert "FOREIGN" not in [p["ref_id"] for p in results(client.get(f"{BASE}/payments/"))]
    summary = client.get(f"{BASE}/summary/").data
    assert summary["gross"] == 150000  # the foreign 999,000 isn't this site's revenue


def test_summary_follows_the_real_payment_states(teacher, buyer, course):
    paid_order(buyer, course, amount=100000, ref="R1")
    second = paid_order(User.objects.create_user(email="b2@example.com", password="x"), course, amount=50000, ref="R2")
    paid_order(User.objects.create_user(email="old@example.com", password="x"), course, amount=70000, ref="OLD", days_ago=60)
    unpaid = Order.objects.create(user=buyer, total_amount=30000)  # still at the gateway: not revenue
    OrderItem.objects.create(order=unpaid, course=course, price_at_purchase=30000)
    Payment.objects.create(order=unpaid, authority="P", status=Payment.Status.INITIATED)
    duplicate = Payment.objects.create(order=second, authority="DUP", status=Payment.Status.CANCELED, note="already paid")
    RefundRequest.objects.create(order=second, amount=50000, status=RefundRequest.Status.REFUNDED, decided_at=timezone.now())
    Order.objects.filter(id=second.id).update(status=Order.Status.REFUNDED)

    data = as_(teacher).get(f"{BASE}/summary/", {"days": 30}).data

    assert data["gross"] == 150000  # both sales in the window, including the one refunded later
    assert data["refunded"] == 50000 and data["net"] == 100000
    assert data["paid_orders"] == 2 and data["pending_orders"] == 1
    assert data["canceled_payments"] == 1  # the duplicate ZarinPal returns by itself
    assert sum(d["amount"] for d in data["daily"]) == 150000
    assert data["top_courses"][0]["title"] == course.title
    assert as_(teacher).get(f"{BASE}/summary/", {"days": 90}).data["gross"] == 220000
    assert duplicate.id  # (kept for clarity: the duplicate never counts as revenue)


def test_payments_list_with_status_filter(teacher, buyer, course):
    order = paid_order(buyer, course)
    Payment.objects.create(order=order, authority="FAIL", status=Payment.Status.FAILED)

    rows = results(as_(teacher).get(f"{BASE}/payments/", {"status": "failed"}))

    assert [r["authority"] for r in rows] == ["FAIL"]
    assert rows[0]["order"] == order.id and rows[0]["buyer_email"] == "ali@example.com"


# ---------- coupons ----------

def coupon_body(**overrides):
    now = timezone.now()
    return {"code": "NOROOZ", "discount_percent": 20, "valid_from": now.isoformat(),
            "valid_to": (now + timedelta(days=10)).isoformat(), "max_uses": 50, **overrides}


def test_teacher_creates_lists_and_edits_coupons_with_usage(teacher, buyer, course):
    client = as_(teacher)
    created = client.post(f"{BASE}/coupons/", coupon_body(), format="json")
    assert created.status_code == 201
    coupon = Coupon.objects.get(code="NOROOZ")
    order = paid_order(buyer, course)
    Order.objects.filter(id=order.id).update(coupon=coupon)
    Coupon.objects.filter(id=coupon.id).update(used_count=1)

    row = results(client.get(f"{BASE}/coupons/"))[0]
    assert row["code"] == "NOROOZ" and row["used_count"] == 1 and row["paid_orders"] == 1

    edited = client.patch(f"{BASE}/coupons/{coupon.id}/", {"max_uses": 5, "max_uses_per_user": 1}, format="json")
    assert edited.status_code == 200 and edited.data["max_uses_per_user"] == 1


@pytest.mark.parametrize(
    "bad",
    [
        {"discount_percent": 0},
        {"discount_percent": 101},
        {"discount_percent": None, "discount_amount": None},
        {"discount_percent": 10, "discount_amount": 5000},
        {"valid_to": (timezone.now() - timedelta(days=30)).isoformat()},
        {"code": "norooz"},  # same code, different case
    ],
)
def test_invalid_coupons_are_refused(teacher, bad):
    client = as_(teacher)
    client.post(f"{BASE}/coupons/", coupon_body(), format="json")
    assert client.post(f"{BASE}/coupons/", coupon_body(code="OTHER", **bad) if "code" not in bad else coupon_body(**bad), format="json").status_code == 400


def test_limit_cannot_drop_below_uses_and_used_coupons_cannot_be_deleted(teacher, buyer, course):
    client = as_(teacher)
    coupon_id = client.post(f"{BASE}/coupons/", coupon_body(), format="json").data["id"]
    Coupon.objects.filter(id=coupon_id).update(used_count=3)
    Order.objects.filter(id=paid_order(buyer, course).id).update(coupon_id=coupon_id)

    assert client.patch(f"{BASE}/coupons/{coupon_id}/", {"max_uses": 2}, format="json").status_code == 400
    assert client.delete(f"{BASE}/coupons/{coupon_id}/").status_code == 400
    unused = client.post(f"{BASE}/coupons/", coupon_body(code="SPARE"), format="json").data["id"]
    assert client.delete(f"{BASE}/coupons/{unused}/").status_code == 204
