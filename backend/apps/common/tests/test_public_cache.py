import pytest
from django.core.cache import cache
from django.db import connection
from django.test.utils import CaptureQueriesContext
from rest_framework.test import APIClient

from apps.accounts.models import User
from apps.courses.models import Category, Course
from apps.enrollments.models import Enrollment
from apps.instructors.models import InstructorProfile

pytestmark = pytest.mark.django_db


@pytest.fixture(autouse=True)
def fresh_cache():
    cache.clear()
    yield
    cache.clear()


@pytest.fixture
def course():
    teacher = User.objects.create_user(email="t@example.com", password="x", role=User.Role.ADMIN, first_name="علی")
    InstructorProfile.objects.create(user=teacher, is_site_owner=True)
    category = Category.objects.create(name="c", slug="c")
    return Course.objects.create(instructor=teacher.instructor_profile, category=category, title="Python", status=Course.Status.PUBLISHED)


def queries_for(client, url):
    with CaptureQueriesContext(connection) as queries:
        response = client.get(url)
    assert response.status_code == 200
    return len(queries), response.data


@pytest.mark.parametrize("url", ["/api/v1/site/", "/api/v1/courses/", "/api/v1/categories/", "/api/v1/courses/python/"])
def test_repeat_anonymous_visits_are_served_from_cache(course, url):
    course.slug = "python"
    course.save()
    client = APIClient()

    first, _ = queries_for(client, url)
    second, _ = queries_for(client, url)

    assert first > 0
    assert second == 0


def test_an_edit_shows_up_immediately(course):
    client = APIClient()
    assert client.get("/api/v1/courses/").data["results"][0]["title"] == "Python"

    course.title = "Python پیشرفته"
    course.save()

    assert client.get("/api/v1/courses/").data["results"][0]["title"] == "Python پیشرفته"


def test_owner_profile_change_shows_up_immediately(course):
    client = APIClient()
    assert client.get("/api/v1/site/").data["display_name"] == "علی"

    owner = course.instructor.user
    owner.first_name = "رضا"
    owner.save()

    assert client.get("/api/v1/site/").data["display_name"] == "رضا"


def test_signed_in_students_get_their_own_answer(course):
    student = User.objects.create_user(email="s@example.com", password="x")
    Enrollment.objects.create(student=student, course=course)
    anonymous = APIClient()
    anonymous.get("/api/v1/courses/")  # warm the anonymous cache

    signed_in = APIClient()
    signed_in.force_authenticate(student)

    assert signed_in.get("/api/v1/courses/").data["results"][0]["is_enrolled"] is True
    assert anonymous.get("/api/v1/courses/").data["results"][0]["is_enrolled"] is False


def test_filters_are_cached_separately(course):
    other = Category.objects.create(name="d", slug="d")
    client = APIClient()

    assert client.get("/api/v1/courses/?category=c").data["count"] == 1
    assert client.get(f"/api/v1/courses/?category={other.slug}").data["count"] == 0
