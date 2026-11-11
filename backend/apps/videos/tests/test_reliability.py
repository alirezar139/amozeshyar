"""Transcoding survives worker restarts and storage hiccups, and deleted videos leave no files
behind (VID-01, VID-04, OPS-01)."""
from datetime import timedelta
from unittest import mock

import pytest
from celery.exceptions import Retry
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from django.utils import timezone
from rest_framework.test import APIClient

from apps.accounts.models import User
from apps.common.tests import file_samples
from apps.courses.models import Category, Course, Lesson
from apps.instructors.models import InstructorProfile
from apps.videos import tasks
from apps.videos.models import VideoAsset
from apps.videos.services import cleanup, transcoder

pytestmark = pytest.mark.django_db
Status = VideoAsset.Status


@pytest.fixture
def lesson():
    teacher = User.objects.create_user(email="t@example.com", password="x", role=User.Role.ADMIN)
    InstructorProfile.objects.create(user=teacher, is_site_owner=True)
    course = Course.objects.create(
        instructor=teacher.instructor_profile, category=Category.objects.create(name="c", slug="c"), title="Py"
    )
    return Lesson.objects.create(course=course, title="L1", order=1)


def make_video(lesson, status=Status.UPLOADING, key=None, **fields):
    return VideoAsset.objects.create(
        lesson=lesson, original_filename="v.mp4", storage_key=key or f"lessons/{lesson.id}/abc/original_v.mp4", status=status, **fields
    )


def admin(lesson):
    client = APIClient()
    client.force_authenticate(lesson.course.instructor.user)
    return client


# ---------- queues ----------

def test_transcoding_has_its_own_queue_and_everything_else_stays_on_default():
    from config.celery import app

    route = app.amqp.router.route
    assert route({}, "apps.videos.tasks.transcode_video_asset_task")["queue"].name == "video"
    for name in ("apps.payments.tasks.reconcile_pending_payments", "apps.videos.tasks.recover_stuck_videos",
                 "apps.videos.tasks.delete_video_files"):
        assert route({}, name)["queue"].name == "default"


def test_visibility_timeout_outlasts_the_longest_transcode(settings):
    assert settings.CELERY_BROKER_TRANSPORT_OPTIONS["visibility_timeout"] > transcoder.MAX_TRANSCODE_SECONDS
    assert settings.CELERY_TASK_ACKS_LATE and settings.CELERY_TASK_REJECT_ON_WORKER_LOST


# ---------- claiming: a redelivered task never runs twice ----------

def test_a_video_is_claimed_once(lesson):
    video = make_video(lesson)
    assert tasks.claim(video.id) is True
    assert tasks.claim(video.id) is False  # a second delivery of the same task
    video.refresh_from_db()
    assert video.status == Status.PROCESSING and video.attempts == 1 and video.processing_started_at


def test_a_stale_processing_video_can_be_claimed_again(lesson):
    video = make_video(lesson, Status.PROCESSING, attempts=1, processing_started_at=timezone.now() - tasks.STALE_PROCESSING - timedelta(minutes=1))
    assert tasks.claim(video.id) is True
    assert VideoAsset.objects.get(id=video.id).attempts == 2


def test_videos_processing_since_before_the_upgrade_are_recovered_too(lesson):
    # Rows that were PROCESSING when the deploy added processing_started_at have it empty.
    old = make_video(lesson, Status.PROCESSING)
    VideoAsset.objects.filter(id=old.id).update(updated_at=timezone.now() - tasks.STALE_PROCESSING - timedelta(minutes=1))
    other = Lesson.objects.create(course=lesson.course, title="L2", order=2)
    recent = make_video(other, Status.PROCESSING)
    with mock.patch.object(tasks, "enqueue_transcode") as enqueue:
        assert tasks.recover_stuck_videos() == {"requeued": 1, "failed": 0}
    enqueue.assert_called_once_with(old.id)
    assert VideoAsset.objects.get(id=recent.id).status == Status.PROCESSING  # may still be running


@pytest.mark.parametrize("status", [Status.READY, Status.FAILED])
def test_finished_videos_are_not_claimed(lesson, status):
    assert tasks.claim(make_video(lesson, status).id) is False


