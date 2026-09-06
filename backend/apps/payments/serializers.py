from rest_framework import serializers

from apps.courses.models import Course

from .models import Order, OrderItem, Payment


class CreateOrderSerializer(serializers.Serializer):
    course_ids = serializers.ListField(child=serializers.IntegerField(), allow_empty=False)
    coupon_code = serializers.CharField(required=False, allow_blank=True)

    def validate_course_ids(self, value):
        courses = Course.objects.filter(id__in=value, status=Course.Status.PUBLISHED)
        if courses.count() != len(set(value)):
            raise serializers.ValidationError("One or more courses are unavailable.")
        return value

    def create(self, validated_data):
        user = self.context["request"].user
        courses = Course.objects.filter(id__in=validated_data["course_ids"])
        order = Order.objects.create(user=user, total_amount=sum(c.effective_price for c in courses))
        OrderItem.objects.bulk_create(
            [OrderItem(order=order, course=c, price_at_purchase=c.effective_price) for c in courses]
        )
        return order


class OrderSerializer(serializers.ModelSerializer):
    class Meta:
        model = Order
        fields = ("id", "status", "total_amount", "currency", "created_at")


class InitiatePaymentResponseSerializer(serializers.Serializer):
    redirect_url = serializers.URLField()


class PaymentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Payment
        fields = ("id", "order", "gateway", "status", "created_at")
        read_only_fields = fields
