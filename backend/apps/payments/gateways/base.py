"""Payment gateway interface.

Kept deliberately narrow so a second gateway (Zibal, IDPay, a direct bank
IPG) can be added later without touching Order/Enrollment logic anywhere
else in the codebase — every gateway-specific detail lives behind this
contract.
"""
from dataclasses import dataclass


class PaymentGatewayError(Exception):
    """The gateway refused or failed to start a payment (bad amount, merchant, network)."""


class PaymentGatewayUnavailable(PaymentGatewayError):
    """No usable answer (timeout, connection error, 5xx, unreadable body).

    Says nothing about whether the buyer paid: the payment must stay open and be asked about again.
    """


@dataclass
class PaymentRequestResult:
    redirect_url: str
    authority: str


@dataclass
class PaymentVerifyResult:
    success: bool
    ref_id: str = ""
    # False when the gateway answered but the answer doesn't settle it (rate limit, a
    # merchant/terminal problem): not "paid", but not proof of "failed" either.
    definite: bool = True
    raw_response: dict | None = None
    error_message: str = ""


class PaymentGateway:
    def create_payment_request(self, order, callback_url: str) -> PaymentRequestResult:
        raise NotImplementedError

    def verify(self, authority: str, amount: int) -> PaymentVerifyResult:
        raise NotImplementedError

    def redirect_url(self, authority: str) -> str:
        """Where to send the buyer to pay an authority that was already issued."""
        raise NotImplementedError
