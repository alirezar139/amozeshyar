"""Read-only report of payment data that needs a human: run it before and after deploying the
PAY-01/02/03 fix. It changes nothing; refunds for anything it lists are done in the ZarinPal panel.

    python manage.py audit_payments
"""
from datetime import timedelta

from django.core.management.base import BaseCommand
from django.db.models import Count, F, Q
from django.utils import timezone

from apps.payments.models import Coupon, Order, OrderItem, Payment
from apps.payments.tasks import LOOK_BACK


class Command(BaseCommand):
    help = "List double charges, overused coupons and payments nobody settled (read-only)."

    def handle(self, *args, **options):
        problems = 0

        orders = Order.objects.annotate(n=Count("payments", filter=Q(payments__status=Payment.Status.VERIFIED))).filter(n__gt=1)
        for order in orders:
            problems += 1
            refs = ", ".join(order.payments.filter(status=Payment.Status.VERIFIED).values_list("ref_id", flat=True))
            self.stdout.write(f"order {order.id} ({order.user}): {order.n} verified payments (ref {refs})")

        twice = (
            OrderItem.objects.filter(order__status=Order.Status.PAID)
            .values("order__user__email", "course__title")
            .annotate(n=Count("order", distinct=True))
            .filter(n__gt=1)
        )
        for row in twice:
            problems += 1
            self.stdout.write(f"{row['order__user__email']} paid for «{row['course__title']}» in {row['n']} orders")

        for coupon in Coupon.objects.filter(max_uses__isnull=False, used_count__gt=F("max_uses")):
            problems += 1
            self.stdout.write(f"coupon {coupon.code}: used {coupon.used_count} times, limit {coupon.max_uses}")

        unsettled = Payment.objects.filter(status=Payment.Status.INITIATED, created_at__lt=timezone.now() - LOOK_BACK + timedelta(hours=1))
        for payment in unsettled.select_related("order__user"):
            problems += 1
            self.stdout.write(
                f"payment {payment.id} (authority {payment.authority}, {payment.order.user}) never settled since {payment.created_at:%Y-%m-%d %H:%M}"
            )

        style = self.style.SUCCESS if not problems else self.style.WARNING
        self.stdout.write(style(f"{problems} item(s) to review."))
