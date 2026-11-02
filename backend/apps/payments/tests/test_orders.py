from datetime import timedelta
from unittest import mock

import pytest
from django.utils import timezone
from rest_framework.test import APIClient

from apps.accounts.models import User
from apps.enrollments.models import Enrollment
from apps.payments import views
from apps.payments.gateways.base import PaymentGateway, PaymentGatewayError, PaymentRequestResult
from apps.payments.gateways.zarinpal import ZarinPalGateway
from apps.payments.models import Coupon, Order, Payment

pytestmark = pytest.mark.django_db


class FakeGateway(PaymentGateway):
    def __init__(self, broken=False):
        self.broken = broken
        self.callback_urls = []

    def create_payment_request(self, order, callback_url):
        if self.broken:
            raise PaymentGatewayError("rejected")
        self.callback_urls.append(callback_url)
        return PaymentRequestResult(redirect_url="https://pay.example/X1", authority="X1")


@pytest.fixture
def gateway(monkeypatch):
    fake = FakeGateway()
    monkeypatch.setattr(views, "get_gateway", lambda: fake)
    return fake


@pytest.fixture
def paid_course(course):
    course.price = 200000
    course.save(update_fields=["price"])
    return course


@pytest.fixture
def student():
    return User.objects.create_user(email="s@example.com", password="x")


def client_for(user):
    client = APIClient()
    client.force_authenticate(user)
    return client


def order(user, course, coupon_code=None):
    body = {"course_ids": [course.id]}
    if coupon_code is not None:
        body["coupon_code"] = coupon_code
    return client_for(user).post("/api/v1/payments/orders/", body, format="json")


def make_coupon(code="OFF", **kwargs):
    now = timezone.now()
    return Coupon.objects.create(
        code=code, valid_from=now - timedelta(days=1), valid_to=now + timedelta(days=1), **kwargs
    )


def test_paid_course_order_waits_for_payment(student, paid_course):
    response = order(student, paid_course)

    assert response.status_code == 201
    assert response.data["status"] == "pending"
    assert int(response.data["total_amount"]) == 200000
    assert not Enrollment.objects.filter(student=student).exists()


def test_free_course_enrolls_without_the_gateway(student, course, gateway):
    response = order(student, course)

    assert response.data["status"] == "paid"
    assert Enrollment.objects.filter(student=student, course=course, is_active=True).exists()
    assert gateway.callback_urls == []


@pytest.mark.parametrize(
    ("discount", "expected"),
    [({"discount_percent": 25}, 150000), ({"discount_amount": 50000}, 150000), ({"discount_amount": 999999}, 0)],
)
def test_coupon_lowers_the_total(student, paid_course, discount, expected):
    make_coupon(**discount)

    response = order(student, paid_course, "off")  # codes match case-insensitively

    assert int(response.data["total_amount"]) == expected
    assert response.data["coupon_code"] == "OFF"


def test_full_discount_coupon_enrolls_and_counts_one_use(student, paid_course):
    coupon = make_coupon(discount_percent=100)

    response = order(student, paid_course, "OFF")

    assert response.data["status"] == "paid"
    assert Enrollment.objects.filter(student=student, course=paid_course).exists()
    coupon.refresh_from_db()
    assert coupon.used_count == 1


def test_coupon_use_is_counted_only_once_the_order_is_paid(student, paid_course):
    coupon = make_coupon(discount_percent=10)

    order(student, paid_course, "OFF")

    coupon.refresh_from_db()
    assert coupon.used_count == 0


