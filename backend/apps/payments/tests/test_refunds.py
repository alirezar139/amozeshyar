"""Refunds: a student asks, the instructor rejects or records the refund; recording it closes the
order's access and tells the student (PAY-04)."""
import pytest
from rest_framework.test import APIClient

from apps.accounts.models import User
from apps.enrollments.models import Enrollment
from apps.messaging.models import Message
from apps.payments.models import Order, RefundRequest
from apps.payments.services import fulfil_order

from .test_sales_admin import BASE, paid_order

pytestmark = pytest.mark.django_db(transaction=True)  # notifications are sent after commit


def as_(user):
    client = APIClient()
    client.force_authenticate(user)
    return client


@pytest.fixture
def teacher(course):
    return course.instructor.user


@pytest.fixture
def student():
    return User.objects.create_user(email="s@example.com", password="x")


@pytest.fixture
def bought(student, course):
    order = paid_order(student, course)
    order.status = Order.Status.PENDING
    order.save()
    fulfil_order(order)  # enrolls, as a real purchase does
    return order


def ask(student, order, reason="دوره با انتظارم فرق داشت"):
    return as_(student).post(f"/api/v1/payments/orders/{order.id}/refund-request/", {"reason": reason}, format="json")


def test_student_requests_a_refund_and_sees_its_status(student, bought):
    assert ask(student, bought).status_code == 201
    mine = as_(student).get("/api/v1/payments/orders/").data["results"][0]
    assert mine["refund"]["status"] == "pending"


def test_one_open_request_per_order(student, bought):
    ask(student, bought)
    assert ask(student, bought).status_code == 400


@pytest.mark.parametrize("problem", ["someone_else", "not_paid", "free", "no_reason"])
def test_refund_request_rules(student, course, bought, problem):
    if problem == "someone_else":
        response = ask(User.objects.create_user(email="o@example.com", password="x"), bought)
        assert response.status_code == 404
        return
    if problem == "not_paid":
        Order.objects.filter(id=bought.id).update(status=Order.Status.PENDING)
    if problem == "free":
        Order.objects.filter(id=bought.id).update(total_amount=0)
    response = ask(student, bought, reason="" if problem == "no_reason" else "x")
    assert response.status_code == 400


def test_teacher_rejects_with_a_note_and_the_student_is_told(teacher, student, bought):
    request_id = ask(student, bought).data["id"]

    response = as_(teacher).post(f"{BASE}/refunds/{request_id}/reject/", {"note": "بیش از نیمی از دوره دیده شده"}, format="json")

    assert response.status_code == 200 and response.data["status"] == "rejected"
    assert Order.objects.get(id=bought.id).status == Order.Status.PAID
    assert Enrollment.objects.get(student=student).is_active
    assert Message.objects.filter(bot="notify", text__contains="پذیرفته نشد").exists()


def test_recording_the_refund_closes_access_and_notifies(teacher, student, course, bought):
    request_id = ask(student, bought).data["id"]

    response = as_(teacher).post(f"{BASE}/refunds/{request_id}/complete/", {"reference": "ZP-REF-881"}, format="json")

    assert response.status_code == 200 and response.data["status"] == "refunded"
    refund = RefundRequest.objects.get(id=request_id)
    assert refund.reference == "ZP-REF-881" and refund.decided_by == teacher and refund.amount == bought.total_amount
    assert Order.objects.get(id=bought.id).status == Order.Status.REFUNDED
    assert not Enrollment.objects.get(student=student, course=course).is_active
    assert Message.objects.filter(bot="notify", text__contains="بازگردانده شد").exists()
    # a decided request can't be decided again
    assert as_(teacher).post(f"{BASE}/refunds/{request_id}/reject/", {}, format="json").status_code == 400


def test_teacher_can_refund_an_order_nobody_asked_about(teacher, student, bought):
    response = as_(teacher).post(f"{BASE}/orders/{bought.id}/refund/", {"reference": "manual-1", "note": "پرداخت دوبار"}, format="json")

    assert response.status_code == 200
    assert RefundRequest.objects.get(order=bought).status == RefundRequest.Status.REFUNDED
    assert Order.objects.get(id=bought.id).status == Order.Status.REFUNDED
    # an order that isn't paid can't be refunded
    assert as_(teacher).post(f"{BASE}/orders/{bought.id}/refund/", {"reference": "again"}, format="json").status_code == 400


def test_refunds_list_and_students_cannot_decide(teacher, student, bought):
    request_id = ask(student, bought).data["id"]
    rows = as_(teacher).get(f"{BASE}/refunds/", {"status": "pending"}).data["results"]
    assert [r["id"] for r in rows] == [request_id] and rows[0]["buyer"]["email"] == "s@example.com"
    assert as_(student).post(f"{BASE}/refunds/{request_id}/complete/", {"reference": "x"}).status_code == 403
