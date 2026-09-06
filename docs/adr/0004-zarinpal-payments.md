# ADR 0004: ZarinPal as the payment gateway

## Status
Accepted

## Context
The platform's user base is Iranian; international processors (Stripe, PayPal) are not viable in this market. The client confirmed ZarinPal as the preferred gateway.

## Decision
Implement `apps.payments.gateways.base.PaymentGateway` as a narrow interface (`create_payment_request`, `verify`) and `apps.payments.gateways.zarinpal.ZarinPalGateway` as the concrete implementation, switched via `ZARINPAL_SANDBOX`. `apps.payments.views.get_gateway()` is the single place that decides which gateway implementation is active, so adding a second gateway later (Zibal, IDPay, a direct bank IPG) does not require touching `Order`/`Enrollment` logic anywhere else.

The callback endpoint (`PaymentCallbackView`) is written to be idempotent (checks `Payment.status` before re-processing, uses `select_for_update` inside an atomic transaction) since ZarinPal — and users hitting back/refresh — can call it more than once for the same authority.

## Consequences
- Amounts are handled as Toman integers (`DecimalField(decimal_places=0)`), matching ZarinPal's API rather than assuming a currency with subunits.
- Storage bucket/CDN choice (ADR pending) is independent of this decision but shares the same "Iranian-market-first" reasoning.