@pytest.mark.parametrize(
    "coupon_kwargs",
    [
        {"code": "OTHER"},  # unknown code
        {"valid_to": timezone.now() - timedelta(hours=1)},  # expired
        {"max_uses": 1, "used_count": 1},  # used up
    ],
)
def test_bad_coupon_is_rejected_instead_of_ignored(student, paid_course, coupon_kwargs):
    kwargs = {"code": "OFF", "discount_percent": 50, **coupon_kwargs}
    now = timezone.now()
    kwargs.setdefault("valid_from", now - timedelta(days=1))
    kwargs.setdefault("valid_to", now + timedelta(days=1))
    Coupon.objects.create(**kwargs)

    response = order(student, paid_course, "OFF")

    assert response.status_code == 400
    assert "coupon_code" in response.data
    assert not Order.objects.exists()


def test_blank_coupon_is_the_same_as_none(student, paid_course):
    response = order(student, paid_course, "  ")

    assert response.status_code == 201
    assert int(response.data["total_amount"]) == 200000


def test_already_enrolled_student_cannot_buy_again(student, paid_course):
    Enrollment.objects.create(student=student, course=paid_course)

    response = order(student, paid_course)

    assert response.status_code == 400
    assert not Order.objects.exists()


def test_buying_again_after_removal_restores_access(student, course):
    Enrollment.objects.create(student=student, course=course, is_active=False)

    response = order(student, course)

    assert response.data["status"] == "paid"
    assert Enrollment.objects.get(student=student, course=course).is_active


def test_order_list_shows_only_own_orders(student, paid_course):
    order(student, paid_course)
    order(User.objects.create_user(email="other@example.com", password="x"), paid_course)

    response = client_for(student).get("/api/v1/payments/orders/")

    assert response.status_code == 200
    results = response.data["results"] if isinstance(response.data, dict) else response.data
    assert len(results) == 1
    assert results[0]["items"][0]["course_title"] == paid_course.title


def test_initiate_sends_zarinpal_back_to_the_api_callback(student, paid_course, gateway):
    order_id = order(student, paid_course).data["id"]

    response = client_for(student).post(f"/api/v1/payments/initiate/{order_id}/")

    assert response.status_code == 200
    assert response.data["redirect_url"] == "https://pay.example/X1"
    assert gateway.callback_urls[0].endswith("/api/v1/payments/callback/")
    assert Payment.objects.filter(order_id=order_id, authority="X1").exists()


def test_initiate_reports_a_gateway_refusal(student, paid_course, gateway):
    gateway.broken = True
    order_id = order(student, paid_course).data["id"]

    response = client_for(student).post(f"/api/v1/payments/initiate/{order_id}/")

    assert response.status_code == 502
    assert not Payment.objects.exists()


def zarinpal_response(status_code, body):
    return mock.Mock(status_code=status_code, json=mock.Mock(return_value=body))


def test_zarinpal_is_sent_rial_not_toman(student, paid_course):
    created = Order.objects.create(user=student, total_amount=200000)
    ok = zarinpal_response(200, {"data": {"code": 100, "authority": "A"}, "errors": []})

    with mock.patch("apps.payments.gateways.zarinpal.requests.post", return_value=ok) as post:
        ZarinPalGateway().create_payment_request(created, "https://site/cb")
        ZarinPalGateway().verify("A", 200000)

    assert [call.kwargs["json"]["amount"] for call in post.call_args_list] == [2000000, 2000000]


def test_zarinpal_refusal_raises_gateway_error(student):
    created = Order.objects.create(user=student, total_amount=50)
    refused = zarinpal_response(400, {"data": [], "errors": {"code": -9, "message": "amount too low"}})

    with mock.patch("apps.payments.gateways.zarinpal.requests.post", return_value=refused):
        with pytest.raises(PaymentGatewayError):
            ZarinPalGateway().create_payment_request(created, "https://site/cb")


def test_zarinpal_unpaid_verify_is_a_failure_not_a_crash():
    unpaid = zarinpal_response(400, {"data": [], "errors": {"code": -51, "message": "not paid"}})

    with mock.patch("apps.payments.gateways.zarinpal.requests.post", return_value=unpaid):
        result = ZarinPalGateway().verify("A", 1000)

    assert result.success is False
    assert result.error_message == "not paid"
