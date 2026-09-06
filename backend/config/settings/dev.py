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
