from django.urls import path

from . import views

urlpatterns = [
    path("orders/", views.CreateOrderView.as_view(), name="order-create"),
    path("initiate/<int:order_id>/", views.InitiatePaymentView.as_view(), name="payment-initiate"),
    path("callback/", views.PaymentCallbackView.as_view(), name="payment-callback"),
]
