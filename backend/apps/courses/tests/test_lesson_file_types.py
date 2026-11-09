"""Lesson files are checked by their bytes, like every other upload (SEC-01)."""
import pytest
from rest_framework.test import APIClient

from apps.accounts.models import User
from apps.common.tests import file_samples
from apps.courses.models import Category, Course, Lesson, LessonFile
from apps.instructors.models import InstructorProfile

pytestmark = pytest.mark.django_db


@pytest.fixture
def lesson_and_admin():
    admin = User.objects.create_user(email="t@example.com", password="x", role=User.Role.ADMIN)
    InstructorProfile.objects.create(user=admin, is_site_owner=True)
    course = Course.objects.create(
        instructor=admin.instructor_profile, category=Category.objects.create(name="c", slug="c"), title="Py"
    )
    client = APIClient()
    client.force_authenticate(admin)
    return Lesson.objects.create(course=course, title="a", order=1), client


def upload(client, lesson, name, content, claimed="application/octet-stream"):
    return client.post(
        "/api/v1/lesson-files/", {"lesson": lesson.id, "file": file_samples.upload(name, content, claimed)}, format="multipart"
    )


@pytest.mark.parametrize(
    ("name", "content"),
    [("جزوه.pdf", file_samples.HTML), ("notes.txt", file_samples.HTML), ("logo.png", file_samples.SVG), ("a.docx", file_samples.PDF)],
)
def test_disguised_files_are_refused(lesson_and_admin, name, content):
    lesson, client = lesson_and_admin
    assert upload(client, lesson, name, content, "application/pdf").status_code == 400
    assert not LessonFile.objects.exists()


def test_genuine_files_are_accepted(lesson_and_admin):
    lesson, client = lesson_and_admin
    assert upload(client, lesson, "جزوه.pdf", file_samples.PDF).status_code == 201
    assert upload(client, lesson, "main.py", b"def f():\n    return 1\n").status_code == 201
    assert upload(client, lesson, "audio.mp3", file_samples.MP3).status_code == 201
