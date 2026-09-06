from django.conf import settings
from django.db import transaction
from django.shortcuts import redirect
from drf_spectacular.utils import extend_schema
from rest_framework import generics, permissions, status
from rest_framework.exceptions import NotFound
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView

from .gateways.zarinpal import ZarinPalGateway
from .models import Order, Payment
from .serializers import CreateOrderSerializer, InitiatePaymentResponseSerializer, OrderSerializer


def get_gateway():
    # Single-gateway MVP; swap/branch here if a second gateway is added later.
    return ZarinPalGateway()


class CreateOrderView(generics.CreateAPIView):
    serializer_class = CreateOrderSerializer
    permission_classes = (permissions.IsAuthenticated,)

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        order = serializer.save()
        return Response(OrderSerializer(order).data, status=status.HTTP_201_CREATED)


class InitiatePaymentView(APIView):
    permission_classes = (permissions.IsAuthenticated,)
    throttle_classes = (ScopedRateThrottle,)
    throttle_scope = "payment_callback"
    serializer_class = InitiatePaymentResponseSerializer

    @extend_schema(request=None, responses=InitiatePaymentResponseSerializer)
    def post(self, request, order_id):
        try:
            order = Order.objects.get(id=order_id, user=request.user, status=Order.Status.PENDING)
        except Order.DoesNotExist as exc:
            raise NotFound("Order not found or already processed.") from exc

        gateway = get_gateway()
        result = gateway.create_payment_request(order, settings.ZARINPAL_CALLBACK_URL)
        Payment.objects.create(order=order, authority=result.authority, status=Payment.Status.INITIATED)
        return Response({"redirect_url": result.redirect_url})


class PaymentCallbackView(APIView):
    """ZarinPal redirects the user's browser here after payment.

    Must be idempotent: the gateway (or the user hitting back/refresh) can
    call this more than once for the same authority, and it must not grant
    a duplicate enrollment or double-process the order.
    """

    permission_classes = (permissions.AllowAny,)
    throttle_classes = (ScopedRateThrottle,)
    throttle_scope = "payment_callback"

    @extend_schema(responses={302: None})
    def get(self, request):
        authority = request.query_params.get("Authority", "")
        try:
            payment = Payment.objects.select_related("order").get(authority=authority)
        except Payment.DoesNotExist as exc:
            raise NotFound("Unknown payment authority.") from exc

        if payment.status == Payment.Status.VERIFIED:
            # Already processed by a prior callback hit — return success without re-granting anything.
            return redirect(f"{settings.ZARINPAL_CALLBACK_URL}?order_id={payment.order_id}&status=paid")

        gateway = get_gateway()
        result = gateway.verify(authority, int(payment.order.total_amount))

        with transaction.atomic():
            payment = Payment.objects.select_for_update().get(id=payment.id)
            if payment.status == Payment.Status.VERIFIED:
                return redirect(f"{settings.ZARINPAL_CALLBACK_URL}?order_id={payment.order_id}&status=paid")

            payment.raw_response = result.raw_response or {}
            if not result.success:
                payment.status = Payment.Status.FAILED
                payment.save(update_fields=["status", "raw_response"])
                return redirect(f"{settings.ZARINPAL_CALLBACK_URL}?order_id={payment.order_id}&status=failed")

            payment.status = Payment.Status.VERIFIED
            payment.ref_id = result.ref_id
            payment.save(update_fields=["status", "ref_id", "raw_response"])

            order = payment.order
            order.status = Order.Status.PAID
            order.save(update_fields=["status"])

            from apps.enrollments.models import Enrollment

            for item in order.items.select_related("course"):
                Enrollment.objects.get_or_create(
                    student=order.user, course=item.course, defaults={"order_item": item}
                )

        return redirect(f"{settings.ZARINPAL_CALLBACK_URL}?order_id={order.id}&status=paid")
