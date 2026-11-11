"""ffmpeg-based transcoding: produces the full HLS rendition plus a
physically-truncated preview clip.

Run as a Celery task on its own "video" queue (see tasks.py), so uploads return immediately,
processing happens off the request/response cycle, and payments never wait behind it.

Failures are of two kinds, and only one is worth retrying:
* TransientTranscodeError: reading the original from or writing results to storage failed
  (network, MinIO restarting). The task retries with backoff; nothing about the video is wrong.
* everything else (ffmpeg rejects the file, runs past its time limit): the video is marked
  FAILED with the reason, for the instructor to see and retry from the lesson card.
"""
import logging
import os
import shutil
import subprocess
import tempfile
from pathlib import Path

from django.conf import settings
from django.core.files.storage import default_storage

logger = logging.getLogger("apps.videos")


class TranscodeError(RuntimeError):
    pass


class TransientTranscodeError(RuntimeError):
    """Storage was unreachable; the same video may well succeed on the next try."""


# Tuned for recorded lessons (mostly a talking head, slides or a screen):
# CRF 26 looks the same as the default 23 for that kind of footage at a
# noticeably smaller size, and the maxrate cap keeps busy scenes from
# spiking the bitrate for viewers on mobile connections. yuv420p because
# phones and some cameras record 10-bit or 4:2:2, which browsers can't play.
# The preset trades encode time for file size: "medium" is the quality default; on a slow
# server set VIDEO_TRANSCODE_PRESET=veryfast (about 3x faster, files ~20% larger).
def _video_args() -> tuple[str, ...]:
    return (
        "-c:v", "libx264", "-preset", settings.VIDEO_TRANSCODE_PRESET, "-crf", "26",
        "-maxrate", "2500k", "-bufsize", "5000k", "-pix_fmt", "yuv420p",
        # x264's memory grows with its thread count; capped so the worker fits its memory limit.
        "-threads", str(settings.VIDEO_TRANSCODE_THREADS),
    )


AUDIO_ARGS = ("-c:a", "aac", "-b:a", "96k")
# At most 720p and never upscaled (that only makes the file bigger); both sides even, as x264 requires.
SCALE_FILTER = "scale=-2:'min(720,trunc(ih/2)*2)'"

# Each ffmpeg run may take this many times the video's length, within these bounds. The upper
# bound must stay below CELERY_BROKER_TRANSPORT_OPTIONS["visibility_timeout"] (7 h), or Redis
# would hand a transcode that is still running to a second worker.
TIME_PER_VIDEO_SECOND = 3
MIN_TRANSCODE_SECONDS = 30 * 60
MAX_TRANSCODE_SECONDS = 6 * 3600

# Lowest CPU priority: on a small server the website must stay responsive
# while a video is being encoded. Linux only: on Windows dev machines the
# `nice` that Git Bash provides mangles the filter's quotes on the way to ffmpeg.
NICE = ("nice", "-n", "19") if os.name == "posix" and shutil.which("nice") else ()


def transcode_timeout(duration_seconds: int | None) -> int:
    return int(min(max(TIME_PER_VIDEO_SECOND * (duration_seconds or 0), MIN_TRANSCODE_SECONDS), MAX_TRANSCODE_SECONDS))


def _run_ffmpeg(*args: str, timeout: int = MAX_TRANSCODE_SECONDS) -> None:
    try:
        result = subprocess.run(
            [*NICE, "ffmpeg", "-y", *args],
            capture_output=True,
            text=True,
            timeout=timeout,
        )
    except subprocess.TimeoutExpired as exc:
        raise TranscodeError(
            f"ffmpeg ran longer than {timeout // 60} minutes. On a slow server set VIDEO_TRANSCODE_PRESET=veryfast."
        ) from exc
    if result.returncode != 0:
        raise TranscodeError(result.stderr[-4000:])


def probe_duration_seconds(local_path: Path) -> int:
    result = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(local_path)],
        capture_output=True,
        text=True,
        timeout=120,
    )
    if result.returncode != 0:
        raise TranscodeError(result.stderr)
    return int(float(result.stdout.strip()))


def download_original(key: str, target: Path) -> None:
    """Copy a stored file to local disk without holding it in memory (originals can be gigabytes).

    On S3/MinIO it streams straight into the file, a couple of 8 MB parts at a time; any other
    storage (tests, local disk) is copied chunk by chunk.
    """
    bucket = getattr(default_storage, "bucket", None)
    if bucket is not None:
        from boto3.s3.transfer import TransferConfig

        bucket.download_file(default_storage._normalize_name(key), str(target),
                             Config=TransferConfig(max_concurrency=2, multipart_chunksize=8 * 1024 * 1024))
        return
    with default_storage.open(key, "rb") as src, open(target, "wb") as dst:
        shutil.copyfileobj(src, dst, 1024 * 1024)


