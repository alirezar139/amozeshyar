from django.conf import settings
from django.db import transaction
from django.shortcuts import redirect
from django.urls import reverse
from drf_spectacular.utils import extend_schema
from rest_framework import generics, permissions, status
from rest_framework.exceptions import APIException, NotFound
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView

from .gateways.base import PaymentGatewayError
from .gateways.zarinpal import ZarinPalGateway
from .models import Order, Payment
from .serializers import CreateOrderSerializer, InitiatePaymentResponseSerializer, OrderSerializer
from .services import finalize_payment, fulfil_order


def get_gateway():
    # Single-gateway MVP; swap/branch here if a second gateway is added later.
    return ZarinPalGateway()


class GatewayUnavailable(APIException):
    status_code = status.HTTP_502_BAD_GATEWAY
    default_detail = "اتصال به درگاه پرداخت برقرار نشد. لطفاً چند دقیقه‌ی دیگر دوباره تلاش کنید."


class OrderListCreateView(generics.ListCreateAPIView):
    """GET: the student's own orders, newest first. POST: a new order.

    An order with nothing to pay (a free course, or a 100% coupon) is
    fulfilled right here and comes back ``paid`` — the client skips the
    gateway for it.
    """

    permission_classes = (permissions.IsAuthenticated,)

    def get_serializer_class(self):
        return CreateOrderSerializer if self.request.method == "POST" else OrderSerializer

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):
            return Order.objects.none()
        return (
            Order.objects.filter(user=self.request.user)
            .select_related("coupon")
            .prefetch_related("items__course")
            .order_by("-created_at")
        )

    @extend_schema(responses={201: OrderSerializer})
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        with transaction.atomic():
            order = serializer.save()
            if order.total_amount == 0:
                fulfil_order(order)
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

        # ZarinPal sends the buyer back to the API, which verifies and then
        # redirects on to the site's result page (ZARINPAL_CALLBACK_URL).
        callback_url = request.build_absolute_uri(reverse("payment-callback"))
        try:
            result = get_gateway().create_payment_request(order, callback_url)
        except PaymentGatewayError as exc:
            raise GatewayUnavailable() from exc
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
