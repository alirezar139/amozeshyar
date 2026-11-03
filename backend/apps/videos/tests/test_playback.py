from urllib.parse import parse_qs, urlparse

import pytest
from django.core import signing
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from rest_framework.test import APIClient

from apps.accounts.models import User
from apps.courses.models import Category, Course, Lesson
from apps.enrollments.models import Enrollment
from apps.instructors.models import InstructorProfile
from apps.videos.models import VideoAsset
from apps.videos.services import signing as video_signing

pytestmark = pytest.mark.django_db

PLAYLIST = """#EXTM3U
#EXT-X-VERSION:3
#EXT-X-TARGETDURATION:10
#EXTINF:10.0,
master0.ts
#EXTINF:4.5,
master1.ts
#EXT-X-ENDLIST
"""


@pytest.fixture
def video():
    teacher = User.objects.create_user(email="t@example.com", password="x", role=User.Role.ADMIN)
    InstructorProfile.objects.create(user=teacher, is_site_owner=True)
    category = Category.objects.create(name="c", slug="c")
    course = Course.objects.create(
        instructor=teacher.instructor_profile, category=category, title="Python", status=Course.Status.PUBLISHED
    )
    lesson = Lesson.objects.create(course=course, title="L1", order=1)
    key = default_storage.save("lessons/1/original_v/hls/master.m3u8", ContentFile(PLAYLIST.encode()))
    return VideoAsset.objects.create(
        lesson=lesson,
        original_filename="v.mp4",
        storage_key="lessons/1/original_v.mp4",
        hls_master_key=key,
        duration_seconds=14,
        status=VideoAsset.Status.READY,
    )


@pytest.fixture
def student(video):
    user = User.objects.create_user(email="s@example.com", password="x")
    Enrollment.objects.create(student=user, course=video.lesson.course)
    return user


def manifest(user, video):
    client = APIClient()
    if user:
        client.force_authenticate(user)
    return client.get(f"/api/v1/videos/{video.id}/manifest/")


def test_enrolled_student_gets_a_playlist_link_with_every_segment_signed(student, video):
    url = manifest(student, video).data["url"]

    assert urlparse(url).path == f"/api/v1/videos/{video.id}/playlist.m3u8"  # path ends in .m3u8 for players
    response = APIClient().get(url)  # the player fetches it without the student's auth

    assert response.status_code == 200
    assert response["Content-Type"] == "application/vnd.apple.mpegurl"
    assert "no-store" in response["Cache-Control"]
    lines = response.content.decode().splitlines()
    segments = [line for line in lines if line and not line.startswith("#")]
    assert len(segments) == 2
    for name, segment in zip(("master0.ts", "master1.ts"), segments, strict=True):
        parsed = urlparse(segment)
        assert parsed.path.endswith(f"/lessons/1/original_v/hls/{name}")
        query = parse_qs(parsed.query)
        assert "Signature" in query or "X-Amz-Signature" in query
    assert "#EXT-X-ENDLIST" in lines  # tags pass through untouched


def test_non_enrolled_student_gets_no_link(video):
    stranger = User.objects.create_user(email="x@example.com", password="x")

    assert manifest(stranger, video).status_code == 403
    assert manifest(None, video).status_code == 403


def test_playlist_needs_a_valid_token_for_that_video(video):
    other = VideoAsset.objects.create(
        lesson=Lesson.objects.create(course=video.lesson.course, title="L2", order=2),
        original_filename="w.mp4",
        storage_key="k",
        hls_master_key=video.hls_master_key,
        status=VideoAsset.Status.READY,
    )
    url = f"/api/v1/videos/{video.id}/playlist.m3u8"

    assert APIClient().get(url).status_code == 403
    assert APIClient().get(url, {"t": "forged"}).status_code == 403
    assert APIClient().get(url, {"t": video_signing.make_playlist_token(other.id)}).status_code == 403
    assert APIClient().get(url, {"t": video_signing.make_playlist_token(video.id)}).status_code == 200


def test_playlist_token_expires(video, monkeypatch):
    token = video_signing.make_playlist_token(video.id)
    real_time = signing.time.time
    monkeypatch.setattr(signing.time, "time", lambda: real_time() + video_signing.PLAYLIST_TOKEN_MAX_AGE + 1)

    assert video_signing.playlist_token_is_valid(token, video.id) is False


@pytest.mark.parametrize(
    ("duration", "hours"), [(None, 2), (60, 2), (3 * 3600, 6), (10 * 3600, 12)]
)
def test_segment_links_outlast_the_viewing(duration, hours):
    assert video_signing.segment_url_lifetime(duration) == hours * 3600
