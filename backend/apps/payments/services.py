"""Turning a gateway verification into a paid order and enrollments.

Shared by the browser callback and the periodic reconciliation task, so a
payment is finalized the same way whichever of the two reaches it first.
"""
from django.db import transaction

from .gateways.base import PaymentGateway
from .models import Order, Payment


def finalize_payment(payment: Payment, gateway: PaymentGateway, *, mark_failed: bool = True) -> Payment:
    """Verify ``payment`` with the gateway and, on success, mark the order paid and enroll the buyer.

    Idempotent: a payment that is already verified is returned untouched and
    never grants a second enrollment, even when two callers race.
    ``mark_failed=False`` leaves an unsuccessful payment as it is, for callers
    that can't yet tell "failed" from "the buyer hasn't finished paying".
    """
    if payment.status == Payment.Status.VERIFIED:
        return payment

    result = gateway.verify(payment.authority, int(payment.order.total_amount))

    with transaction.atomic():
        payment = Payment.objects.select_for_update().select_related("order").get(id=payment.id)
        if payment.status == Payment.Status.VERIFIED:
            return payment

        if not result.success:
            if mark_failed:
                payment.status = Payment.Status.FAILED
                payment.raw_response = result.raw_response or {}
                payment.save(update_fields=["status", "raw_response"])
            return payment

        payment.status = Payment.Status.VERIFIED
        payment.ref_id = result.ref_id
        payment.raw_response = result.raw_response or {}
        payment.save(update_fields=["status", "ref_id", "raw_response"])

        order = payment.order
        order.status = Order.Status.PAID
        order.save(update_fields=["status"])

        from apps.enrollments.models import Enrollment

        for item in order.items.select_related("course"):
            Enrollment.objects.get_or_create(student=order.user, course=item.course, defaults={"order_item": item})

    return payment
