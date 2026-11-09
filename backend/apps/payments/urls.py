from django.urls import include, path
from rest_framework.routers import DefaultRouter

from . import views

# The instructor's sales panel (admin role): /api/v1/payments/admin/...
admin_router = DefaultRouter()
admin_router.register("orders", views.AdminOrderViewSet, basename="admin-order")
admin_router.register("payments", views.AdminPaymentViewSet, basename="admin-payment")
admin_router.register("coupons", views.AdminCouponViewSet, basename="admin-coupon")
admin_router.register("refunds", views.AdminRefundViewSet, basename="admin-refund")

urlpatterns = [
    path("orders/", views.OrderListCreateView.as_view(), name="order-list"),
    path("orders/<int:order_id>/refund-request/", views.RefundRequestView.as_view(), name="order-refund-request"),
    path("initiate/<int:order_id>/", views.InitiatePaymentView.as_view(), name="payment-initiate"),
    path("callback/", views.PaymentCallbackView.as_view(), name="payment-callback"),
    path("admin/summary/", views.SalesSummaryView.as_view(), name="admin-sales-summary"),
    path("admin/", include(admin_router.urls)),
]
