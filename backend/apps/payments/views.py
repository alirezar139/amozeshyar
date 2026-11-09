from django.conf import settings
from django.shortcuts import redirect
from django.urls import reverse
from drf_spectacular.utils import extend_schema
from rest_framework import generics, permissions, status
from rest_framework.exceptions import APIException, NotFound
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView

from . import services
from .gateways.base import PaymentGatewayError
from .gateways.zarinpal import ZarinPalGateway
from .models import Order, Payment
from .serializers import CreateOrderSerializer, InitiatePaymentResponseSerializer, OrderSerializer


def get_gateway():
    # Single-gateway MVP; swap/branch here if a second gateway is added later.
    return ZarinPalGateway()


class GatewayUnavailable(APIException):
    status_code = status.HTTP_502_BAD_GATEWAY
    default_detail = "اتصال به درگاه پرداخت برقرار نشد. لطفاً چند دقیقه‌ی دیگر دوباره تلاش کنید."


class PaymentConflict(APIException):
    status_code = status.HTTP_409_CONFLICT
    default_code = "payment_conflict"


class OrderListCreateView(generics.ListCreateAPIView):
    """GET: the student's own orders, newest first. POST: a new order.

    An order with nothing to pay (a free course, or a 100% coupon) is
    fulfilled right here and comes back ``paid`` — the client skips the
    gateway for it. Asking again for exactly the same courses (and coupon)
    while that order is unpaid returns it again (200) instead of a second one.
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

    @extend_schema(responses={201: OrderSerializer, 200: OrderSerializer})
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            order = serializer.save()
        except services.OrderConflict as exc:
            raise PaymentConflict(
                "پرداخت دیگری برای همین دوره همین حالا در جریان است. چند دقیقه‌ی دیگر دوباره تلاش کنید."
            ) from exc
        code = status.HTTP_200_OK if serializer.reused else status.HTTP_201_CREATED
        return Response(OrderSerializer(order).data, status=code)


class InitiatePaymentView(APIView):
    """Send the buyer to the gateway. Pressing pay again while a payment of this order is still
    in progress returns that same payment, so one order never has two live payments."""

    permission_classes = (permissions.IsAuthenticated,)
    throttle_classes = (ScopedRateThrottle,)
    throttle_scope = "payment_callback"
    serializer_class = InitiatePaymentResponseSerializer

    @extend_schema(request=None, responses=InitiatePaymentResponseSerializer)
    def post(self, request, order_id):
        # ZarinPal sends the buyer back to the API, which verifies and then
        # redirects on to the site's result page (ZARINPAL_CALLBACK_URL).
        callback_url = request.build_absolute_uri(reverse("payment-callback"))
        try:
            redirect_url = services.start_payment(order_id, request.user, get_gateway(), callback_url)
        except Order.DoesNotExist as exc:
            raise NotFound("سفارش پیدا نشد یا قبلاً پردازش شده است.") from exc
        except services.AlreadyBought as exc:
            raise PaymentConflict("شما این دوره را قبلاً خریده‌اید؛ این سفارش لغو شد.") from exc
        except PaymentGatewayError as exc:
            raise GatewayUnavailable() from exc
        return Response({"redirect_url": redirect_url})


class PaymentCallbackView(APIView):
    """ZarinPal redirects the user's browser here after payment.

    Idempotent: the gateway (or the user hitting back/refresh) can call this
    more than once for the same authority; it never grants a duplicate
    enrollment or double-processes the order. Never a 500 either: when the
    gateway can't be reached the buyer is told the payment is being checked
    (``status=pending``) and reconciliation finishes it.
    """

    permission_classes = (permissions.AllowAny,)
    throttle_classes = (ScopedRateThrottle,)
    throttle_scope = "payment_callback"

    @extend_schema(responses={302: None})
    def get(self, request):
        authority = request.query_params.get("Authority", "")
        payment = Payment.objects.select_related("order").filter(authority=authority).first() if authority else None
        if payment is None:
            raise NotFound("شناسه‌ی پرداخت نامعتبر است.")

        payment = services.finalize_payment(payment, get_gateway())
        outcome = services.outcome_of(payment)
        return redirect(f"{settings.ZARINPAL_CALLBACK_URL}?order_id={payment.order_id}&status={outcome}")
