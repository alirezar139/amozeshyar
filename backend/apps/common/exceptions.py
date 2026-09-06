import logging

from rest_framework.views import exception_handler

logger = logging.getLogger("apps")


def custom_exception_handler(exc, context):
    """Wrap DRF's default handler so every unhandled error is logged with request context.

    Unhandled (non-APIException) errors still return DRF's None, which
    Django turns into a 500; the logging here is what lets Sentry/ops
    actually see what request triggered it.
    """
    response = exception_handler(exc, context)
    if response is None:
        request = context.get("request")
        logger.exception("Unhandled exception on %s", getattr(request, "path", "?"))
    return response
