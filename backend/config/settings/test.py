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

# Fail in seconds, not minutes, when Postgres isn't running (e.g. Docker is off).
DATABASES["default"].setdefault("OPTIONS", {})["connect_timeout"] = 5  # noqa: F405

# Signed media links are computed locally (no request to the storage server),
# but boto3 still needs a key pair to sign with; never use the real one here.
AWS_ACCESS_KEY_ID = "test-access-key"  # noqa: S105
AWS_SECRET_ACCESS_KEY = "test-secret-key"  # noqa: S105
