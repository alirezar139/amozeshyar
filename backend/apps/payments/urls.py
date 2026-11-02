from django.urls import path

from . import views

urlpatterns = [
    path("orders/", views.OrderListCreateView.as_view(), name="order-list"),
    path("initiate/<int:order_id>/", views.InitiatePaymentView.as_view(), name="payment-initiate"),
    path("callback/", views.PaymentCallbackView.as_view(), name="payment-callback"),
]
