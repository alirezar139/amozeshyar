"""Runs the real ffmpeg (skipped where it isn't installed; the production image has it)."""
import json
import shutil
import subprocess

import pytest

from apps.videos.services import transcoder

pytestmark = pytest.mark.skipif(not shutil.which("ffmpeg"), reason="ffmpeg not installed")


def make_source(path, width, height, seconds=3, pix_fmt="yuv420p"):
    subprocess.run(
        [
            "ffmpeg", "-y", "-v", "error",
            "-f", "lavfi", "-i", f"testsrc2=size={width}x{height}:rate=25:duration={seconds}",
            "-f", "lavfi", "-i", f"sine=frequency=440:duration={seconds}",
            "-c:v", "libx264", "-pix_fmt", pix_fmt, "-c:a", "aac", "-shortest", str(path),
        ],
        check=True,
    )
    return path


def probe(path):
    out = subprocess.run(
        ["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries",
         "stream=width,height,pix_fmt:format=duration", "-of", "json", str(path)],
        capture_output=True, text=True, check=True,
    ).stdout
    data = json.loads(out)
    stream = data["streams"][0]
    return stream["width"], stream["height"], stream["pix_fmt"], float(data["format"]["duration"])


def test_full_hd_comes_out_at_720p_hls(tmp_path):
    source = make_source(tmp_path / "in.mp4", 1920, 1080)
    playlist = tmp_path / "hls" / "master.m3u8"
    playlist.parent.mkdir()

    transcoder.encode_hls(source, playlist)

    assert list(playlist.parent.glob("*.ts"))
    width, height, pix_fmt, _ = probe(playlist)
    assert (width, height, pix_fmt) == (1280, 720, "yuv420p")


def test_small_odd_sized_video_is_not_upscaled(tmp_path):
    source = make_source(tmp_path / "in.mp4", 640, 482)
    preview = tmp_path / "preview.mp4"

    transcoder.encode_preview(source, preview, 2)

    width, height, _, duration = probe(preview)
    assert height == 482 and width % 2 == 0
    assert duration == pytest.approx(2, abs=0.2)


def test_ten_bit_source_becomes_browser_playable(tmp_path):
    source = make_source(tmp_path / "in.mp4", 640, 360, pix_fmt="yuv422p10le")
    preview = tmp_path / "preview.mp4"

    transcoder.encode_preview(source, preview, 1)

    assert probe(preview)[2] == "yuv420p"
