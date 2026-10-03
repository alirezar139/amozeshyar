"""Development settings: verbose errors, permissive hosts, local storage fallback."""
from .base import *  # noqa: F401,F403

DEBUG = True
ALLOWED_HOSTS = ["*"]

INSTALLED_APPS += ["debug_toolbar"]  # noqa: F405
MIDDLEWARE = [
    "debug_toolbar.middleware.DebugToolbarMiddleware",
    "apps.common.middleware.RequestTimingMiddleware",
    "apps.common.live_log.APIErrorLogMiddleware",
    *MIDDLEWARE,  # noqa: F405
]
INTERNAL_IPS = ["127.0.0.1"]

# Temporary: tracking down a reported freeze on the admin calendar page.
# Tails to backend/logs/requests.log — see apps/common/middleware.py.
LOGS_DIR = BASE_DIR / "logs"  # noqa: F405
LOGS_DIR.mkdir(exist_ok=True)
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "plain": {"format": "%(asctime)s %(message)s"},
        "live": {"format": "%(asctime)s %(levelname)s %(message)s", "datefmt": "%H:%M:%S"},
    },
    "handlers": {
        # Live error log (see apps/common/live_log.py): API errors, server
        # tracebacks and browser errors. Watch it with
        #   Get-Content backend\logs\live.log -Wait -Tail 20
        "live_file": {
            "class": "logging.FileHandler",
            "filename": LOGS_DIR / "live.log",
            "formatter": "live",
            "encoding": "utf-8",
            "level": "WARNING",
        },
        "requests_file": {
            "class": "logging.FileHandler",
            "filename": LOGS_DIR / "requests.log",
            "formatter": "plain",
            "encoding": "utf-8",
        },
    },
    "loggers": {
        "requests": {"handlers": ["requests_file"], "level": "INFO", "propagate": False},
        "live": {"handlers": ["live_file"], "level": "WARNING", "propagate": False},
        # 5xx tracebacks (4xx are already logged with their body by "live").
        "django.request": {"handlers": ["live_file"], "level": "ERROR", "propagate": True},
        "apps": {"handlers": ["live_file"], "level": "WARNING", "propagate": True},
    },
}
# Redirect interception is more confusing than useful when just clicking
# around the admin/login flow during dev.
DEBUG_TOOLBAR_CONFIG = {"INTERCEPT_REDIRECTS": False}

CORS_ALLOWED_ORIGINS = [
    "http://localhost:3300",
    "http://127.0.0.1:3300",
]
# Windows' Hyper-V/WSL reserved port ranges move between reboots, so Nuxt
# sometimes can't bind 3300 and falls back to another port — accept any
# local port in dev rather than breaking every API call.
CORS_ALLOWED_ORIGIN_REGEXES = [r"^http://(localhost|127\.0\.0\.1):\d+$"]

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
