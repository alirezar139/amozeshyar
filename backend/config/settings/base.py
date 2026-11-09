"""Base Django settings shared by every environment.

Environment-specific settings (dev/prod/test) import from this module and
override only what differs, per the twelve-factor convention used across
this project (see docs/adr/ for the reasoning).
"""
from datetime import timedelta
from pathlib import Path

import environ

BASE_DIR = Path(__file__).resolve().parent.parent.parent

env = environ.Env()
environ.Env.read_env(BASE_DIR / ".env")

SECRET_KEY = env("DJANGO_SECRET_KEY")
DEBUG = False
ALLOWED_HOSTS = env.list("DJANGO_ALLOWED_HOSTS", default=[])

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    # third-party
    "rest_framework",
    "rest_framework_simplejwt",
    "rest_framework_simplejwt.token_blacklist",
    "corsheaders",
    "django_filters",
    "drf_spectacular",
    "storages",
    # local apps
    "apps.common",
    "apps.accounts",
    "apps.instructors",
    "apps.courses",
    "apps.videos",
    "apps.enrollments",
    "apps.payments",
    "apps.messaging",
    "apps.board",
    "apps.exams",
    "apps.monitoring",
    "apps.notifications",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.locale.LocaleMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    # Records API error responses for the developer's live log (apps/monitoring).
    "apps.monitoring.middleware.APIErrorLogMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"
ASGI_APPLICATION = "config.asgi.application"

# --- Database ---
DATABASES = {
    "default": env.db("DATABASE_URL", default="postgres://postgres:postgres@localhost:5432/amozeshyar"),
}
# Reuse DB connections across requests (each new one costs ~40 ms) and
# check them before use so a restarted Postgres doesn't surface as errors.
DATABASES["default"]["CONN_MAX_AGE"] = env.int("DB_CONN_MAX_AGE", default=60)
DATABASES["default"]["CONN_HEALTH_CHECKS"] = True

# --- Custom user model ---
AUTH_USER_MODEL = "accounts.User"

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator", "OPTIONS": {"min_length": 10}},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

# --- i18n: Persian (default) + English, per product requirement ---
LANGUAGE_CODE = "fa"
LANGUAGES = [
    ("fa", "Persian"),
    ("en", "English"),
]
LOCALE_PATHS = [BASE_DIR / "locale"]
TIME_ZONE = "Asia/Tehran"
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
MEDIA_URL = "media/"
MEDIA_ROOT = BASE_DIR / "media"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# --- DRF ---
REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": (
        "rest_framework_simplejwt.authentication.JWTAuthentication",
    ),
    "DEFAULT_PERMISSION_CLASSES": ("rest_framework.permissions.IsAuthenticated",),
    "DEFAULT_FILTER_BACKENDS": ("django_filters.rest_framework.DjangoFilterBackend",),
    "DEFAULT_PAGINATION_CLASS": "apps.common.pagination.StandardResultsPagination",
    "PAGE_SIZE": 20,
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
    "DEFAULT_THROTTLE_CLASSES": (
        "rest_framework.throttling.AnonRateThrottle",
        "rest_framework.throttling.UserRateThrottle",
    ),
    "DEFAULT_THROTTLE_RATES": {
        "anon": "100/hour",
        "user": "1000/hour",
        "auth": "10/minute",
        "payment_callback": "30/minute",
        "video_manifest": "120/minute",
        "password_reset": "5/hour",
    },
    "EXCEPTION_HANDLER": "apps.common.exceptions.custom_exception_handler",
}

# --- SimpleJWT ---
SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(minutes=15),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=14),
    "ROTATE_REFRESH_TOKENS": True,
    "BLACKLIST_AFTER_ROTATION": True,
    "UPDATE_LAST_LOGIN": True,
    "AUTH_HEADER_TYPES": ("Bearer",),
    "USER_ID_FIELD": "id",
}

# --- CORS ---
CORS_ALLOWED_ORIGINS = env.list("CORS_ALLOWED_ORIGINS", default=[])
CORS_ALLOW_CREDENTIALS = True

# --- drf-spectacular ---
SPECTACULAR_SETTINGS = {
    "TITLE": "Amozeshyar LMS API",
    "DESCRIPTION": "REST API for the Amozeshyar online-learning & instructor-marketing platform.",
    "VERSION": "1.0.0",
    "SERVE_INCLUDE_SCHEMA": False,
    # Both Course.Status and InstructorProfile.Status are plain "status"
    # choice fields; without this, drf-spectacular gives them disambiguating
    # hash suffixes (Status1a4Enum) instead of readable names.
    "ENUM_NAME_OVERRIDES": {
        "CourseStatusEnum": "apps.courses.models.Course.Status",
        "InstructorStatusEnum": "apps.instructors.models.InstructorProfile.Status",
    },
}

