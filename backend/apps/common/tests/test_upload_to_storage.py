"""End to end, from a real API request down to what is written to S3/MinIO.

The test suite normally stores files in memory, which has no Content-Type
at all; here the production S3 backend runs for real (its signed URLs are
computed locally) and only the final network upload is replaced by a
recorder, so the test sees exactly the headers MinIO would serve the
object with.
"""
import pytest
from rest_framework.test import APIClient

from apps.accounts.models import User
from apps.common.storage import SharedSessionS3Storage
from apps.courses.models import Category, Course, Lesson
from apps.instructors.models import InstructorProfile

from . import file_samples

pytestmark = pytest.mark.django_db


class RecordingBucket:
    name = "test-media"

    def __init__(self):
        self.objects = {}

    def Object(self, key):  # noqa: N802 (boto3's name)
        bucket = self

        class _Object:
            def upload_fileobj(self, content, ExtraArgs=None, Config=None):  # noqa: N803
                bucket.objects[key] = {"body": content.read(), **(ExtraArgs or {})}

        return _Object()


@pytest.fixture
def bucket(settings, monkeypatch):
    settings.STORAGES = {**settings.STORAGES, "default": {"BACKEND": "apps.common.storage.SharedSessionS3Storage"}}
    recorder = RecordingBucket()
    monkeypatch.setattr(SharedSessionS3Storage, "bucket", property(lambda self: recorder))
    return recorder


@pytest.fixture
def people():
    teacher = User.objects.create_user(email="t@example.com", password="x", role=User.Role.ADMIN)
    InstructorProfile.objects.create(user=teacher, is_site_owner=True)
    student = User.objects.create_user(email="s@example.com", password="x")
    return teacher, student


def as_(user):
    client = APIClient()
    client.force_authenticate(user)
    return client


def direct_chat(student):
    return next(c for c in as_(student).get("/api/v1/conversations/").data if c["kind"] == "direct")["id"]


def stored(bucket, folder):
    return [v for k, v in bucket.objects.items() if k.startswith(folder)]


def test_chat_file_is_stored_as_a_download_whatever_the_client_claims(bucket, people):
    _, student = people
    cid = direct_chat(student)
    response = as_(student).post(
        f"/api/v1/conversations/{cid}/messages/",
        {"file": file_samples.upload("تمرین.pdf", file_samples.PDF, "text/html")},
        format="multipart",
    )
    assert response.status_code == 201
    assert response.data["attachment_url"].startswith("http")
    (obj,) = stored(bucket, "chat/")
    assert obj["ContentType"] == "application/octet-stream" and obj["ContentDisposition"] == "attachment"
    assert obj["body"] == file_samples.PDF  # the file itself is untouched


def test_html_disguised_as_pdf_never_reaches_storage(bucket, people):
    _, student = people
    cid = direct_chat(student)
    for claimed in ("text/html", "application/pdf"):
        response = as_(student).post(
            f"/api/v1/conversations/{cid}/messages/",
            {"file": file_samples.upload("notes.pdf", file_samples.HTML, claimed)},
            format="multipart",
        )
        assert response.status_code == 400 and "file" in response.data
    assert bucket.objects == {}


def test_chat_image_keeps_its_real_type_so_it_still_displays(bucket, people):
    _, student = people
    cid = direct_chat(student)
    response = as_(student).post(
        f"/api/v1/conversations/{cid}/messages/",
        {"file": file_samples.upload("shot.png", file_samples.image(), "text/html")},
        format="multipart",
    )
    assert response.status_code == 201 and response.data["attachment_kind"] == "image"
    (obj,) = stored(bucket, "chat/")
    assert obj["ContentType"] == "image/png" and "ContentDisposition" not in obj


def test_avatar_is_stored_as_an_image_not_as_what_the_client_said(bucket, people):
    _, student = people
    response = as_(student).patch(
        "/api/v1/auth/me/", {"avatar": file_samples.upload("me.png", file_samples.image(), "text/html")}, format="multipart"
    )
    assert response.status_code == 200
    (obj,) = stored(bucket, "avatars/")
    assert obj["ContentType"] == "image/png"


def test_lesson_file_is_stored_as_a_download(bucket, people):
    teacher, _ = people
    course = Course.objects.create(
        instructor=teacher.instructor_profile, category=Category.objects.create(name="c", slug="c"), title="Py"
    )
    lesson = Lesson.objects.create(course=course, title="a", order=1)
    response = as_(teacher).post(
        "/api/v1/lesson-files/",
        {"lesson": lesson.id, "file": file_samples.upload("main.py", b"print('hi')\n", "text/html")},
        format="multipart",
    )
    assert response.status_code == 201
    (obj,) = stored(bucket, "lesson_files/")
    assert obj["ContentType"] == "application/octet-stream" and obj["ContentDisposition"] == "attachment"
