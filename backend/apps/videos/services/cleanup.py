"""Removing the stored files of videos that were deleted or replaced (VID-01).

A video's files all share its original's name: the original `lessons/<lesson>/<id>/original_x.mp4`,
its HLS output under `.../original_x/hls/` and its preview `.../original_x/preview.mp4`.
`video_prefixes()` gives those two prefixes. Nothing is ever deleted while a remaining
VideoAsset still points inside a prefix (or the prefix inside one of its own): that covers a
re-upload that landed on the same key, and anything else unexpected.

Only the `lessons/` area is ever touched; lesson handouts live under `lesson_files/`.
"""
import logging
from datetime import timedelta

from django.core.files.storage import default_storage
from django.utils import timezone

logger = logging.getLogger("apps.videos")

VIDEO_ROOT = "lessons/"
DELETE_BATCH = 1000  # S3 DeleteObjects limit


def video_prefixes(storage_key: str) -> list[str]:
    """The original's exact key, and the folder its HLS output and preview live in."""
    if not storage_key:
        return []
    return [storage_key, storage_key.rsplit(".", 1)[0] + "/"]


def referenced_prefixes() -> list[str]:
    from apps.videos.models import VideoAsset

    prefixes = []
    for key in VideoAsset.objects.exclude(storage_key="").values_list("storage_key", flat=True):
        prefixes += video_prefixes(key)
    return prefixes


def _in_use(key_or_prefix: str, referenced: list[str]) -> bool:
    return any(key_or_prefix.startswith(r) or r.startswith(key_or_prefix) for r in referenced)


def _keys_under(prefix: str) -> list[str]:
    """Stored keys equal to `prefix`, or under it when it ends with '/'."""
    if hasattr(default_storage, "bucket"):
        keys = [o.key for o in default_storage.bucket.objects.filter(Prefix=prefix)]
    else:  # file/in-memory storage (tests, local dev without MinIO)
        keys = _walk(prefix.rsplit("/", 1)[0] if "/" in prefix else "")
        keys = [k for k in keys if k.startswith(prefix)]
    return keys if prefix.endswith("/") else [k for k in keys if k == prefix]


def _walk(folder: str) -> list[str]:
    try:
        dirs, files = default_storage.listdir(folder)
    except (FileNotFoundError, OSError):
        return []
    found = [f"{folder}/{f}" if folder else f for f in files]
    for d in dirs:
        found += _walk(f"{folder}/{d}" if folder else d)
    return found


def delete_keys(keys: list[str]) -> None:
    if not keys:
        return
    if hasattr(default_storage, "bucket"):
        bucket = default_storage.bucket
        for i in range(0, len(keys), DELETE_BATCH):
            bucket.delete_objects(Delete={"Objects": [{"Key": k} for k in keys[i:i + DELETE_BATCH]], "Quiet": True})
    else:
        for key in keys:
            default_storage.delete(key)


def delete_unreferenced(prefixes: list[str]) -> int:
    """Delete everything stored under `prefixes` that no VideoAsset uses any more. Returns the count."""
    referenced = referenced_prefixes()
    deleted = 0
    for prefix in prefixes:
        if not prefix.startswith(VIDEO_ROOT) or _in_use(prefix, referenced):
            logger.info("Keeping %s: still used by a video", prefix)
            continue
        keys = [k for k in _keys_under(prefix) if not _in_use(k, referenced)]
        delete_keys(keys)
        deleted += len(keys)
    if deleted:
        logger.info("Deleted %s stored files of removed videos", deleted)
    return deleted


def find_orphans(min_age: timedelta) -> list[dict]:
    """Objects under lessons/ that no VideoAsset uses, older than `min_age` (an upload in flight
    is written before its VideoAsset row exists). S3/MinIO only."""
    if not hasattr(default_storage, "bucket"):
        return []
    referenced = referenced_prefixes()
    cutoff = timezone.now() - min_age
    return [
        {"key": o.key, "size": o.size, "modified": o.last_modified}
        for o in default_storage.bucket.objects.filter(Prefix=VIDEO_ROOT)
        if o.last_modified < cutoff and not _in_use(o.key, referenced)
    ]