# --- Celery ---
CELERY_BROKER_URL = env("CELERY_BROKER_URL", default="redis://localhost:6379/0")
CELERY_RESULT_BACKEND = env("CELERY_RESULT_BACKEND", default="redis://localhost:6379/0")
CELERY_ACCEPT_CONTENT = ["json"]
CELERY_TASK_SERIALIZER = "json"
CELERY_RESULT_SERIALIZER = "json"
CELERY_TIMEZONE = TIME_ZONE
CELERY_BEAT_SCHEDULE = {
    # Enrolls buyers whose browser never made it back to the payment callback.
    "reconcile-pending-payments": {
        "task": "apps.payments.tasks.reconcile_pending_payments",
        "schedule": 600.0,
    },
}

# --- Object storage (S3-compatible; MinIO in dev, Iranian cloud provider in prod) ---
STORAGES = {
    "default": {
        "BACKEND": "apps.common.storage.SharedSessionS3Storage",
    },
    "staticfiles": {
        "BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage",
    },
}
AWS_ACCESS_KEY_ID = env("STORAGE_ACCESS_KEY", default="")
AWS_SECRET_ACCESS_KEY = env("STORAGE_SECRET_KEY", default="")
AWS_STORAGE_BUCKET_NAME = env("STORAGE_BUCKET_NAME", default="amozeshyar-media")
AWS_S3_ENDPOINT_URL = env("STORAGE_ENDPOINT_URL", default="http://localhost:9000")
AWS_S3_REGION_NAME = env("STORAGE_REGION", default="us-east-1")
AWS_DEFAULT_ACL = "private"
AWS_QUERYSTRING_EXPIRE = 600  # signed URLs expire after 10 minutes
AWS_S3_ADDRESSING_STYLE = "path"

# --- Video preview / paywall defaults ---
# Actual value is normally read from the singleton `videos.PreviewPolicy`
# row so admins can tune it without a deploy; this is only the fallback.
DEFAULT_PREVIEW_SECONDS = env.int("DEFAULT_PREVIEW_SECONDS", default=30)

# --- Payments (ZarinPal) ---
ZARINPAL_MERCHANT_ID = env("ZARINPAL_MERCHANT_ID", default="")
ZARINPAL_SANDBOX = env.bool("ZARINPAL_SANDBOX", default=True)
# The site page a buyer lands on after paying (gets ?order_id=&status=paid|failed).
# ZarinPal itself returns to the API's /payments/callback/, which verifies first.
ZARINPAL_CALLBACK_URL = env("ZARINPAL_CALLBACK_URL", default="http://localhost:3000/checkout/callback")

# --- Public site address (links in emails/SMS, e.g. the password reset page) ---
SITE_URL = env("SITE_URL", default="http://localhost:3300").rstrip("/")

# --- Password reset: a signed link valid this long, and only until the password changes ---
PASSWORD_RESET_TIMEOUT = env.int("PASSWORD_RESET_TIMEOUT_MINUTES", default=30) * 60

# --- Notifications (apps/notifications) ---
# Channels a notification may use; each also needs its own configuration below.
NOTIFICATION_CHANNELS = env.list("NOTIFICATION_CHANNELS", default=["inbox", "email", "sms"])
# Email is on only when EMAIL_URL is set, e.g. smtp+tls://user:password@smtp.example.com:587
_email_url = env("EMAIL_URL", default="")
EMAIL_ENABLED = bool(_email_url)
if EMAIL_ENABLED:
    vars().update(env.email_url("EMAIL_URL"))
EMAIL_TIMEOUT = 10
DEFAULT_FROM_EMAIL = env("DEFAULT_FROM_EMAIL", default="no-reply@localhost")
# Dotted path to an SMS provider class with send(phone, text); empty = no SMS.
SMS_PROVIDER = env("SMS_PROVIDER", default="")

# --- Sentry ---
SENTRY_DSN = env("SENTRY_DSN", default="")

# --- Security headers (tightened further in prod.py) ---
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_REFERRER_POLICY = "strict-origin-when-cross-origin"
X_FRAME_OPTIONS = "DENY"