def test_the_same_task_coming_back_after_its_worker_stopped_takes_the_video_over(lesson):
    # worker-video stops with SIGQUIT (deploy, reboot): the message goes back to the queue while
    # the video still says PROCESSING. That delivery must start over, not be skipped.
    video = make_video(lesson)
    assert tasks.claim(video.id, "task-1") is True
    assert tasks.claim(video.id, "task-2") is False  # anyone else: skipped
    assert tasks.claim(video.id, "task-1") is True  # the same task, redelivered
    video.refresh_from_db()
    assert video.attempts == 2 and video.processing_task_id == "task-1"


def test_a_redelivered_task_runs_the_transcode_again(lesson):
    video = make_video(lesson, Status.PROCESSING, processing_started_at=timezone.now(), processing_task_id="t-1")
    with mock.patch.object(transcoder, "transcode_video_asset") as run:
        tasks.transcode_video_asset_task.apply(args=[video.id], task_id="t-1")
    run.assert_called_once_with(video.id)


def test_the_task_skips_a_video_someone_else_is_processing(lesson):
    video = make_video(lesson, Status.PROCESSING, processing_started_at=timezone.now())
    with mock.patch.object(transcoder, "transcode_video_asset") as run:
        tasks.transcode_video_asset_task.delay(video.id)
    run.assert_not_called()


# ---------- retries ----------

def attempt(video_id, retries):
    """One delivery of the task, as Celery makes it on the n-th retry (eager mode doesn't loop)."""
    return tasks.transcode_video_asset_task.apply(args=[video_id], retries=retries)


def test_storage_hiccups_are_retried_with_backoff_and_then_succeed(lesson):
    video = make_video(lesson)
    calls = []

    def flaky(video_id):
        calls.append(video_id)
        if len(calls) < 3:
            raise transcoder.TransientTranscodeError("reading the original: EndpointConnectionError")
        VideoAsset.objects.filter(id=video_id).update(status=Status.READY)

    with mock.patch.object(transcoder, "transcode_video_asset", side_effect=flaky):
        for retries, wait in ((0, 60), (1, 120)):
            with pytest.raises(Retry) as retry:
                attempt(video.id, retries)
            assert retry.value.when == wait  # 1, 2, 4... minutes
            assert VideoAsset.objects.get(id=video.id).status == Status.PROCESSING  # still ours
        attempt(video.id, 2)

    assert len(calls) == 3
    video.refresh_from_db()
    assert video.status == Status.READY and video.attempts == 1  # one claim, retries don't re-claim


def test_storage_that_stays_down_ends_in_failed_with_a_reason(lesson):
    video = make_video(lesson)
    tasks.claim(video.id)
    with mock.patch.object(transcoder, "transcode_video_asset", side_effect=transcoder.TransientTranscodeError("MinIO down")):
        attempt(video.id, tasks.TRANSIENT_RETRIES)  # the last allowed retry
    video.refresh_from_db()
    assert video.status == Status.FAILED and "MinIO down" in video.processing_error


def test_ffmpeg_rejecting_the_file_fails_at_once_without_retrying(lesson):
    video = make_video(lesson)
    default_storage.save(video.storage_key, ContentFile(b"not a video"))
    with mock.patch.object(transcoder, "probe_duration_seconds", side_effect=transcoder.TranscodeError("Invalid data found")) as probe:
        tasks.transcode_video_asset_task.delay(video.id)
    assert probe.call_count == 1
    video.refresh_from_db()
    assert video.status == Status.FAILED and "Invalid data" in video.processing_error


def test_storage_errors_inside_the_transcoder_are_transient(lesson):
    video = make_video(lesson, key=f"lessons/{lesson.id}/missing/original_v.mp4")  # nothing stored there
    with pytest.raises(transcoder.TransientTranscodeError):
        transcoder.transcode_video_asset(video.id)
    assert VideoAsset.objects.get(id=video.id).status == Status.UPLOADING  # left for the retry


def test_ffmpeg_running_too_long_is_a_clear_failure():
    with mock.patch("subprocess.run", side_effect=transcoder.subprocess.TimeoutExpired("ffmpeg", 5)):
        with pytest.raises(transcoder.TranscodeError, match="VIDEO_TRANSCODE_PRESET"):
            transcoder._run_ffmpeg("-i", "x", timeout=5)


@pytest.mark.parametrize(
    ("duration", "expected"),
    [(0, 1800), (60, 1800), (3600, 3 * 3600), (5 * 3600, 6 * 3600)],
)
def test_time_limit_follows_the_video_length(duration, expected):
    assert transcoder.transcode_timeout(duration) == expected


# ---------- recovering stuck videos ----------

