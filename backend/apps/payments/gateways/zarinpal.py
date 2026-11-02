"""ZarinPal REST integration (https://www.zarinpal.com/docs/paymentGateway/).

Sandbox vs live is switched purely by base URL (`ZARINPAL_SANDBOX`), so the
same code path is exercised in dev and prod — reducing the chance that a
sandbox-only bug ships unnoticed.
"""
import requests
from django.conf import settings

from .base import PaymentGateway, PaymentGatewayError, PaymentRequestResult, PaymentVerifyResult

REQUEST_TIMEOUT = 15


def to_rial(toman) -> int:
    # Prices are stored in Toman, but ZarinPal reads `amount` as Rial unless told
    # otherwise; sending Toman as-is would charge a tenth of the price.
    return int(toman) * 10


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
            "amount": to_rial(order.total_amount),
            "callback_url": callback_url,
            "description": f"Order #{order.id}",
        }
        try:
            response = requests.post(self.request_url, json=payload, timeout=REQUEST_TIMEOUT)
            body = response.json()
        except (requests.RequestException, ValueError) as exc:
            raise PaymentGatewayError("gateway unreachable") from exc
        # On rejection ZarinPal answers 4xx with `data: []` and the reason in `errors`.
        data = body.get("data") or {}
        authority = data.get("authority", "")
        if data.get("code") != 100 or not authority:
            raise PaymentGatewayError(str(body.get("errors") or body))
        return PaymentRequestResult(
            redirect_url=f"{self.gateway_redirect_base}{authority}",
            authority=authority,
        )

    def verify(self, authority: str, amount: int) -> PaymentVerifyResult:
        payload = {"merchant_id": self.merchant_id, "amount": to_rial(amount), "authority": authority}
        response = requests.post(self.verify_url, json=payload, timeout=REQUEST_TIMEOUT)
        # An unpaid authority comes back as 4xx with a JSON reason: that's an
        # answer ("not paid"), not an outage, so only 5xx raises.
        if response.status_code >= 500:
            response.raise_for_status()
        body = response.json()
        data = body.get("data") or {}
        # ZarinPal codes 100 (verified) and 101 (already verified) both count as success.
        success = data.get("code") in (100, 101)
        return PaymentVerifyResult(
            success=success,
            ref_id=str(data.get("ref_id", "")),
            raw_response=body,
            error_message="" if success else (body.get("errors") or {}).get("message", "Verification failed"),
        )
