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
    used_count = models.PositiveIntegerField(default=0)

    def __str__(self):
        return self.code

    @property
    def is_valid(self) -> bool:
        from django.utils import timezone

        now = timezone.now()
        if not (self.valid_from <= now <= self.valid_to):
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

    def __str__(self):
        return f"Order #{self.id} ({self.status})"


class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="items")
    course = models.ForeignKey(Course, on_delete=models.PROTECT, related_name="order_items")
    price_at_purchase = models.DecimalField(max_digits=12, decimal_places=0)

    class Meta:
        unique_together = ("order", "course")


class Payment(TimeStampedModel):
    class Status(models.TextChoices):
        INITIATED = "initiated", "Initiated"
        VERIFIED = "verified", "Verified"
        FAILED = "failed", "Failed"

    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="payments")
    gateway = models.CharField(max_length=30, default="zarinpal")
    authority = models.CharField(max_length=100, blank=True)  # ZarinPal "Authority" token
    ref_id = models.CharField(max_length=100, blank=True)  # ZarinPal ref id on success
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.INITIATED)
    raw_response = models.JSONField(default=dict, blank=True)  # full gateway payload, for audit/debugging

    def __str__(self):
        return f"Payment #{self.id} for Order #{self.order_id} ({self.status})"
