from django.db import transaction
from rest_framework import serializers

from apps.courses.models import Course
from apps.enrollments.models import Enrollment

from . import services
from .models import Coupon, Order, OrderItem, Payment, RefundRequest


class CreateOrderSerializer(serializers.Serializer):
    course_ids = serializers.ListField(child=serializers.IntegerField(), allow_empty=False)
    coupon_code = serializers.CharField(required=False, allow_blank=True)

    def validate_course_ids(self, value):
        courses = Course.objects.filter(id__in=value, status=Course.Status.PUBLISHED)
        if courses.count() != len(set(value)):
            raise serializers.ValidationError("یک یا چند دوره در دسترس نیست.")
        user = self.context["request"].user
        if Enrollment.objects.filter(student=user, course_id__in=value, is_active=True).exists():
            raise serializers.ValidationError("شما قبلاً در این دوره ثبت‌نام کرده‌اید.")
        return value

    def validate_coupon_code(self, value):
        code = value.strip()
        if not code:
            return None
        coupon = Coupon.objects.filter(code__iexact=code).first()
        if coupon is None or not coupon.is_valid:
            raise serializers.ValidationError("کد تخفیف معتبر نیست یا منقضی شده است.")
        return coupon

    def create(self, validated_data):
        """Place the order, or hand back the buyer's identical open order (``self.reused``).

        The checks above ran without locks; they are repeated here under the buyer's row lock
        (and the coupon's), which is what makes them hold under simultaneous requests.
        A free order (free course, 100% coupon) is fulfilled in the same transaction.
        """
        user = self.context["request"].user
        course_ids = set(validated_data["course_ids"])
        coupon = validated_data.get("coupon_code")
        with transaction.atomic():
            services.lock_buyer(user.id)
            if services.enrolled_course_ids(user, course_ids):
                raise serializers.ValidationError({"course_ids": "شما قبلاً در این دوره ثبت‌نام کرده‌اید."})
            if coupon is not None:
                coupon = Coupon.objects.select_for_update().get(id=coupon.id)
            existing = services.reuse_or_retire_open_orders(user, course_ids, coupon)
            if existing is not None:
                self.reused = True
                return existing
            if coupon is not None:
                problem = services.coupon_problem(coupon, user)
                if problem:
                    raise serializers.ValidationError({"coupon_code": problem})
            courses = Course.objects.filter(id__in=course_ids)
            subtotal = sum(c.effective_price for c in courses)
            order = Order.objects.create(user=user, total_amount=apply_coupon(subtotal, coupon), coupon=coupon)
            OrderItem.objects.bulk_create(
                [OrderItem(order=order, course=c, price_at_purchase=c.effective_price) for c in courses]
            )
            if order.total_amount == 0:
                services.fulfil_order(order)
        self.reused = False
        return order


def apply_coupon(subtotal, coupon):
    """The amount left to pay after ``coupon``, never below zero."""
    if coupon is None:
        return subtotal
    discount = 0
    if coupon.discount_percent:
        discount = subtotal * min(coupon.discount_percent, 100) // 100
    elif coupon.discount_amount:
        discount = coupon.discount_amount
    return max(subtotal - discount, 0)


class OrderItemSerializer(serializers.ModelSerializer):
    course_title = serializers.CharField(source="course.title", read_only=True)
    course_slug = serializers.CharField(source="course.slug", read_only=True)

    class Meta:
        model = OrderItem
        fields = ("course_title", "course_slug", "price_at_purchase")


class OrderSerializer(serializers.ModelSerializer):
    items = OrderItemSerializer(many=True, read_only=True)
    coupon_code = serializers.CharField(source="coupon.code", read_only=True, default=None)
    refund = serializers.SerializerMethodField()

    class Meta:
        model = Order
        fields = ("id", "status", "total_amount", "currency", "coupon_code", "items", "refund", "created_at")

    def get_refund(self, obj) -> dict | None:
        """The latest refund request (prefetch `refund_requests` to avoid a query per order)."""
        latest = max(obj.refund_requests.all(), key=lambda r: r.created_at, default=None)
        return RefundStatusSerializer(latest).data if latest else None


class InitiatePaymentResponseSerializer(serializers.Serializer):
    redirect_url = serializers.URLField()


class PaymentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Payment
        fields = ("id", "order", "gateway", "status", "created_at")
        read_only_fields = fields


# ---------- refunds (student side) ----------

class RefundStatusSerializer(serializers.ModelSerializer):
    class Meta:
        model = RefundRequest
        fields = ("id", "status", "reason", "admin_note", "created_at", "decided_at")
        read_only_fields = fields


