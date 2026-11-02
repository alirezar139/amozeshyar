import pytest
from rest_framework.test import APIClient

from apps.accounts.models import User
from apps.courses.models import Category, Course, Lesson
from apps.enrollments.models import Enrollment, LessonProgress, WishlistItem
from apps.instructors.models import InstructorProfile

pytestmark = pytest.mark.django_db


@pytest.fixture
def course():
    teacher = User.objects.create_user(email="t@example.com", password="x", role=User.Role.ADMIN)
    InstructorProfile.objects.create(user=teacher, is_site_owner=True)
    category = Category.objects.create(name="c", slug="c")
    return Course.objects.create(
        instructor=teacher.instructor_profile, category=category, title="Python", status=Course.Status.PUBLISHED
    )


@pytest.fixture
def lessons(course):
    return [Lesson.objects.create(course=course, title=f"L{i}", order=i) for i in (1, 2, 3)]


@pytest.fixture
def student():
    return User.objects.create_user(email="s@example.com", password="x")


@pytest.fixture
def client(student):
    client = APIClient()
    client.force_authenticate(student)
    return client


def test_my_enrollments_hide_removed_and_other_students(client, student, course):
    other_course = Course.objects.create(
        instructor=course.instructor, category=course.category, title="Django", status=Course.Status.PUBLISHED
    )
    Enrollment.objects.create(student=student, course=course)
    Enrollment.objects.create(student=student, course=other_course, is_active=False)
    Enrollment.objects.create(student=User.objects.create_user(email="o@example.com", password="x"), course=course)

    response = client.get("/api/v1/enrollments/")

    results = response.data["results"] if isinstance(response.data, dict) else response.data
    assert [e["course"]["id"] if isinstance(e["course"], dict) else e["course"] for e in results] == [course.id]


def test_summary_counts_lessons_of_active_courses(client, student, course, lessons):
    Enrollment.objects.create(student=student, course=course)
    LessonProgress.objects.create(student=student, lesson=lessons[0], position_seconds=600, completed=True)

    data = client.get("/api/v1/enrollments/summary/").data

    assert data["courses"] == 1
    assert data["total_lessons"] == 3
    assert data["completed_lessons"] == 1
    assert data["watched_minutes"] == 10


def test_continue_prefers_the_half_watched_lesson(client, student, course, lessons):
    Enrollment.objects.create(student=student, course=course)
    LessonProgress.objects.create(student=student, lesson=lessons[1], position_seconds=95)

    data = client.get("/api/v1/enrollments/continue/").data

    assert data["lesson_id"] == lessons[1].id
    assert data["position_seconds"] == 95


def test_continue_falls_back_to_the_first_lesson(client, student, course, lessons):
    Enrollment.objects.create(student=student, course=course)

    data = client.get("/api/v1/enrollments/continue/").data

    assert data["lesson_id"] == lessons[0].id
    assert data["position_seconds"] == 0


def test_continue_is_empty_without_enrollments(client):
    assert client.get("/api/v1/enrollments/continue/").data is None


def test_progress_rewatching_does_not_unfinish_a_lesson(client, student, lessons):
    lesson = lessons[0]
    client.post("/api/v1/progress/", {"lesson_id": lesson.id, "completed": True}, format="json")

    response = client.post("/api/v1/progress/", {"lesson_id": lesson.id, "position_seconds": 5}, format="json")

    assert response.data["completed"] is True
    assert response.data["position_seconds"] == 5


def test_progress_can_be_unmarked_explicitly(client, student, lessons):
    lesson = lessons[0]
    client.post("/api/v1/progress/", {"lesson_id": lesson.id, "completed": True}, format="json")

    response = client.post("/api/v1/progress/", {"lesson_id": lesson.id, "completed": False}, format="json")

    assert response.data["completed"] is False


def test_enrollment_endpoints_need_login(course):
    assert APIClient().get("/api/v1/enrollments/").status_code == 401
    assert APIClient().post("/api/v1/progress/", {"lesson_id": 1}, format="json").status_code == 401


def test_wishlist_add_twice_is_a_validation_error(client, student, course):
    first = client.post("/api/v1/wishlist/", {"course_id": course.id}, format="json")
    second = client.post("/api/v1/wishlist/", {"course_id": course.id}, format="json")

    assert first.status_code == 201
    assert second.status_code == 400
    assert WishlistItem.objects.filter(student=student).count() == 1


def test_wishlist_rejects_unknown_or_draft_courses(client, course):
    course.status = Course.Status.DRAFT
    course.save(update_fields=["status"])

    assert client.post("/api/v1/wishlist/", {"course_id": course.id}, format="json").status_code == 400
    assert client.post("/api/v1/wishlist/", {"course_id": 99999}, format="json").status_code == 400
