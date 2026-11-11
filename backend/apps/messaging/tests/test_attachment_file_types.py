"""Chat attachments are checked by their bytes, not their name or claimed type (SEC-01)."""
import pytest
from rest_framework.test import APIClient

from apps.accounts.models import User
from apps.common.tests import file_samples
from apps.instructors.models import InstructorProfile
from apps.messaging.models import Message

pytestmark = pytest.mark.django_db


@pytest.fixture
def people():
    teacher = User.objects.create_user(email="t@example.com", password="x", role=User.Role.ADMIN)
    InstructorProfile.objects.create(user=teacher, is_site_owner=True)
    return teacher, User.objects.create_user(email="s@example.com", password="x")


def as_(user):
    client = APIClient()
    client.force_authenticate(user)
    return client


def send(student, upload, **extra):
    cid = next(c for c in as_(student).get("/api/v1/conversations/").data if c["kind"] == "direct")["id"]
    return as_(student).post(f"/api/v1/conversations/{cid}/messages/", {"file": upload, **extra}, format="multipart")


@pytest.mark.parametrize(
    ("name", "content", "claimed", "extra"),
    [
        ("تمرین.pdf", file_samples.HTML, "application/pdf", {}),  # HTML disguised as PDF, faked MIME type
        ("notes.txt", file_samples.HTML, "text/plain", {}),
        ("shot.png", file_samples.HTML, "image/png", {}),
        ("shot.png", file_samples.SVG, "image/png", {}),
        ("shot.gif", file_samples.PDF, "image/gif", {}),
        ("voice.webm", file_samples.HTML, "audio/webm", {"voice": "true"}),
        ("archive.zip", file_samples.PDF, "application/zip", {}),
    ],
)
def test_content_must_match_the_kind_of_attachment(people, name, content, claimed, extra):
    _, student = people
    response = send(student, file_samples.upload(name, content, claimed), **extra)
    assert response.status_code == 400 and "file" in response.data
    assert not Message.objects.filter(sender=student).exists()


@pytest.mark.parametrize(
    ("name", "content", "kind", "extra"),
    [
        ("تمرین.pdf", file_samples.PDF, "file", {}),
        ("shot.jpg", file_samples.image("JPEG"), "image", {}),
        ("voice.webm", file_samples.WEBM, "voice", {"voice": "true"}),
        ("voice.mp3", file_samples.MP3, "voice", {"voice": "true"}),
        ("main.py", b"print('hello')\n", "file", {}),
    ],
)
def test_genuine_attachments_still_go_through(people, name, content, kind, extra):
    _, student = people
    response = send(student, file_samples.upload(name, content, "application/octet-stream"), **extra)
    assert response.status_code == 201 and response.data["attachment_kind"] == kind


def test_group_avatar_must_be_a_real_image(people):
    teacher, _ = people
    bad = as_(teacher).post(
        "/api/v1/conversations/groups/",
        {"title": "گروه", "avatar": file_samples.upload("g.png", file_samples.HTML, "image/png")},
        format="multipart",
    )
    assert bad.status_code == 400
    good = as_(teacher).post(
        "/api/v1/conversations/groups/",
        {"title": "گروه", "avatar": file_samples.upload("g.png", file_samples.image(), "image/png")},
        format="multipart",
    )
    assert good.status_code == 201
