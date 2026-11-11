"""Throttles shared by every API view (REST_FRAMEWORK["DEFAULT_THROTTLE_CLASSES"])."""
from rest_framework.throttling import UserRateThrottle


class SignedInUserRateThrottle(UserRateThrottle):
    """The per-account cap, for signed-in users only.

    DRF's UserRateThrottle falls back to the client's IP for anonymous requests, so anonymous
    traffic was held by the lower of "anon" and "user" per IP: raising "anon" alone changed
    nothing for a classroom behind one IP. Anonymous requests are AnonRateThrottle's job.
    """

    def get_cache_key(self, request, view):
        if not (request.user and request.user.is_authenticated):
            return None
        return super().get_cache_key(request, view)