def encode_hls(source: Path, playlist: Path, timeout: int = MAX_TRANSCODE_SECONDS) -> None:
    """The full lesson as a single-rendition HLS stream, in 6-second segments."""
    _run_ffmpeg(
        "-i", str(source),
        "-vf", SCALE_FILTER, *_video_args(), *AUDIO_ARGS,
        "-hls_time", "6", "-hls_playlist_type", "vod",
        str(playlist),
        timeout=timeout,
    )


def encode_preview(source: Path, target: Path, seconds: int, timeout: int = MIN_TRANSCODE_SECONDS) -> None:
    """The free preview: a separate file cut to `seconds`, with its index up front so playback starts at once."""
    _run_ffmpeg(
        "-i", str(source),
        "-t", str(seconds),
        "-vf", SCALE_FILTER, *_video_args(), *AUDIO_ARGS,
        "-movflags", "+faststart",
        str(target),
        timeout=timeout,
    )


def _storage(step: str, action):
    """Run a storage call, turning any failure into a retryable error."""
    try:
        return action()
    except Exception as exc:  # botocore/network/OS errors all mean "try again later"
        raise TransientTranscodeError(f"{step}: {type(exc).__name__}: {exc}") from exc


def transcode_video_asset(video_asset_id: int) -> None:
    """Download the original upload, produce HLS + preview clip, upload results, update the model.

    The caller (tasks.transcode_video_asset_task) has already claimed the video (status
    PROCESSING). Raises TransientTranscodeError for storage trouble, leaving the video as it is
    for the retry; any other failure marks it FAILED.

    Imported lazily inside the function body (not at module import time) to
    keep this module importable without Django apps being loaded yet, which
    matters for the Celery worker's autodiscovery import order.
    """
    from apps.videos.models import VideoAsset

    video_asset = VideoAsset.objects.select_related("lesson__course").get(id=video_asset_id)

    with tempfile.TemporaryDirectory() as tmp:
        tmp_dir = Path(tmp)
        original_path = tmp_dir / "original"
        try:
            def download():
                download_original(video_asset.storage_key, original_path)

            _storage("reading the original", download)

            duration = probe_duration_seconds(original_path)
            preview_seconds = video_asset.effective_preview_seconds
            timeout = transcode_timeout(duration)

            # Full HLS rendition (single 720p rendition for MVP; multi-bitrate is a later optimization).
            hls_dir = tmp_dir / "hls"
            hls_dir.mkdir()
            hls_playlist = hls_dir / "master.m3u8"
            encode_hls(original_path, hls_playlist, timeout=timeout)

            # Preview clip: a SEPARATE, physically-truncated file (not a
            # time-limited view into the full file) — this is what makes the
            # gate unbypassable by URL manipulation.
            preview_path = tmp_dir / "preview.mp4"
            encode_preview(original_path, preview_path, min(preview_seconds, duration))

            base_key = video_asset.storage_key.rsplit(".", 1)[0]
            hls_master_key = f"{base_key}/hls/master.m3u8"
            preview_clip_key = f"{base_key}/preview.mp4"

            def upload():
                for file_path in hls_dir.rglob("*"):
                    if file_path.is_file():
                        relative = file_path.relative_to(hls_dir)
                        with open(file_path, "rb") as fh:
                            default_storage.save(f"{base_key}/hls/{relative.as_posix()}", fh)
                with open(preview_path, "rb") as fh:
                    default_storage.save(preview_clip_key, fh)

            _storage("saving the results", upload)

            video_asset.duration_seconds = duration
            video_asset.hls_master_key = hls_master_key
            video_asset.preview_clip_key = preview_clip_key
            video_asset.status = VideoAsset.Status.READY
            video_asset.processing_error = ""
            video_asset.save()
        except TransientTranscodeError:
            raise
        except Exception as exc:  # noqa: BLE001 — any other failure must flip status to FAILED for the UI to show it
            logger.exception("Transcoding failed for VideoAsset %s", video_asset_id)
            mark_failed(video_asset_id, str(exc))


def mark_failed(video_asset_id: int, reason: str) -> None:
    from apps.videos.models import VideoAsset

    VideoAsset.objects.filter(id=video_asset_id).update(status=VideoAsset.Status.FAILED, processing_error=reason[:2000])
