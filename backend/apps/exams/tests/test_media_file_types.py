"""Exam media is checked by its bytes: a student's answer file goes straight to the teacher (SEC-01)."""
import pytest
from rest_framework.test import APIClient

from apps.accounts.models import User
from apps.common.tests import file_samples
from apps.courses.models import Category, Course
from apps.enrollments.models import Enrollment
from apps.exams.models import AnswerFile, QuestionMedia
from apps.instructors.models import InstructorProfile

pytestmark = pytest.mark.django_db


def as_(user):
    client = APIClient()
    client.force_authenticate(user)
    return client


@pytest.fixture
def setup():
    teacher = User.objects.create_user(email="t@example.com", password="x", role=User.Role.ADMIN)
    InstructorProfile.objects.create(user=teacher, is_site_owner=True)
    course = Course.objects.create(
        instructor=teacher.instructor_profile, category=Category.objects.create(name="c", slug="c"), title="Python"
    )
    student = User.objects.create_user(email="s@example.com", password="x")
    Enrollment.objects.create(student=student, course=course)
    client = as_(teacher)
    exam = client.post("/api/v1/exams/manage/", {"course": course.id, "title": "شفاهی"}, format="json").data
    essay = client.post("/api/v1/exam-questions/", {
        "exam": exam["id"], "kind": "essay", "text": "توضیح بده", "points": "5", "answer_key": "…",
    }, format="json").data
    client.patch(f"/api/v1/exams/manage/{exam['id']}/", {"status": "published"}, format="json")
    attempt_id = as_(student).post(f"/api/v1/exams/{exam['id']}/start/").data["id"]
    return {"teacher": teacher, "student": student, "essay": essay, "attempt_id": attempt_id}


def send_answer_file(setup, upload):
    return as_(setup["student"]).post(
        f"/api/v1/exam-attempts/{setup['attempt_id']}/files/",
        {"question": setup["essay"]["id"], "file": upload},
        format="multipart",
    )


@pytest.mark.parametrize(
    ("name", "content", "claimed"),
    [
        ("answer.png", file_samples.HTML, "image/png"),  # HTML with a faked MIME type
        ("answer.jpg", file_samples.SVG, "image/jpeg"),
        ("voice.webm", file_samples.HTML, "audio/webm"),
        ("voice.mp3", file_samples.image(), "audio/mpeg"),
    ],
)
def test_student_answer_file_must_really_be_an_image_or_audio(setup, name, content, claimed):
    response = send_answer_file(setup, file_samples.upload(name, content, claimed))
    assert response.status_code == 400 and "file" in response.data
    assert not AnswerFile.objects.exists()


def test_genuine_answer_files_are_still_accepted(setup):
    assert send_answer_file(setup, file_samples.upload("answer.png", file_samples.image(), "image/png")).status_code == 201
    voice = send_answer_file(setup, file_samples.upload("voice.webm", file_samples.WEBM, "audio/webm"))
    assert voice.status_code == 201 and voice.data["kind"] == "audio"


def test_teacher_question_media_is_checked_too(setup):
    url = "/api/v1/exam-question-media/"
    bad = as_(setup["teacher"]).post(url, {
        "question": setup["essay"]["id"], "role": "prompt", "file": file_samples.upload("q.mp3", file_samples.HTML, "audio/mpeg"),
    }, format="multipart")
    assert bad.status_code == 400 and not QuestionMedia.objects.exists()
    good = as_(setup["teacher"]).post(url, {
        "question": setup["essay"]["id"], "role": "prompt", "file": file_samples.upload("q.mp3", file_samples.MP3, "audio/mpeg"),
    }, format="multipart")
    assert good.status_code == 201
