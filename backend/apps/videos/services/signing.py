"""Presigned-URL issuance for the S3-compatible object storage backend.

Every object is private; the only way to reach a video byte is through one
of these short-lived, single-object URLs, minted per-request after the
caller's permissions have already been checked by the view.
"""
from django.conf import settings
from storages.backends.s3 import S3Storage

_storage = S3Storage()


def get_presigned_url(storage_key: str, expires_in: int = 600) -> str:
    """Return a short-lived signed URL for `storage_key`.

    `expires_in` defaults to `AWS_QUERYSTRING_EXPIRE` (10 min); callers
    issuing preview/manifest links should keep it short so a leaked link
    (screenshot, shared chat) stops working quickly.
    """
    return _storage.url(storage_key, expire=expires_in)


def get_download_url(storage_key: str, filename: str, expires_in: int = 300) -> str:
    """Presigned URL forcing a browser download (Content-Disposition), for the owner/admin download endpoint."""
    params = {"ResponseContentDisposition": f'attachment; filename="{filename}"'}
    return _storage.bucket.meta.client.generate_presigned_url(
        "get_object",
        Params={"Bucket": settings.AWS_STORAGE_BUCKET_NAME, "Key": storage_key, **params},
        ExpiresIn=expires_in,
    )
