"""ZarinPal REST integration (https://www.zarinpal.com/docs/paymentGateway/).

Sandbox vs live is switched purely by base URL (`ZARINPAL_SANDBOX`), so the
same code path is exercised in dev and prod — reducing the chance that a
sandbox-only bug ships unnoticed.
"""
import requests
from django.conf import settings

from .base import PaymentGateway, PaymentRequestResult, PaymentVerifyResult

REQUEST_TIMEOUT = 15


class ZarinPalGateway(PaymentGateway):
    def __init__(self):
        self.merchant_id = settings.ZARINPAL_MERCHANT_ID
        base = "sandbox.zarinpal.com" if settings.ZARINPAL_SANDBOX else "api.zarinpal.com"
        self.request_url = f"https://{base}/pg/v4/payment/request.json"
        self.verify_url = f"https://{base}/pg/v4/payment/verify.json"
        self.gateway_redirect_base = f"https://{base}/pg/StartPay/"

    def create_payment_request(self, order, callback_url: str) -> PaymentRequestResult:
        payload = {
            "merchant_id": self.merchant_id,
            "amount": int(order.total_amount),
            "callback_url": callback_url,
            "description": f"Order #{order.id}",
        }
        response = requests.post(self.request_url, json=payload, timeout=REQUEST_TIMEOUT)
        response.raise_for_status()
        data = response.json().get("data", {})
        authority = data.get("authority", "")
        return PaymentRequestResult(
            redirect_url=f"{self.gateway_redirect_base}{authority}",
            authority=authority,
        )

    def verify(self, authority: str, amount: int) -> PaymentVerifyResult:
        payload = {"merchant_id": self.merchant_id, "amount": amount, "authority": authority}
        response = requests.post(self.verify_url, json=payload, timeout=REQUEST_TIMEOUT)
        response.raise_for_status()
        body = response.json()
        data = body.get("data", {})
        # ZarinPal codes 100 (verified) and 101 (already verified) both count as success.
        success = data.get("code") in (100, 101)
        return PaymentVerifyResult(
            success=success,
            ref_id=str(data.get("ref_id", "")),
            raw_response=body,
            error_message="" if success else body.get("errors", {}).get("message", "Verification failed"),
        )
