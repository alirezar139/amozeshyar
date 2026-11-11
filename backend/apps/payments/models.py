from django.conf import settings
from django.db import models

from apps.common.models import TimeStampedModel
from apps.courses.models import Course


class Coupon(TimeStampedModel):
    code = models.CharField(max_length=50, unique=True)
    discount_percent = models.PositiveIntegerField(null=True, blank=True)
    discount_amount = models.DecimalField(max_digits=12, decimal_places=0, null=True, blank=True)
    valid_from = models.DateTimeField()
    valid_to = models.DateTimeField()
    max_uses = models.PositiveIntegerField(null=True, blank=True)
    # Uses per buyer (null: no per-buyer limit). Checked against their paid and held orders.
    max_uses_per_user = models.PositiveIntegerField(null=True, blank=True)
    used_count = models.PositiveIntegerField(default=0)  # paid orders only; see services.coupon_problem

    def __str__(self):
        return self.code

    def is_valid_at(self, when) -> bool:
        """Within its dates. How many uses are left is `services.coupon_problem`'s job, since it
        also counts orders still being paid."""
        return self.valid_from <= when <= self.valid_to

    @property
    def is_valid(self) -> bool:
        from django.utils import timezone

        if not self.is_valid_at(timezone.now()):
            return False
        if self.max_uses is not None and self.used_count >= self.max_uses:
            return False
        return True


class Order(TimeStampedModel):
    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        PAID = "paid", "Paid"
        FAILED = "failed", "Failed"
        CANCELED = "canceled", "Canceled"
        REFUNDED = "refunded", "Refunded"

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="orders")
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    total_amount = models.DecimalField(max_digits=12, decimal_places=0, default=0)
    currency = models.CharField(max_length=10, default="IRT")
    coupon = models.ForeignKey(Coupon, on_delete=models.SET_NULL, null=True, blank=True)
    # When it became paid. Orders paid before this field existed have none; reports fall back
    # to created_at for them.
    paid_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"Order #{self.id} ({self.status})"


class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="items")
    course = models.ForeignKey(Course, on_delete=models.PROTECT, related_name="order_items")
    price_at_purchase = models.DecimalField(max_digits=12, decimal_places=0)

    class Meta:
        unique_together = ("order", "course")

    def __str__(self):
        return f"{self.course} in order #{self.order_id}"


class Payment(TimeStampedModel):
    class Status(models.TextChoices):
        INITIATED = "initiated", "Initiated"
        VERIFIED = "verified", "Verified"
        FAILED = "failed", "Failed"
        # Paid at the gateway but deliberately never verified (the course was already bought, or
        # the coupon ran out), so ZarinPal returns the money to the buyer. `note` says why.
        CANCELED = "canceled", "Canceled (not verified, refunded by the gateway)"

    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="payments")
    gateway = models.CharField(max_length=30, default="zarinpal")
    authority = models.CharField(max_length=100, blank=True, db_index=True)  # ZarinPal "Authority" token
    ref_id = models.CharField(max_length=100, blank=True)  # ZarinPal ref id on success
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.INITIATED)
    raw_response = models.JSONField(default=dict, blank=True)  # full gateway payload, for audit/debugging
    note = models.CharField(max_length=255, blank=True)  # why a payment was canceled, for the admin

    def __str__(self):
        return f"Payment #{self.id} for Order #{self.order_id} ({self.status})"


class RefundRequest(TimeStampedModel):
    """A refund of a paid order: asked for by the student, or recorded by the instructor directly.

    The money itself goes back through the ZarinPal panel (or the bank); "refunded" here records
    that it was sent (`reference`) and closes the order's course access.
    """

    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        REJECTED = "rejected", "Rejected"
        REFUNDED = "refunded", "Refunded"

    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="refund_requests")
    requested_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="refund_requests"
    )
    reason = models.TextField(blank=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    amount = models.DecimalField(max_digits=12, decimal_places=0)
    reference = models.CharField(max_length=100, blank=True)  # the refund's id in the ZarinPal panel / bank
    admin_note = models.TextField(blank=True)
    decided_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="+"
    )
    decided_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ("-created_at",)
        constraints = [
            models.UniqueConstraint(
                fields=("order",), condition=models.Q(status="pending"), name="one_open_refund_request_per_order"
            ),
        ]

    def __str__(self):
        return f"Refund of order #{self.order_id} ({self.status})"