class RefundRequestCreateSerializer(serializers.Serializer):
    reason = serializers.CharField(max_length=1000, trim_whitespace=True)


# ---------- the instructor's sales panel ----------

class BuyerSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    email = serializers.EmailField()
    first_name = serializers.CharField()
    last_name = serializers.CharField()
    phone_number = serializers.CharField()


class AdminPaymentSerializer(serializers.ModelSerializer):
    buyer_email = serializers.EmailField(source="order.user.email", read_only=True)

    class Meta:
        model = Payment
        fields = ("id", "order", "buyer_email", "gateway", "authority", "ref_id", "status", "note", "created_at")
        read_only_fields = fields


class AdminRefundSerializer(serializers.ModelSerializer):
    buyer = BuyerSerializer(source="order.user", read_only=True)
    order_total = serializers.DecimalField(source="order.total_amount", max_digits=12, decimal_places=0, read_only=True)
    decided_by_email = serializers.EmailField(source="decided_by.email", read_only=True, default=None)
    courses = serializers.SerializerMethodField()

    class Meta:
        model = RefundRequest
        fields = (
            "id", "order", "order_total", "buyer", "courses", "reason", "status", "amount", "reference",
            "admin_note", "decided_by_email", "decided_at", "created_at",
        )
        read_only_fields = fields

    def get_courses(self, obj) -> list[str]:
        return [i.course.title for i in obj.order.items.all()]


class AdminOrderSerializer(serializers.ModelSerializer):
    buyer = BuyerSerializer(source="user", read_only=True)
    items = OrderItemSerializer(many=True, read_only=True)
    coupon_code = serializers.CharField(source="coupon.code", read_only=True, default=None)
    payments = AdminPaymentSerializer(many=True, read_only=True)
    refunds = RefundStatusSerializer(source="refund_requests", many=True, read_only=True)

    class Meta:
        model = Order
        fields = (
            "id", "status", "total_amount", "currency", "coupon_code", "buyer", "items", "payments", "refunds",
            "created_at", "paid_at",
        )
        read_only_fields = fields


class RefundDecisionSerializer(serializers.Serializer):
    reference = serializers.CharField(max_length=100, required=False, allow_blank=True, default="")
    note = serializers.CharField(max_length=2000, required=False, allow_blank=True, default="")


class AdminCouponSerializer(serializers.ModelSerializer):
    held_orders = serializers.SerializerMethodField()
    paid_orders = serializers.IntegerField(read_only=True, default=0)

    class Meta:
        model = Coupon
        fields = (
            "id", "code", "discount_percent", "discount_amount", "valid_from", "valid_to",
            "max_uses", "max_uses_per_user", "used_count", "held_orders", "paid_orders", "created_at",
        )
        read_only_fields = ("id", "used_count", "held_orders", "paid_orders", "created_at")

    def get_held_orders(self, obj) -> int:
        return services.held_coupon_orders(obj).count()

    def validate_code(self, value):
        value = value.strip().upper()
        if not value or " " in value:
            raise serializers.ValidationError("کد را بدون فاصله وارد کنید.")
        clash = Coupon.objects.filter(code__iexact=value)
        if self.instance:
            clash = clash.exclude(pk=self.instance.pk)
        if clash.exists():
            raise serializers.ValidationError("کدی با همین نام وجود دارد.")
        return value

    def validate(self, attrs):
        get = lambda f: attrs[f] if f in attrs else getattr(self.instance, f, None)  # noqa: E731
        percent, amount = get("discount_percent"), get("discount_amount")
        if bool(percent) == bool(amount):
            raise serializers.ValidationError("فقط یکی از «درصد» یا «مبلغ» تخفیف را وارد کنید.")
        if percent is not None and percent and not 1 <= percent <= 100:
            raise serializers.ValidationError({"discount_percent": "درصد تخفیف باید بین ۱ تا ۱۰۰ باشد."})
        if amount is not None and amount and amount <= 0:
            raise serializers.ValidationError({"discount_amount": "مبلغ تخفیف باید بیشتر از صفر باشد."})
        valid_from, valid_to = get("valid_from"), get("valid_to")
        if valid_from and valid_to and valid_to <= valid_from:
            raise serializers.ValidationError({"valid_to": "پایان اعتبار باید بعد از شروع آن باشد."})
        used = self.instance.used_count if self.instance else 0
        if get("max_uses") is not None and get("max_uses") < used:
            raise serializers.ValidationError({"max_uses": f"این کد تا الان {used} بار استفاده شده؛ سقف نمی‌تواند کمتر باشد."})
        return attrs
