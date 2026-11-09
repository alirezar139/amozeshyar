from django.conf import settings
from django.db import IntegrityError, transaction
from django.db.models import Count, Q
from django.shortcuts import redirect
from django.urls import reverse
from django.utils.dateparse import parse_date
from drf_spectacular.utils import extend_schema
from rest_framework import generics, permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import APIException, NotFound, ValidationError
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView

from apps.accounts.permissions import IsAdminRole

from . import sales, services
from .gateways.base import PaymentGatewayError
from .gateways.zarinpal import ZarinPalGateway
from .models import Coupon, Order, OrderItem, Payment, RefundRequest
from .serializers import (
    AdminCouponSerializer,
    AdminOrderSerializer,
    AdminPaymentSerializer,
    AdminRefundSerializer,
    CreateOrderSerializer,
    InitiatePaymentResponseSerializer,
    OrderSerializer,
    RefundDecisionSerializer,
    RefundRequestCreateSerializer,
    RefundStatusSerializer,
)


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
            .prefetch_related("items__course", "refund_requests")
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


class RefundRequestView(APIView):
    """The student asks for the money of one of their paid orders back; the instructor decides."""

    permission_classes = (permissions.IsAuthenticated,)
    serializer_class = RefundStatusSerializer

    @extend_schema(request=RefundRequestCreateSerializer, responses={201: RefundStatusSerializer})
    def post(self, request, order_id):
        payload = RefundRequestCreateSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        order = Order.objects.filter(id=order_id, user=request.user).first()
        if order is None:
            raise NotFound("سفارش پیدا نشد.")
        if order.status != Order.Status.PAID or not order.total_amount:
            raise ValidationError("فقط برای سفارش پرداخت‌شده‌ی غیررایگان می‌توان درخواست استرداد داد.")
        if order.refund_requests.filter(status=RefundRequest.Status.PENDING).exists():
            raise ValidationError("برای این سفارش یک درخواست بررسی‌نشده دارید.")
        try:
            with transaction.atomic():
                refund = RefundRequest.objects.create(
                    order=order, requested_by=request.user, reason=payload.validated_data["reason"],
                    amount=order.total_amount,
                )
        except IntegrityError:  # a simultaneous duplicate hit the one-open-request constraint
            raise ValidationError("برای این سفارش یک درخواست بررسی‌نشده دارید.") from None
        return Response(RefundStatusSerializer(refund).data, status=status.HTTP_201_CREATED)


# ---------- the instructor's sales panel (admin role only) ----------

class SalesSummaryView(APIView):
    """Revenue and payment counts for the last `?days=` days (default 30)."""

    permission_classes = (permissions.IsAuthenticated, IsAdminRole)

    @extend_schema(responses={200: None})
    def get(self, request):
        try:
            days = min(max(int(request.query_params.get("days", 30)), 1), 3650)
        except ValueError:
            raise ValidationError({"days": "یک عدد روز وارد کنید."}) from None
        return Response(sales.summary(days))


class AdminOrderViewSet(viewsets.ReadOnlyModelViewSet):
    """`?status=`, `?search=` (email, name, phone, order number), `?course=`, `?date_from=`/`?date_to=` (YYYY-MM-DD)."""

    serializer_class = AdminOrderSerializer
    permission_classes = (permissions.IsAuthenticated, IsAdminRole)

    def get_queryset(self):
        orders = (
            sales.site_orders()
            .select_related("user", "coupon")
            .prefetch_related("items__course", "payments", "refund_requests")
            .order_by("-created_at")
        )
        params = self.request.query_params
        if params.get("status") in Order.Status.values:
            orders = orders.filter(status=params["status"])
        if params.get("search", "").strip():
            orders = orders.filter(sales.search_filter(params["search"].strip()))
        if params.get("course", "").isdigit():
            orders = orders.filter(id__in=OrderItem.objects.filter(course_id=int(params["course"])).values("order_id"))
        for param, lookup in (("date_from", "created_at__date__gte"), ("date_to", "created_at__date__lte")):
            if params.get(param):
                day = parse_date(params[param])
                if day is None:
                    raise ValidationError({param: "تاریخ را به شکل YYYY-MM-DD بفرستید."})
                orders = orders.filter(**{lookup: day})
        return orders

    @extend_schema(request=RefundDecisionSerializer, responses=AdminRefundSerializer)
    @action(detail=True, methods=["post"])
    def refund(self, request, pk=None):
        """Record a refund the instructor made without a request (the money is returned in the ZarinPal panel)."""
        order = self.get_object()
        payload = RefundDecisionSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        try:
            refund = sales.complete_refund(None, order=order, by=request.user, **payload.validated_data)
        except sales.RefundError as exc:
            raise ValidationError(str(exc)) from None
        return Response(AdminRefundSerializer(refund).data)


class AdminPaymentViewSet(viewsets.ReadOnlyModelViewSet):
    """Every gateway transaction, newest first; `?status=initiated|verified|failed|canceled`."""

    serializer_class = AdminPaymentSerializer
    permission_classes = (permissions.IsAuthenticated, IsAdminRole)

    def get_queryset(self):
        payments = sales.site_payments().select_related("order__user").order_by("-created_at")
        if self.request.query_params.get("status") in Payment.Status.values:
            payments = payments.filter(status=self.request.query_params["status"])
        return payments


class AdminCouponViewSet(viewsets.ModelViewSet):
    """Discount codes. A code that was ever used can't be deleted (end it by moving `valid_to`)."""

    serializer_class = AdminCouponSerializer
    permission_classes = (permissions.IsAuthenticated, IsAdminRole)

    def get_queryset(self):
        return Coupon.objects.annotate(
            paid_orders=Count("order", filter=Q(order__status=Order.Status.PAID))
        ).order_by("-created_at")

    def perform_destroy(self, instance):
        if instance.used_count or Order.objects.filter(coupon=instance).exists():
            raise ValidationError("این کد در سفارش‌ها استفاده شده و حذف نمی‌شود؛ تاریخ پایانش را به امروز تغییر دهید.")
        instance.delete()


class AdminRefundViewSet(viewsets.ReadOnlyModelViewSet):
    """Refund requests, newest first; `?status=pending|rejected|refunded`."""

    serializer_class = AdminRefundSerializer
    permission_classes = (permissions.IsAuthenticated, IsAdminRole)

    def get_queryset(self):
        refunds = (
            sales.site_refunds()
            .select_related("order__user", "decided_by")
            .prefetch_related("order__items__course")
            .order_by("-created_at")
        )
        if self.request.query_params.get("status") in RefundRequest.Status.values:
            refunds = refunds.filter(status=self.request.query_params["status"])
        return refunds

    def _decide(self, request, decide):
        payload = RefundDecisionSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        try:
            refund = decide(self.get_object(), payload.validated_data)
        except sales.RefundError as exc:
            raise ValidationError(str(exc)) from None
        return Response(AdminRefundSerializer(sales.site_refunds().get(id=refund.id)).data)

    @extend_schema(request=RefundDecisionSerializer, responses=AdminRefundSerializer)
    @action(detail=True, methods=["post"])
    def complete(self, request, pk=None):
        """The money was returned: give the ZarinPal panel's or bank's reference."""
        return self._decide(request, lambda r, d: sales.complete_refund(r, order=r.order, by=request.user, **d))

    @extend_schema(request=RefundDecisionSerializer, responses=AdminRefundSerializer)
    @action(detail=True, methods=["post"])
    def reject(self, request, pk=None):
        return self._decide(request, lambda r, d: sales.reject_refund(r, by=request.user, note=d["note"]))
