from django.db import transaction
from rest_framework import serializers

from apps.courses.models import Course
from apps.enrollments.models import Enrollment

from . import services
from .models import Coupon, Order, OrderItem, Payment


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

    class Meta:
        model = Order
        fields = ("id", "status", "total_amount", "currency", "coupon_code", "items", "created_at")


class InitiatePaymentResponseSerializer(serializers.Serializer):
    redirect_url = serializers.URLField()


class PaymentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Payment
        fields = ("id", "order", "gateway", "status", "created_at")
        read_only_fields = fields