def test_recover_requeues_lost_and_abandoned_videos_and_gives_up_eventually(lesson):
    old = timezone.now() - timedelta(hours=3)
    lost = make_video(lesson)
    VideoAsset.objects.filter(id=lost.id).update(updated_at=old)
    other = Lesson.objects.create(course=lesson.course, title="L2", order=2)
    abandoned = make_video(other, Status.PROCESSING, attempts=1, processing_started_at=timezone.now() - tasks.STALE_PROCESSING - timedelta(minutes=5))
    third = Lesson.objects.create(course=lesson.course, title="L3", order=3)
    hopeless = make_video(third, Status.PROCESSING, attempts=tasks.MAX_ATTEMPTS, processing_started_at=timezone.now() - tasks.STALE_PROCESSING - timedelta(minutes=5))
    fourth = Lesson.objects.create(course=lesson.course, title="L4", order=4)
    running = make_video(fourth, Status.PROCESSING, attempts=1, processing_started_at=timezone.now())

    with mock.patch.object(tasks, "enqueue_transcode") as enqueue:
        result = tasks.recover_stuck_videos()

    assert sorted(c.args[0] for c in enqueue.call_args_list) == sorted([lost.id, abandoned.id])
    assert result == {"requeued": 2, "failed": 1}
    assert VideoAsset.objects.get(id=abandoned.id).status == Status.UPLOADING  # claimable again
    assert VideoAsset.objects.get(id=hopeless.id).status == Status.FAILED
    assert VideoAsset.objects.get(id=running.id).status == Status.PROCESSING


def test_admin_can_retry_a_failed_video_without_uploading_it_again(lesson):
    video = make_video(lesson, Status.FAILED, attempts=3, processing_error="boom")
    student = APIClient()
    student.force_authenticate(User.objects.create_user(email="s@example.com", password="x"))
    assert student.post(f"/api/v1/videos/{video.id}/retry/").status_code == 403

    with mock.patch.object(tasks, "enqueue_transcode") as enqueue:
        response = admin(lesson).post(f"/api/v1/videos/{video.id}/retry/")

    assert response.status_code == 202
    enqueue.assert_called_once_with(video.id)
    video.refresh_from_db()
    assert (video.status, video.attempts, video.processing_error) == (Status.UPLOADING, 0, "")
    assert admin(lesson).post(f"/api/v1/videos/{video.id}/retry/").status_code == 400  # not failed any more


# ---------- files of deleted / replaced videos (VID-01) ----------

def store_video_files(key):
    base = key.rsplit(".", 1)[0]
    for name in (key, f"{base}/hls/master.m3u8", f"{base}/hls/master0.ts", f"{base}/preview.mp4"):
        default_storage.save(name, ContentFile(b"x"))
    return [key, f"{base}/hls/master.m3u8", f"{base}/hls/master0.ts", f"{base}/preview.mp4"]


def test_deleting_a_video_removes_its_files_and_nothing_else(lesson, django_capture_on_commit_callbacks):
    other_lesson = Lesson.objects.create(course=lesson.course, title="L2", order=2)
    gone = make_video(lesson, Status.READY, key=f"lessons/{lesson.id}/aaa/original_v.mp4")
    kept = make_video(other_lesson, Status.READY, key=f"lessons/{other_lesson.id}/bbb/original_v.mp4")
    gone_files, kept_files = store_video_files(gone.storage_key), store_video_files(kept.storage_key)
    handout = default_storage.save("lesson_files/notes.pdf", ContentFile(b"%PDF"))

    with django_capture_on_commit_callbacks(execute=True):
        admin(lesson).delete(f"/api/v1/videos/{gone.id}/")

    assert not any(default_storage.exists(f) for f in gone_files)
    assert all(default_storage.exists(f) for f in kept_files) and default_storage.exists(handout)


def test_files_still_used_by_another_video_are_never_deleted(lesson):
    key = f"lessons/{lesson.id}/same/original_v.mp4"
    files = store_video_files(key)
    make_video(lesson, Status.READY, key=key)  # still referenced

    assert cleanup.delete_unreferenced(cleanup.video_prefixes(key)) == 0
    assert all(default_storage.exists(f) for f in files)
    assert cleanup.delete_unreferenced(["lesson_files/"]) == 0  # never outside lessons/


