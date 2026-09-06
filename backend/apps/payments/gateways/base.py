"""Payment gateway interface.

Kept deliberately narrow so a second gateway (Zibal, IDPay, a direct bank
IPG) can be added later without touching Order/Enrollment logic anywhere
else in the codebase — every gateway-specific detail lives behind this
contract.
"""
from dataclasses import dataclass


@dataclass
class PaymentRequestResult:
    redirect_url: str
    authority: str


@dataclass
class PaymentVerifyResult:
    success: bool
    ref_id: str = ""
    raw_response: dict | None = None
    error_message: str = ""


class PaymentGateway:
    def create_payment_request(self, order, callback_url: str) -> PaymentRequestResult:
        raise NotImplementedError

    def verify(self, authority: str, amount: int) -> PaymentVerifyResult:
        raise NotImplementedError
