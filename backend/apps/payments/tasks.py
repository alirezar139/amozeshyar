import logging
from datetime import timedelta

from celery import shared_task
from django.utils import timezone

from .models import Payment
from .services import finalize_payment

logger = logging.getLogger(__name__)

# A buyer may still be on the gateway page this long after starting to pay.
SETTLE_AFTER = timedelta(minutes=15)
# Past this, an unsuccessful verification means the payment really failed.
GIVE_UP_AFTER = timedelta(hours=1)
# Gateway authorities don't live longer than this; older rows aren't worth asking about.
LOOK_BACK = timedelta(days=2)


@shared_task
def reconcile_pending_payments() -> int:
    """Verify payments whose buyer never came back from the gateway.

    If the browser closes or the connection drops after paying, the callback
    never runs: the money is taken but the student isn't enrolled. This asks
    the gateway about every such payment and finalizes the ones that were paid.
    Returns how many payments it verified.
    """
    from .views import get_gateway

    now = timezone.now()
    stale = Payment.objects.filter(
        status=Payment.Status.INITIATED,
        created_at__lte=now - SETTLE_AFTER,
        created_at__gte=now - LOOK_BACK,
    ).select_related("order")

    gateway = get_gateway()
    verified = 0
    for payment in stale:
        try:
            payment = finalize_payment(payment, gateway, mark_failed=payment.created_at <= now - GIVE_UP_AFTER)
        except Exception:  # one unreachable/odd payment must not stop the rest
            logger.exception("Could not reconcile payment %s", payment.id)
            continue
        if payment.status == Payment.Status.VERIFIED:
            verified += 1
            logger.info("Reconciled payment %s for order %s", payment.id, payment.order_id)
    return verified
