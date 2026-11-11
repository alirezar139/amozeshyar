"""Reading ids from request parameters: a bad value is the caller's mistake (400), never a 500 (BE-01)."""
from rest_framework.exceptions import ValidationError


def id_param(value, name: str) -> int | None:
    """An id from a query parameter or body field: None if absent, ValidationError if it isn't one."""
    if value in (None, ""):
        return None
    try:
        number = int(value)
    except (TypeError, ValueError):
        raise ValidationError({name: "شناسه باید یک عدد باشد."}) from None
    if number < 0:
        raise ValidationError({name: "شناسه باید یک عدد باشد."})
    return number


def query_id(request, name: str) -> int | None:
    return id_param(request.query_params.get(name), name)