def test_replacing_a_video_keeps_the_new_one_even_with_the_same_file_name(lesson, django_capture_on_commit_callbacks):
    client = admin(lesson)
    upload = lambda: file_samples.upload("lecture.mp4", open_sample_video(), "video/mp4")  # noqa: E731
    with mock.patch.object(tasks, "enqueue_transcode"), django_capture_on_commit_callbacks(execute=True):
        first = client.post("/api/v1/videos/upload/", {"lesson": lesson.id, "file": upload()}, format="multipart")
    first_key = VideoAsset.objects.get(id=first.data["id"]).storage_key
    with mock.patch.object(tasks, "enqueue_transcode"), django_capture_on_commit_callbacks(execute=True):
        second = client.post("/api/v1/videos/upload/", {"lesson": lesson.id, "file": upload()}, format="multipart")
    assert second.status_code == 201, second.data
    second_key = VideoAsset.objects.get(id=second.data["id"]).storage_key

    assert first_key != second_key  # a folder per upload
    assert not default_storage.exists(first_key) and default_storage.exists(second_key)


def open_sample_video() -> bytes:
    # The smallest file libmagic calls video/mp4: an ISO-BMFF "ftyp" box.
    return b"\x00\x00\x00\x18ftypmp42\x00\x00\x00\x00mp42isom" + b"\x00" * 64


def test_find_orphans_lists_only_old_unreferenced_video_files(lesson, monkeypatch):
    make_video(lesson, Status.READY, key=f"lessons/{lesson.id}/live/original_v.mp4")
    now = timezone.now()
    objects = [
        mock.Mock(key=f"lessons/{lesson.id}/live/original_v.mp4", size=10, last_modified=now - timedelta(days=9)),
        mock.Mock(key=f"lessons/{lesson.id}/live/original_v/hls/master0.ts", size=10, last_modified=now - timedelta(days=9)),
        mock.Mock(key=f"lessons/{lesson.id}/dead/original_v.mp4", size=2_000_000, last_modified=now - timedelta(days=9)),
        mock.Mock(key=f"lessons/{lesson.id}/fresh/original_v.mp4", size=5, last_modified=now - timedelta(hours=1)),
    ]
    bucket = mock.Mock()
    bucket.objects.filter.return_value = objects
    monkeypatch.setattr(type(default_storage._wrapped), "bucket", bucket, raising=False)

    orphans = cleanup.find_orphans(timedelta(hours=24))

    assert [o["key"] for o in orphans] == [f"lessons/{lesson.id}/dead/original_v.mp4"]
    bucket.objects.filter.assert_called_with(Prefix="lessons/")


def test_production_logging_config_is_valid():
    """In a separate process: importing config.settings.prod mutates the shared settings
    (MIDDLEWARE, REST_FRAMEWORK...) and would break every test after this one."""
    import os
    import subprocess
    import sys
    from pathlib import Path

    env = {**os.environ, "DJANGO_SECRET_KEY": "x" * 60, "DJANGO_ALLOWED_HOSTS": "site.test",
           "CORS_ALLOWED_ORIGINS": "https://site.test", "DJANGO_SETTINGS_MODULE": "config.settings.prod"}
    code = (
        "import logging.config, config.settings.prod as p; logging.config.dictConfig(p.LOGGING); "
        "assert p.LOGGING['root']['handlers'] == ['stdout']; print('ok')"
    )
    backend = Path(__file__).resolve().parents[3]
    result = subprocess.run([sys.executable, "-c", code], cwd=backend, env=env, capture_output=True, text=True, timeout=60)
    assert result.returncode == 0 and result.stdout.strip() == "ok", result.stderr[-2000:]


# ---------- memory: originals never pass through RAM ----------

def test_reading_stored_files_spills_to_disk_above_8mb(settings):
    # django-storages' default (0) keeps the whole object in memory: a 2 GB original OOM-killed the worker.
    assert 0 < settings.AWS_S3_MAX_MEMORY_SIZE <= 8 * 1024 * 1024


def test_the_original_is_streamed_to_disk_on_s3(tmp_path, monkeypatch):
    bucket = mock.Mock()
    monkeypatch.setattr(transcoder.default_storage, "_wrapped", mock.Mock(bucket=bucket, _normalize_name=lambda k: k))
    transcoder.download_original("lessons/1/abc/original_v.mp4", tmp_path / "original")
    key, target = bucket.download_file.call_args.args
    assert key == "lessons/1/abc/original_v.mp4" and target == str(tmp_path / "original")
    assert bucket.download_file.call_args.kwargs["Config"].max_request_concurrency == 2
