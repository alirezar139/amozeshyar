"""`manage.py audit_payments` lists what needs a refund or a look, and changes nothing."""
from datetime import timedelta
from io import StringIO

import pytest
from django.core.management import call_command
from django.utils import timezone

from apps.accounts.models import User
from apps.payments.models import Coupon, Order, OrderItem, Payment

pytestmark = pytest.mark.django_db


def test_reports_double_charges_overused_coupons_and_stuck_payments(course):
    buyer = User.objects.create_user(email="b@example.com", password="x")
    first = Order.objects.create(user=buyer, total_amount=100, status=Order.Status.PAID)
    OrderItem.objects.create(order=first, course=course, price_at_purchase=100)
    Payment.objects.create(order=first, authority="V1", status=Payment.Status.VERIFIED, ref_id="r1")
    Payment.objects.create(order=first, authority="V2", status=Payment.Status.VERIFIED, ref_id="r2")
    second = Order.objects.create(user=buyer, total_amount=100, status=Order.Status.PAID)
    OrderItem.objects.create(order=second, course=course, price_at_purchase=100)
    now = timezone.now()
    Coupon.objects.create(code="X", valid_from=now, valid_to=now, max_uses=1, used_count=3)
    stuck = Payment.objects.create(order=second, authority="S1")
    Payment.objects.filter(id=stuck.id).update(created_at=now - timedelta(days=3))
    before = list(Payment.objects.values_list("id", "status").order_by("id"))

    out = StringIO()
    call_command("audit_payments", stdout=out)
    report = out.getvalue()

    assert f"order {first.id}" in report and "r1" in report and "r2" in report
    assert "in 2 orders" in report
    assert "coupon X: used 3 times, limit 1" in report
    assert "authority S1" in report
    assert "4 item(s) to review." in report
    assert list(Payment.objects.values_list("id", "status").order_by("id")) == before


def test_clean_data_reports_nothing():
    out = StringIO()
    call_command("audit_payments", stdout=out)
    assert "0 item(s) to review." in out.getvalue()
