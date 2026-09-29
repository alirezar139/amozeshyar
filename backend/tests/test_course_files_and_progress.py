"""Lesson management, course files (upload + gated download) and the
student-side progress/summary endpoints."""
from datetime import timedelta

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from django.utils import timezone
from rest_framework.test import APIClient

from apps.accounts.models import User
from apps.courses.models import Category, ClassSession, Course, Lesson, LessonFile
from apps.enrollments.models import Enrollment
from apps.instructors.models import InstructorProfile

pytestmark = pytest.mark.django_db


@pytest.fixture
def owner():
    user = User.objects.create_user(email="t@example.com", password="x", role=User.Role.ADMIN)
    return InstructorProfile.objects.create(user=user, is_site_owner=True)


@pytest.fixture
def course(owner):
    category = Category.objects.create(name="c", slug="c")
    return Course.objects.create(instructor=owner, category=category, title="Python", status=Course.Status.PUBLISHED)


def client_for(user):
    client = APIClient()
    client.force_authenticate(user)
    return client


def upload(client, lesson, name="جزوه.pdf", content=b"%PDF-1.4 data"):
    return client.post(
        "/api/v1/lesson-files/",
        {"lesson": lesson.id, "file": SimpleUploadedFile(name, content)},
        format="multipart",
    )


def test_lessons_scoped_by_course_and_not_paginated(owner, course):
    for i in range(25):
        Lesson.objects.create(course=course, title=f"L{i}", order=i + 1)
    data = client_for(owner.user).get(f"/api/v1/lessons/?course={course.id}").data
    assert isinstance(data, list) and len(data) == 25


def test_new_lesson_takes_next_free_order_after_a_delete(owner, course):
    client = client_for(owner.user)
    ids = [client.post("/api/v1/lessons/", {"course": course.id, "title": t}).data["id"] for t in "abc"]
    client.delete(f"/api/v1/lessons/{ids[1]}/")
    response = client.post("/api/v1/lessons/", {"course": course.id, "title": "d"})
    assert response.status_code == 201
    assert response.data["order"] == 4


def test_move_lesson_swaps_order(owner, course):
    a = Lesson.objects.create(course=course, title="a", order=1)
    b = Lesson.objects.create(course=course, title="b", order=2)
    client_for(owner.user).post(f"/api/v1/lessons/{b.id}/move/", {"direction": "up"})
    a.refresh_from_db()
    b.refresh_from_db()
    assert (a.order, b.order) == (2, 1)


def test_upload_file_and_list_without_url(owner, course):
    lesson = Lesson.objects.create(course=course, title="a", order=1)
    response = upload(client_for(owner.user), lesson)
    assert response.status_code == 201, response.data
    assert response.data["original_name"] == "جزوه.pdf"
    assert response.data["title"] == "جزوه"
    assert response.data["extension"] == "pdf"

    public = APIClient().get(f"/api/v1/courses/{course.slug}/").data
    files = public["lessons"][0]["files"]
    assert files[0]["original_name"] == "جزوه.pdf"
    assert "file" not in files[0] and "url" not in files[0]


def test_rejects_dangerous_file_types(owner, course):
    lesson = Lesson.objects.create(course=course, title="a", order=1)
    for name in ("page.html", "icon.svg", "setup.exe", "noextension"):
        assert upload(client_for(owner.user), lesson, name=name).status_code == 400, name


def test_download_requires_enrollment(owner, course):
    lesson = Lesson.objects.create(course=course, title="a", order=1)
    file_id = upload(client_for(owner.user), lesson).data["id"]
    student = User.objects.create_user(email="s@example.com", password="x")

    assert client_for(student).get(f"/api/v1/lesson-files/{file_id}/download/").status_code == 403
    assert APIClient().get(f"/api/v1/lesson-files/{file_id}/download/").status_code == 401

    Enrollment.objects.create(student=student, course=course)
    response = client_for(student).get(f"/api/v1/lesson-files/{file_id}/download/")
    assert response.status_code == 200 and response.data["url"]


def test_free_preview_files_download_without_enrollment(owner, course):
    lesson = Lesson.objects.create(course=course, title="a", order=1, is_free_preview=True)
    file_id = upload(client_for(owner.user), lesson).data["id"]
    student = User.objects.create_user(email="s@example.com", password="x")
    assert client_for(student).get(f"/api/v1/lesson-files/{file_id}/download/").status_code == 200


def test_students_cannot_upload_or_delete_files(owner, course):
    lesson = Lesson.objects.create(course=course, title="a", order=1)
    file_id = upload(client_for(owner.user), lesson).data["id"]
    student = User.objects.create_user(email="s@example.com", password="x")
    assert upload(client_for(student), lesson).status_code == 403
    assert client_for(student).delete(f"/api/v1/lesson-files/{file_id}/").status_code == 403
    assert LessonFile.objects.filter(id=file_id).exists()


def test_manual_completion_and_progress_summary(owner, course):
    lessons = [Lesson.objects.create(course=course, title=f"L{i}", order=i + 1) for i in range(4)]
    upload(client_for(owner.user), lessons[0])
    ClassSession.objects.create(course=course, title="Live", starts_at=timezone.now() + timedelta(days=1))
    student = User.objects.create_user(email="s@example.com", password="x")
    Enrollment.objects.create(student=student, course=course)
    client = client_for(student)

    assert client.post("/api/v1/progress/", {"lesson_id": lessons[0].id, "completed": True}).data["completed"]
    client.post("/api/v1/progress/", {"lesson_id": lessons[1].id, "completed": True})
    client.post("/api/v1/progress/", {"lesson_id": lessons[1].id, "completed": False})

    enrollment = client.get("/api/v1/enrollments/").data["results"][0]
    assert enrollment["progress"] == {"total_lessons": 4, "completed_lessons": 1, "percent": 25}

    summary = client.get("/api/v1/enrollments/summary/").data
    assert summary["courses"] == 1
    assert summary["completed_lessons"] == 1 and summary["total_lessons"] == 4
    assert summary["next_session"]["title"] == "Live"
    assert summary["recent_files"][0]["course_slug"] == course.slug


def test_upload_accepts_recently_expired_token_but_other_endpoints_do_not(owner, course):
    from datetime import timedelta as td

    from rest_framework_simplejwt.tokens import AccessToken

    lesson = Lesson.objects.create(course=course, title="a", order=1)
    token = AccessToken.for_user(owner.user)
    token.set_exp(lifetime=-td(minutes=30))  # expired half an hour ago
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")

    response = client.post(
        "/api/v1/lesson-files/",
        {"lesson": lesson.id, "file": SimpleUploadedFile("a.pdf", b"%PDF")},
        format="multipart",
    )
    assert response.status_code == 201
    assert client.get("/api/v1/lesson-files/").status_code == 401

    token.set_exp(lifetime=-td(hours=7))
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")
    response = client.post(
        "/api/v1/lesson-files/",
        {"lesson": lesson.id, "file": SimpleUploadedFile("a.pdf", b"%PDF")},
        format="multipart",
    )
    assert response.status_code == 401
