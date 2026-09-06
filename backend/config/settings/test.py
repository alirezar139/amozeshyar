"""Settings used by the pytest suite: fast password hashing, in-memory-ish DB."""
from .base import *  # noqa: F401,F403

DEBUG = False
SECRET_KEY = "test-secret-key-not-for-production"

PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]

STORAGES["default"] = {  # noqa: F405
    "BACKEND": "django.core.files.storage.InMemoryStorage",
}

CELERY_TASK_ALWAYS_EAGER = True
CELERY_TASK_EAGER_PROPAGATES = True
