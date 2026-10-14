"""ffmpeg-based transcoding: produces the full HLS rendition plus a
physically-truncated preview clip.

Run as a Celery task (see tasks.py) so uploads return immediately and
processing happens off the request/response cycle.
"""
import logging
import os
import shutil
import subprocess
import tempfile
from pathlib import Path

from django.core.files.storage import default_storage

logger = logging.getLogger("apps.videos")


class TranscodeError(RuntimeError):
    pass


# Tuned for recorded lessons (mostly a talking head, slides or a screen):
# CRF 26 looks the same as the default 23 for that kind of footage at a
# noticeably smaller size, and the maxrate cap keeps busy scenes from
# spiking the bitrate for viewers on mobile connections. yuv420p because
# phones and some cameras record 10-bit or 4:2:2, which browsers can't play.
VIDEO_ARGS = (
    "-c:v", "libx264", "-preset", "medium", "-crf", "26",
    "-maxrate", "2500k", "-bufsize", "5000k", "-pix_fmt", "yuv420p",
)
AUDIO_ARGS = ("-c:a", "aac", "-b:a", "96k")
# At most 720p and never upscaled (that only makes the file bigger); both sides even, as x264 requires.
SCALE_FILTER = "scale=-2:'min(720,trunc(ih/2)*2)'"

# Lowest CPU priority: on a small server the website must stay responsive
# while a video is being encoded. Linux only: on Windows dev machines the
# `nice` that Git Bash provides mangles the filter's quotes on the way to ffmpeg.
NICE = ("nice", "-n", "19") if os.name == "posix" and shutil.which("nice") else ()


def _run_ffmpeg(*args: str) -> None:
    result = subprocess.run(
        [*NICE, "ffmpeg", "-y", *args],
        capture_output=True,
        text=True,
        timeout=60 * 60,
    )
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


def encode_hls(source: Path, playlist: Path) -> None:
    """The full lesson as a single-rendition HLS stream, in 6-second segments."""
    _run_ffmpeg(
        "-i", str(source),
        "-vf", SCALE_FILTER, *VIDEO_ARGS, *AUDIO_ARGS,
        "-hls_time", "6", "-hls_playlist_type", "vod",
        str(playlist),
    )


def encode_preview(source: Path, target: Path, seconds: int) -> None:
    """The free preview: a separate file cut to `seconds`, with its index up front so playback starts at once."""
    _run_ffmpeg(
        "-i", str(source),
        "-t", str(seconds),
        "-vf", SCALE_FILTER, *VIDEO_ARGS, *AUDIO_ARGS,
        "-movflags", "+faststart",
        str(target),
    )


def transcode_video_asset(video_asset_id: int) -> None:
    """Download the original upload, produce HLS + preview clip, upload results, update the model.

    Imported lazily inside the function body (not at module import time) to
    keep this module importable without Django apps being loaded yet, which
    matters for the Celery worker's autodiscovery import order.
    """
    from apps.videos.models import VideoAsset

    video_asset = VideoAsset.objects.select_related("lesson__course").get(id=video_asset_id)
    video_asset.status = VideoAsset.Status.PROCESSING
    video_asset.save(update_fields=["status"])

    with tempfile.TemporaryDirectory() as tmp:
        tmp_dir = Path(tmp)
        original_path = tmp_dir / "original"
        try:
            with default_storage.open(video_asset.storage_key, "rb") as src, open(original_path, "wb") as dst:
                for chunk in src.chunks():
                    dst.write(chunk)

            duration = probe_duration_seconds(original_path)
            preview_seconds = video_asset.effective_preview_seconds

            # Full HLS rendition (single 720p rendition for MVP; multi-bitrate is a later optimization).
            hls_dir = tmp_dir / "hls"
            hls_dir.mkdir()
            hls_playlist = hls_dir / "master.m3u8"
            encode_hls(original_path, hls_playlist)

            # Preview clip: a SEPARATE, physically-truncated file (not a
            # time-limited view into the full file) — this is what makes the
            # gate unbypassable by URL manipulation.
            preview_path = tmp_dir / "preview.mp4"
            encode_preview(original_path, preview_path, min(preview_seconds, duration))

            base_key = video_asset.storage_key.rsplit(".", 1)[0]
            hls_master_key = f"{base_key}/hls/master.m3u8"
            preview_clip_key = f"{base_key}/preview.mp4"

            for file_path in hls_dir.rglob("*"):
                if file_path.is_file():
                    relative = file_path.relative_to(hls_dir)
                    with open(file_path, "rb") as fh:
                        default_storage.save(f"{base_key}/hls/{relative.as_posix()}", fh)

            with open(preview_path, "rb") as fh:
                default_storage.save(preview_clip_key, fh)

            video_asset.duration_seconds = duration
            video_asset.hls_master_key = hls_master_key
            video_asset.preview_clip_key = preview_clip_key
            video_asset.status = VideoAsset.Status.READY
            video_asset.save()
        except Exception as exc:  # noqa: BLE001 — any failure must flip status to FAILED for the UI to show it
            logger.exception("Transcoding failed for VideoAsset %s", video_asset_id)
            video_asset.status = VideoAsset.Status.FAILED
            video_asset.processing_error = str(exc)[:2000]
            video_asset.save(update_fields=["status", "processing_error"])
