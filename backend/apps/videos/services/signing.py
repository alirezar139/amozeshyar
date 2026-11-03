"""Presigned-URL issuance for the S3-compatible object storage backend.

Every object is private; the only way to reach a video byte is through one
of these short-lived, single-object URLs, minted per-request after the
caller's permissions have already been checked by the view.
"""
from urllib.parse import quote

from django.conf import settings
from django.core import signing
from django.core.files.storage import default_storage

from apps.common.storage import SharedSessionS3Storage

_storage = SharedSessionS3Storage()


def get_presigned_url(storage_key: str, expires_in: int = 600) -> str:
    """Return a short-lived signed URL for `storage_key`.

    `expires_in` defaults to `AWS_QUERYSTRING_EXPIRE` (10 min); callers
    issuing preview/manifest links should keep it short so a leaked link
    (screenshot, shared chat) stops working quickly.
    """
    return _storage.url(storage_key, expire=expires_in)


def get_download_url(storage_key: str, filename: str, expires_in: int = 300) -> str:
    """Presigned URL forcing a browser download (Content-Disposition), for the owner/admin download endpoint."""
    # RFC 6266: an ASCII fallback plus the real (often Persian) name as UTF-8.
    stem, dot, ext = filename.rpartition(".")
    if not dot:
        stem, ext = filename, ""
    ascii_stem = stem.encode("ascii", "ignore").decode().replace('"', "").strip() or "download"
    ascii_ext = ext.encode("ascii", "ignore").decode().replace('"', "")
    ascii_name = f"{ascii_stem}.{ascii_ext}" if ascii_ext else ascii_stem
    disposition = f"attachment; filename=\"{ascii_name}\"; filename*=UTF-8''{quote(filename)}"
    params = {"ResponseContentDisposition": disposition}
    return _storage.bucket.meta.client.generate_presigned_url(
        "get_object",
        Params={"Bucket": settings.AWS_STORAGE_BUCKET_NAME, "Key": storage_key, **params},
        ExpiresIn=expires_in,
    )


# --- HLS playback -----------------------------------------------------------
# A presigned URL covers exactly one object, but an HLS playlist points at
# many segment files by relative name. So the playlist itself is served by
# the API (behind a short-lived token minted after the access check), with
# every segment line rewritten to its own presigned URL.

PLAYLIST_TOKEN_SALT = "videos.hls-playlist"
PLAYLIST_TOKEN_MAX_AGE = 600  # seconds to start playback after the access check


def make_playlist_token(video_id: int) -> str:
    return signing.dumps({"v": video_id}, salt=PLAYLIST_TOKEN_SALT, compress=True)


def playlist_token_is_valid(token: str, video_id: int) -> bool:
    try:
        payload = signing.loads(token, salt=PLAYLIST_TOKEN_SALT, max_age=PLAYLIST_TOKEN_MAX_AGE)
    except signing.BadSignature:  # also covers SignatureExpired
        return False
    return payload.get("v") == video_id


def segment_url_lifetime(duration_seconds: int | None) -> int:
    """Segments must stay fetchable for the whole viewing (pauses included), so
    twice the video's length, at least 2 hours and at most 12."""
    return min(max(2 * (duration_seconds or 0), 2 * 3600), 12 * 3600)


def signed_playlist(playlist_key: str, duration_seconds: int | None) -> str:
    """The stored playlist with every segment URI swapped for a presigned URL."""
    with default_storage.open(playlist_key, "rb") as fh:
        text = fh.read().decode("utf-8")
    folder = playlist_key.rsplit("/", 1)[0]
    expires_in = segment_url_lifetime(duration_seconds)
    lines = []
    for line in text.splitlines():
        stripped = line.strip()
        if stripped and not stripped.startswith("#"):
            line = get_presigned_url(f"{folder}/{stripped}", expires_in=expires_in)
        lines.append(line)
    return "\n".join(lines) + "\n"
