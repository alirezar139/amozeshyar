"""Development settings: verbose errors, permissive hosts, local storage fallback."""
from .base import *  # noqa: F401,F403

DEBUG = True
ALLOWED_HOSTS = ["*"]

INSTALLED_APPS += ["debug_toolbar"]  # noqa: F405
MIDDLEWARE = ["debug_toolbar.middleware.DebugToolbarMiddleware", *MIDDLEWARE]  # noqa: F405
INTERNAL_IPS = ["127.0.0.1"]
# Redirect interception is more confusing than useful when just clicking
# around the admin/login flow during dev.
DEBUG_TOOLBAR_CONFIG = {"INTERCEPT_REDIRECTS": False}

CORS_ALLOWED_ORIGINS = [
    "http://localhost:3300",
    "http://127.0.0.1:3300",
]

# SimpleJWT refresh cookie isn't Secure-only in dev (no HTTPS on localhost).
SESSION_COOKIE_SECURE = False
CSRF_COOKIE_SECURE = False

# The production rates in base.py are easy to exhaust while actively
# developing/demoing from a single machine (every browser tab shares one
# IP) — loosen them here so local testing doesn't get self-DoS'd.
REST_FRAMEWORK["DEFAULT_THROTTLE_RATES"] = {  # noqa: F405
    "anon": "10000/hour",
    "user": "10000/hour",
    "auth": "1000/minute",
    "payment_callback": "1000/minute",
    "video_manifest": "1000/minute",
}
