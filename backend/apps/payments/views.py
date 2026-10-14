from django.conf import settings
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
from .services import finalize_payment


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
            raise NotFound("سفارش پیدا نشد یا قبلاً پردازش شده است.") from exc

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
            raise NotFound("شناسه‌ی پرداخت نامعتبر است.") from exc

        # A repeat hit on an already-verified payment returns success without re-granting anything.
        payment = finalize_payment(payment, get_gateway())
        outcome = "paid" if payment.status == Payment.Status.VERIFIED else "failed"
        return redirect(f"{settings.ZARINPAL_CALLBACK_URL}?order_id={payment.order_id}&status={outcome}")
