"""The rules that keep a buyer from paying twice and a coupon from being overused.

Shared by order creation, payment initiation, the browser callback and the periodic
reconciliation task, so a payment is handled the same way whichever path reaches it first.

Locking: every step that can move money locks the buyer's user row first (SELECT ... FOR
UPDATE), so one buyer's checkouts, payment starts and verifications run one at a time even
across gunicorn workers and the Celery worker. Locks are always taken in the order
user -> coupon -> order -> payment, so they can't deadlock.

Duplicate payments: ZarinPal returns the money of any payment that is never verified. So when
a payment arrives for something already paid for, it is simply not verified (status CANCELED,
with a note) rather than verified and refunded by hand.
"""
import logging
from datetime import timedelta

from django.contrib.auth import get_user_model
from django.db import transaction
from django.db.models import F
from django.utils import timezone

from .gateways.base import PaymentGateway, PaymentGatewayError
from .models import Coupon, Order, OrderItem, Payment

logger = logging.getLogger(__name__)

# How long a started payment counts as "the buyer is on the gateway page right now": pressing
# pay again in this window reuses it, and no other order for its courses may be started.
LIVE_PAYMENT_WINDOW = timedelta(minutes=15)
# How long an unpaid order holds one use of its coupon. Matches the reconciliation task's
# GIVE_UP_AFTER, after which an unpaid payment is called failed.
COUPON_HOLD = timedelta(hours=1)


class Outcome:
    """What the buyer is told after a callback (the `status` of the site's result page)."""

    PAID = "paid"
    FAILED = "failed"
    PENDING = "pending"  # no clear answer from the gateway yet; reconciliation will settle it
    CANCELED = "canceled"  # paid for something already bought: not verified, the gateway refunds it


def lock_buyer(user_id: int):
    return get_user_model().objects.select_for_update().get(pk=user_id)


def live_payments():
    return Payment.objects.filter(status=Payment.Status.INITIATED, created_at__gte=timezone.now() - LIVE_PAYMENT_WINDOW)


def enrolled_course_ids(user, course_ids) -> set[int]:
    from apps.enrollments.models import Enrollment

    return set(
        Enrollment.objects.filter(student=user, course_id__in=course_ids, is_active=True).values_list("course_id", flat=True)
    )


# ---------- coupons ----------

def _holding_orders(coupon: Coupon):
    """Unpaid orders whose hold on `coupon` hasn't run out (an order's hold restarts when its
    payment is started, see `start_payment`)."""
    return Order.objects.filter(
        coupon=coupon, status=Order.Status.PENDING, updated_at__gte=timezone.now() - COUPON_HOLD
    )


def coupon_problem(coupon: Coupon, user, *, exclude_order_id=None, at_payment=False) -> str | None:
    """Why `user` can't use `coupon` now, or None. Call with the coupon row locked.

    At order time a use is taken by every paid order (`used_count`) and every holding order.
    At payment time (`at_payment=True`) the order being paid already went through that check, so
    only uses that were *paid* since count against it: a hold that ran out meanwhile can't push
    the coupon past its limit, but a buyer who paid within the hold always gets their discount.
    """
    if not at_payment and not coupon.is_valid_at(timezone.now()):
        return "کد تخفیف معتبر نیست یا منقضی شده است."
    held = _holding_orders(coupon).exclude(id=exclude_order_id)
    if coupon.max_uses is not None:
        taken = coupon.used_count + (0 if at_payment else held.count())
        if taken >= coupon.max_uses:
            return "ظرفیت این کد تخفیف تمام شده است."
    if coupon.max_uses_per_user is not None:
        mine = Order.objects.filter(coupon=coupon, user=user, status=Order.Status.PAID)
        if not at_payment:
            mine = mine | held.filter(user=user)
        if mine.exclude(id=exclude_order_id).count() >= coupon.max_uses_per_user:
            return "سهم شما از این کد تخفیف استفاده شده است."
    return None


# ---------- orders ----------

class OrderConflict(Exception):
    """Another order for the same courses is being paid right now."""


def reuse_or_retire_open_orders(user, course_ids: set[int], coupon: Coupon | None) -> Order | None:
    """Before creating an order (buyer row locked): return the buyer's open order for exactly
    these courses and coupon, if any; cancel their other open orders that share a course; refuse
    if one of those is being paid at this moment."""
    # No DISTINCT (Postgres refuses it with FOR UPDATE): pick the orders by id instead.
    ids = OrderItem.objects.filter(order__user=user, order__status=Order.Status.PENDING, course_id__in=course_ids)
    overlapping = list(
        Order.objects.select_for_update()
        .filter(id__in=ids.values("order_id"))
        .prefetch_related("items")
        .order_by("-created_at")
    )
    for order in overlapping:
        if {i.course_id for i in order.items.all()} == course_ids and order.coupon_id == (coupon.id if coupon else None):
            return order
    for order in overlapping:
        if live_payments().filter(order=order).exists():
            raise OrderConflict
    for order in overlapping:
        order.status = Order.Status.CANCELED
        order.save(update_fields=["status", "updated_at"])
        logger.info("Order %s canceled: replaced by a new order for the same courses", order.id)
    return None


# ---------- starting a payment ----------

class AlreadyBought(Exception):
    """The order contains a course the buyer already has; it has been canceled."""


