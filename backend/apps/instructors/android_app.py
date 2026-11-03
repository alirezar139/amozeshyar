"""The site's Android app (APK), kept in the media storage like any other file.

Not in git (a binary per release) and not on GitHub (unreliable from Iran):
`manage.py publish_android_app` puts the build CI produced here, and visitors
download it through a short-lived signed link.
"""
from botocore.exceptions import ClientError
from django.core.files.base import File
from django.core.files.storage import default_storage

APK_KEY = "apps/android/app.apk"


def is_published() -> bool:
    # Not storage.exists(): django-storages' S3 backend answers False without
    # asking whenever file_overwrite is on. Reading the size really checks.
    try:
        default_storage.size(APK_KEY)
    except (FileNotFoundError, ClientError):
        return False
    return True


def publish(fileobj) -> None:
    # Same key every release, so the download link never changes.
    default_storage.delete(APK_KEY)
    saved = default_storage.save(APK_KEY, File(fileobj))
    if saved != APK_KEY:
        raise RuntimeError(f"storage saved the APK as {saved}, not {APK_KEY}")


def download_url(filename: str) -> str:
    from apps.videos.services.signing import get_download_url

    return get_download_url(APK_KEY, filename)
