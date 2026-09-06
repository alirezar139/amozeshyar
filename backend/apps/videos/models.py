import secrets
from datetime import timedelta

from django.conf import settings
from django.db import models
from django.utils import timezone

from apps.common.models import TimeStampedModel
from apps.courses.models import Lesson


def generate_session_token() -> str:
    return secrets.token_urlsafe(32)


class VideoAsset(TimeStampedModel):
    """The uploaded/processed video behind one lesson.

    Paywall design (see docs/adr/video-preview-gating.md): non-purchasers
    are only ever handed a URL to `preview_clip_key`, a physically
    truncated file produced by the transcoding task — never the full file
    gated by a client-side timer, since that is trivially bypassed via
    devtools or a direct request to the underlying object URL.
    """

    class Status(models.TextChoices):
        UPLOADING = "uploading", "Uploading"
        PROCESSING = "processing", "Processing"
        READY = "ready", "Ready"
        FAILED = "failed", "Failed"

    lesson = models.OneToOneField(Lesson, on_delete=models.CASCADE, related_name="video_asset")
    original_filename = models.CharField(max_length=255)
    storage_key = models.CharField(max_length=500)  # original upload, owner-download only
    hls_master_key = models.CharField(max_length=500, blank=True)  # full transcoded rendition, enrolled-only
    preview_clip_key = models.CharField(max_length=500, blank=True)  # physically-truncated clip, public
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.UPLOADING)
    duration_seconds = models.PositiveIntegerField(null=True, blank=True)
    file_size_bytes = models.BigIntegerField(null=True, blank=True)
    checksum_sha256 = models.CharField(max_length=64, blank=True)
    processing_error = models.TextField(blank=True)

    def __str__(self):
        return f"Video for {self.lesson}"

    @property
    def effective_preview_seconds(self) -> int:
        course = self.lesson.course
        if course.preview_seconds_override is not None:
            return course.preview_seconds_override
        return PreviewPolicy.get_default_seconds()


class PreviewPolicy(models.Model):
    """Singleton row holding the site-wide default free-preview length.

    A model (rather than a plain setting) so an admin can tune it from the
    Django admin without a deploy; `Course.preview_seconds_override` can
    still override it per course.
    """

    default_preview_seconds = models.PositiveIntegerField(default=30)

    class Meta:
        verbose_name_plural = "Preview policy"

    def save(self, *args, **kwargs):
        self.pk = 1
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        pass  # singleton: never actually deletable

    @classmethod
    def get_default_seconds(cls) -> int:
        obj, _ = cls.objects.get_or_create(pk=1, defaults={"default_preview_seconds": settings.DEFAULT_PREVIEW_SECONDS})
        return obj.default_preview_seconds


class WatchSession(TimeStampedModel):
    """A short-lived, server-issued session used to gate access to the full-video manifest/segments.

    Re-checked (not just created once) on every manifest fetch so revoking
    access mid-session (refund, subscription lapse) takes effect quickly.
    """

    video = models.ForeignKey(VideoAsset, on_delete=models.CASCADE, related_name="watch_sessions")
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, null=True, blank=True)
    session_token = models.CharField(max_length=64, unique=True, default=generate_session_token, db_index=True)
    has_full_access = models.BooleanField(default=False)
    expires_at = models.DateTimeField()
    client_ip = models.GenericIPAddressField(null=True, blank=True)

    @classmethod
    def issue(cls, video: VideoAsset, user, has_full_access: bool, client_ip: str | None = None) -> "WatchSession":
        return cls.objects.create(
            video=video,
            user=user if getattr(user, "is_authenticated", False) else None,
            has_full_access=has_full_access,
            expires_at=timezone.now() + timedelta(hours=4),
            client_ip=client_ip,
        )

    @property
    def is_expired(self) -> bool:
        return timezone.now() >= self.expires_at
