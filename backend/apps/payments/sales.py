"""The instructor's view of sales: which orders are theirs, the revenue report, and refunds.

"Theirs" means orders for courses of this site's instructor (`get_site_owner`). An install has
one instructor, so in practice that is every order; the filter is still applied everywhere, so a
course that belongs to any other InstructorProfile (an old marketplace row, a test account) never
shows up in this instructor's money.
"""
from datetime import timedelta

from django.db import transaction
from django.db.models import Count, DecimalField, Q, Sum, Value
from django.db.models.functions import Coalesce, TruncDate
from django.utils import timezone

from apps.instructors.site import get_site_owner

from .models import Order, OrderItem, Payment, RefundRequest


def site_order_ids():
    owner = get_site_owner()
    return OrderItem.objects.filter(course__instructor=owner).values("order_id")


def site_orders():
    """By id (not a join), so an order with several courses is never counted twice."""
    return Order.objects.filter(id__in=site_order_ids())


def site_payments():
    return Payment.objects.filter(order_id__in=site_order_ids())


def site_refunds():
    return RefundRequest.objects.filter(order_id__in=site_order_ids())


def _money(queryset, field):
    return int(queryset.aggregate(s=Coalesce(Sum(field), Value(0), output_field=DecimalField()))["s"])


def summary(days: int) -> dict:
    """Sales in the last `days` days, by the day each order was paid.

    gross: every order paid in the window, including ones refunded since. refunded: refunds
    recorded in the window. Payments still at the gateway, failed or canceled (duplicates the
    gateway returns by itself) are never revenue.
    """
    since = timezone.now() - timedelta(days=days)
    sold = (
        site_orders()
        .filter(status__in=(Order.Status.PAID, Order.Status.REFUNDED))
        .annotate(sold_at=Coalesce("paid_at", "created_at"))
        .filter(sold_at__gte=since)
    )
    refunds = site_refunds().filter(status=RefundRequest.Status.REFUNDED, decided_at__gte=since)
    gross, refunded = _money(sold, "total_amount"), _money(refunds, "amount")
    daily = (
        sold.annotate(day=TruncDate("sold_at"))
        .values("day")
        .annotate(amount=Sum("total_amount"), orders=Count("id"))
        .order_by("day")
    )
    top = (
        OrderItem.objects.filter(order__in=sold, course__instructor=get_site_owner())
        .values("course_id", "course__title")
        .annotate(sales=Count("id"), list_price_total=Sum("price_at_purchase"))
        .order_by("-sales", "course__title")[:5]
    )
    payments = site_payments().filter(created_at__gte=since)
    return {
        "days": days,
        "gross": gross,
        "refunded": refunded,
        "net": gross - refunded,
        "paid_orders": sold.count(),
        "buyers": sold.values("user").distinct().count(),
        "pending_orders": site_orders().filter(status=Order.Status.PENDING, created_at__gte=since).count(),
        "failed_payments": payments.filter(status=Payment.Status.FAILED).count(),
        "canceled_payments": payments.filter(status=Payment.Status.CANCELED).count(),
        "unsettled_payments": payments.filter(status=Payment.Status.INITIATED).count(),
        "open_refunds": site_refunds().filter(status=RefundRequest.Status.PENDING).count(),
        "daily": [{"date": d["day"], "amount": int(d["amount"]), "orders": d["orders"]} for d in daily],
        "top_courses": [
            {"course_id": t["course_id"], "title": t["course__title"], "sales": t["sales"], "list_price_total": int(t["list_price_total"])}
            for t in top
        ],
    }


class RefundError(Exception):
    pass


def _close_access(order: Order) -> None:
    from apps.enrollments.models import Enrollment

    # Only enrollments this order granted: a course bought again in a later order keeps it.
    Enrollment.objects.filter(order_item__order=order, is_active=True).update(is_active=False, updated_at=timezone.now())


def complete_refund(refund: RefundRequest | None, *, order: Order, by, reference: str, note: str = "") -> RefundRequest:
    """Record that `order`'s money was returned: the order becomes refunded and its courses close."""
    from apps.notifications.service import notify

    with transaction.atomic():
        order = Order.objects.select_for_update().get(id=order.id)
        if order.status != Order.Status.PAID:
            raise RefundError("فقط سفارش پرداخت‌شده را می‌توان مسترد کرد.")
        if refund is None:
            refund = RefundRequest(order=order, amount=order.total_amount)
        else:
            refund = RefundRequest.objects.select_for_update().get(id=refund.id)
            if refund.status != RefundRequest.Status.PENDING:
                raise RefundError("این درخواست قبلاً بررسی شده است.")
        refund.status = RefundRequest.Status.REFUNDED
        refund.reference, refund.admin_note = reference, note
        refund.decided_by, refund.decided_at = by, timezone.now()
        refund.save()
        RefundRequest.objects.filter(order=order, status=RefundRequest.Status.PENDING).exclude(id=refund.id).update(
            status=RefundRequest.Status.REJECTED, admin_note="استرداد جداگانه ثبت شد."
        )
        order.status = Order.Status.REFUNDED
        order.save(update_fields=["status", "updated_at"])
        _close_access(order)
        notify(order.user, "refund_completed", order_id=order.id, amount=int(refund.amount), reference=reference)
    return refund


def reject_refund(refund: RefundRequest, *, by, note: str = "") -> RefundRequest:
    from apps.notifications.service import notify

    with transaction.atomic():
        refund = RefundRequest.objects.select_for_update().select_related("order").get(id=refund.id)
        if refund.status != RefundRequest.Status.PENDING:
            raise RefundError("این درخواست قبلاً بررسی شده است.")
        refund.status = RefundRequest.Status.REJECTED
        refund.admin_note = note
        refund.decided_by, refund.decided_at = by, timezone.now()
        refund.save()
        notify(refund.order.user, "refund_rejected", order_id=refund.order_id, note=note)
    return refund


ORDER_SEARCH_FIELDS = ("user__email", "user__first_name", "user__last_name", "user__phone_number")


def search_filter(term: str) -> Q:
    q = Q()
    for field in ORDER_SEARCH_FIELDS:
        q |= Q(**{f"{field}__icontains": term})
    if term.isdigit():
        q |= Q(id=int(term))
    return q