def start_payment(order_id: int, user, gateway: PaymentGateway, callback_url: str) -> str:
    """The gateway URL to send the buyer to for `order_id`: the payment already in progress if
    there is one, otherwise a new one. Raises Order.DoesNotExist, AlreadyBought or
    PaymentGatewayError."""
    with transaction.atomic():
        lock_buyer(user.id)
        order = Order.objects.select_for_update().get(id=order_id, user=user, status=Order.Status.PENDING)
        if enrolled_course_ids(user, [i.course_id for i in order.items.all()]):
            order.status = Order.Status.CANCELED
            order.save(update_fields=["status", "updated_at"])
            redirect_url = None  # raised below, after the commit, so the cancellation is kept
        elif current := live_payments().filter(order=order).order_by("-created_at").first():
            redirect_url = gateway.redirect_url(current.authority)
        else:
            result = gateway.create_payment_request(order, callback_url)
            Payment.objects.create(order=order, authority=result.authority, status=Payment.Status.INITIATED)
            order.save(update_fields=["updated_at"])  # restarts the coupon hold
            redirect_url = result.redirect_url
    if redirect_url is None:
        raise AlreadyBought
    return redirect_url


# ---------- finishing a payment ----------

def fulfil_order(order: Order) -> None:
    """Mark ``order`` paid, enroll its buyer in every course, and count its coupon as used.

    Call inside a transaction holding the buyer's row (see `lock_buyer`).
    """
    order.status = Order.Status.PAID
    order.save(update_fields=["status", "updated_at"])

    if order.coupon_id:
        Coupon.objects.filter(id=order.coupon_id).update(used_count=F("used_count") + 1)

    from apps.enrollments.models import Enrollment

    for item in order.items.select_related("course"):
        enrollment, created = Enrollment.objects.get_or_create(
            student=order.user, course=item.course, defaults={"order_item": item}
        )
        if not created and not enrollment.is_active:
            # Buying again after the instructor removed them restores access.
            enrollment.is_active = True
            enrollment.order_item = item
            enrollment.save(update_fields=["is_active", "order_item", "updated_at"])


def _cancel(payment: Payment, order: Order, note: str) -> Payment:
    payment.status = Payment.Status.CANCELED
    payment.note = note
    payment.save(update_fields=["status", "note", "updated_at"])
    if order.status == Order.Status.PENDING:
        order.status = Order.Status.CANCELED
        order.save(update_fields=["status", "updated_at"])
    logger.warning("Payment %s (order %s) not verified: %s. ZarinPal refunds it.", payment.id, order.id, note)
    return payment


def outcome_of(payment: Payment) -> str:
    return {
        Payment.Status.VERIFIED: Outcome.PAID,
        Payment.Status.FAILED: Outcome.FAILED,
        Payment.Status.CANCELED: Outcome.CANCELED,
    }.get(payment.status, Outcome.PENDING)


def finalize_payment(payment: Payment, gateway: PaymentGateway, *, mark_failed: bool = True) -> Payment:
    """Settle ``payment``: verify it with the gateway and fulfil its order, at most once.

    Under the buyer's lock, a payment is only verified if its order isn't paid yet, none of its
    courses is already bought, and its coupon still has room; otherwise it is CANCELED (not
    verified, so the gateway refunds it). A gateway outage or unclear answer leaves it INITIATED
    for reconciliation. ``mark_failed=False`` also leaves a definite "not paid" as it is, for
    callers that can't yet tell "failed" from "the buyer hasn't finished paying".
    """
    if payment.status != Payment.Status.INITIATED:
        return payment

    with transaction.atomic():
        lock_buyer(payment.order.user_id)
        payment = Payment.objects.select_for_update(of=("self",)).select_related("order").get(id=payment.id)
        if payment.status != Payment.Status.INITIATED:
            return payment  # settled by a concurrent callback or reconciliation
        order = payment.order

        if order.status == Order.Status.PAID:
            return _cancel(payment, order, f"order {order.id} was already paid by another payment")
        if enrolled_course_ids(order.user, [i.course_id for i in order.items.all()]):
            return _cancel(payment, order, "the buyer already has a course in this order")
        if order.coupon_id:
            coupon = Coupon.objects.select_for_update().get(id=order.coupon_id)
            problem = coupon_problem(coupon, order.user, exclude_order_id=order.id, at_payment=True)
            if problem:
                return _cancel(payment, order, f"coupon {coupon.code}: {problem}")

        try:
            result = gateway.verify(payment.authority, int(order.total_amount))
        except PaymentGatewayError as exc:
            logger.warning("Payment %s (authority %s): gateway unavailable, left open: %s", payment.id, payment.authority, exc)
            return payment

        if not result.success:
            if not result.definite:
                logger.warning(
                    "Payment %s (authority %s): unclear gateway answer, left open: %s",
                    payment.id, payment.authority, result.raw_response,
                )
            elif mark_failed:
                payment.status = Payment.Status.FAILED
                payment.raw_response = result.raw_response or {}
                payment.save(update_fields=["status", "raw_response", "updated_at"])
            return payment

        payment.status = Payment.Status.VERIFIED
        payment.ref_id = result.ref_id
        payment.raw_response = result.raw_response or {}
        payment.save(update_fields=["status", "ref_id", "raw_response", "updated_at"])
        fulfil_order(order)
        logger.info("Payment %s verified (ref %s); order %s paid", payment.id, payment.ref_id, order.id)
        return payment

