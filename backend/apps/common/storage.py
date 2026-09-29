import threading

from storages.backends.s3 import S3Storage

_session = None
_session_lock = threading.Lock()


class SharedSessionS3Storage(S3Storage):
    """S3Storage that builds its boto3 Session once per process.

    django-storages keeps one S3 connection per *thread*, and each one
    started from a brand-new boto3 Session, which re-parses botocore's
    service definitions: ~400-500 ms. The dev server (and threaded
    workers) serve every request on a fresh thread, so every request that
    rendered a file URL paid that cost. A shared Session keeps the
    per-thread connection cheap (~5 ms); sessions are safe to create
    resources from across threads, and the lock only guards the first build.
    """

    def _create_session(self):
        global _session
        if _session is None:
            with _session_lock:
                if _session is None:
                    _session = super()._create_session()
        return _session
