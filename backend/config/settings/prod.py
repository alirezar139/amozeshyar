"""Production settings: hardened security headers, strict hosts/origins."""
import sentry_sdk
from sentry_sdk.integrations.django import DjangoIntegration

from .base import *  # noqa: F401,F403
from .base import env

DEBUG = False

SECURE_SSL_REDIRECT = True
SECURE_HSTS_SECONDS = 31536000
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SESSION_COOKIE_SAMESITE = "Lax"
CSRF_COOKIE_SAMESITE = "Lax"

if SENTRY_DSN:  # noqa: F405
    sentry_sdk.init(
        dsn=SENTRY_DSN,  # noqa: F405
        integrations=[DjangoIntegration()],
        traces_sample_rate=0.2,
        send_default_pii=False,
    )

STORAGES["staticfiles"] = {  # noqa: F405
    "BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage",
}
MIDDLEWARE.insert(1, "whitenoise.middleware.WhiteNoiseMiddleware")  # noqa: F405

# Region-specific hosting note (see docs/adr/): the client's user base is
# Iranian, so ALLOWED_HOSTS/CORS must point at the deployed domestic domain,
# never assumed to be a generic *.com — configure via env per deployment.
ALLOWED_HOSTS = env.list("DJANGO_ALLOWED_HOSTS")
CORS_ALLOWED_ORIGINS = env.list("CORS_ALLOWED_ORIGINS")
CSRF_TRUSTED_ORIGINS = env.list("CSRF_TRUSTED_ORIGINS", default=CORS_ALLOWED_ORIGINS)

# TLS ends at the reverse proxy (nginx), which forwards plain HTTP. Without this
# Django thinks every request is insecure and SECURE_SSL_REDIRECT loops forever.
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")

# DRF throttles key on the client IP. Behind exactly one proxy (host nginx) the real IP is the
# last X-Forwarded-For entry; without this a client could send its own X-Forwarded-For and get
# a fresh throttle bucket per request (bypassing the login/payment rate limits).
REST_FRAMEWORK["NUM_PROXIES"] = 1  # noqa: F405

# The OpenAPI schema maps every endpoint; in production only staff (the developer account) may
# read it. Developers can still generate it locally with `manage.py spectacular`.
SPECTACULAR_SETTINGS["SERVE_PERMISSIONS"] = ["rest_framework.permissions.IsAdminUser"]  # noqa: F405

# Captcha challenges and DRF throttle counters live in the cache. The default per-process
# LocMemCache breaks both under gunicorn's multiple workers: a puzzle created in one worker
# can't be verified in another, and each worker counts login attempts separately.
CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.redis.RedisCache",
        "LOCATION": env("CACHE_URL", default="redis://redis:6379/1"),
        "KEY_PREFIX": "amozeshyar",
    }
}

# Logs go to stdout; Docker keeps them (rotated: see x-logging in deploy/docker-compose.prod.yml)
# and `docker compose logs backend worker worker-video` reads them. One line per event, with the
# logger name, so payments/videos/db problems can be grepped for. Without this, Django drops
# 500 tracebacks in production (they go to mail_admins, and ADMINS is empty).
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "line": {"format": "%(asctime)s %(levelname)s %(name)s [%(process)d] %(message)s"},
    },
    "handlers": {
        "stdout": {"class": "logging.StreamHandler", "stream": "ext://sys.stdout", "formatter": "line"},
    },
    "root": {"handlers": ["stdout"], "level": "WARNING"},
    "loggers": {
        # Request errors with tracebacks (5xx), and 4xx at WARNING.
        "django.request": {"level": "WARNING", "propagate": True},
        # Database errors surface through django.request / the app loggers; this adds slow-query
        # and connection-level warnings without logging every SQL statement.
        "django.db.backends": {"level": "WARNING", "propagate": True},
        "django.security": {"level": "WARNING", "propagate": True},
        # Our code: payments (verify, refunds, unclear gateway answers), videos (transcode,
        # retries, cleanup), notifications, monitoring. INFO keeps the payment trail.
        "apps": {"level": "INFO", "propagate": True},
        # The live-log middleware writes 4xx bodies here too; they're already in ErrorEvent.
        "live": {"level": "ERROR", "propagate": True},
        "celery": {"level": "INFO", "propagate": True},
        "celery.task": {"level": "INFO", "propagate": True},
        "gunicorn.error": {"level": "INFO", "propagate": True},
    },
}

# Nuxt's SSR calls the backend directly on the Docker network (Host: backend:8000) and names the
# public host in X-Forwarded-Host. nginx always overwrites that header for outside requests, and
# the value is still checked against ALLOWED_HOSTS.
USE_X_FORWARDED_HOST = True
