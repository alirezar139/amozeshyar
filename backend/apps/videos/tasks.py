"""Video background jobs.

transcode_video_asset_task runs on the "video" queue (its own worker); everything else here is
short and runs on "default" next to payment reconciliation (see CELERY_TASK_ROUTES).
"""
import logging
from datetime import timedelta

from celery import shared_task
from django.db.models import F, Q
from django.utils import timezone

from apps.videos.services import transcoder
from apps.videos.services.cleanup import delete_unreferenced

logger = logging.getLogger("apps.videos")

# Storage hiccups are retried this many times, waiting 1, 2, 4... minutes in between.
TRANSIENT_RETRIES = 4
# A PROCESSING video whose try started longer ago than this has lost its worker.
STALE_PROCESSING = timedelta(seconds=transcoder.MAX_TRANSCODE_SECONDS + 1800)
# An UPLOADING video this old was never picked up (its queued task was lost).
STALE_UPLOADING = timedelta(hours=2)
# recover_stuck_videos stops re-queuing a video after this many worker starts.
MAX_ATTEMPTS = 3


def stale_processing(now) -> Q:
    """PROCESSING for longer than any transcode can take: its worker is gone.

    Videos that were already PROCESSING when processing_started_at was added have no start time;
    their last change (updated_at) stands in for it, or they'd never be recovered.
    """
    from apps.videos.models import VideoAsset

    cutoff = now - STALE_PROCESSING
    return Q(status=VideoAsset.Status.PROCESSING) & (
        Q(processing_started_at__lt=cutoff) | Q(processing_started_at__isnull=True, updated_at__lt=cutoff)
    )


def claim(video_asset_id: int, task_id: str = "") -> bool:
    """Atomically move the video to PROCESSING; False if another worker owns it or it's done.

    Makes a duplicate delivery harmless: it only runs if nobody is working on the video. The one
    exception is the same task coming back (task_id): its worker was stopped mid-transcode and
    handed the message back to the queue, so nobody else is working on it; it starts over.
    A try that has been going on too long (STALE_PROCESSING) is taken over too.
    """
    from apps.videos.models import VideoAsset

    now = timezone.now()
    claimable = Q(status=VideoAsset.Status.UPLOADING) | stale_processing(now)
    if task_id:
        claimable |= Q(status=VideoAsset.Status.PROCESSING, processing_task_id=task_id)
    return bool(
        VideoAsset.objects.filter(claimable, id=video_asset_id).update(
            status=VideoAsset.Status.PROCESSING, processing_started_at=now, processing_task_id=task_id,
            attempts=F("attempts") + 1,
        )
    )


@shared_task(bind=True, max_retries=TRANSIENT_RETRIES)
def transcode_video_asset_task(self, video_asset_id: int):
    from apps.videos.models import VideoAsset

    if self.request.retries == 0 and not claim(video_asset_id, self.request.id or ""):
        logger.info("VideoAsset %s is already being processed or done; skipping", video_asset_id)
        return
    if self.request.retries:
        # A retry of our own transient failure: we still own the video; restart its clock.
        VideoAsset.objects.filter(id=video_asset_id, status=VideoAsset.Status.PROCESSING).update(processing_started_at=timezone.now())
    try:
        transcoder.transcode_video_asset(video_asset_id)
    except VideoAsset.DoesNotExist:
        logger.info("VideoAsset %s was deleted before it was transcoded", video_asset_id)
    except transcoder.TransientTranscodeError as exc:
        if self.request.retries >= self.max_retries:
            logger.error("VideoAsset %s: storage kept failing, giving up: %s", video_asset_id, exc)
            transcoder.mark_failed(video_asset_id, f"ذخیره‌سازی در دسترس نبود ({exc}). دوباره تلاش کنید.")
            return
        countdown = 60 * 2 ** self.request.retries
        logger.warning("VideoAsset %s: %s; retrying in %ss", video_asset_id, exc, countdown)
        raise self.retry(exc=exc, countdown=countdown) from exc


def enqueue_transcode(video_asset_id: int) -> None:
    transcode_video_asset_task.delay(video_asset_id)


@shared_task
def recover_stuck_videos() -> dict:
    """Every 15 minutes (beat): find videos whose transcode will never finish on its own.

    - UPLOADING for over 2 hours: the queued task was lost (e.g. Redis restarted before it ran).
    - PROCESSING past the longest possible transcode: its worker died mid-way.
    Each is queued again, up to MAX_ATTEMPTS worker starts; after that it's marked FAILED so the
    instructor sees it and can retry by hand.
    """
    from apps.videos.models import VideoAsset

    now = timezone.now()
    stuck = VideoAsset.objects.filter(
        Q(status=VideoAsset.Status.UPLOADING, updated_at__lt=now - STALE_UPLOADING)
        | stale_processing(now)
    )
    requeued = failed = 0
    for video in stuck:
        if video.attempts >= MAX_ATTEMPTS:
            transcoder.mark_failed(video.id, f"پردازش ویدیو {video.attempts} بار ناتمام ماند. دوباره تلاش کنید یا فایل دیگری بفرستید.")
            logger.error("VideoAsset %s gave up after %s attempts", video.id, video.attempts)
            failed += 1
            continue
        if video.status == VideoAsset.Status.PROCESSING:
            # Hand it back to the queue as a fresh upload, so claim() takes it.
            VideoAsset.objects.filter(id=video.id, status=VideoAsset.Status.PROCESSING).update(status=VideoAsset.Status.UPLOADING)
        enqueue_transcode(video.id)
        logger.warning("VideoAsset %s was stuck (%s); queued again", video.id, video.status)
        requeued += 1
    return {"requeued": requeued, "failed": failed}


@shared_task
def delete_video_files(prefixes: list[str]) -> int:
    """Remove the stored files of deleted/replaced videos (default queue), skipping any still in use."""
    return delete_unreferenced(prefixes)
