"""BE-01: no request a user can make answers 500.

Every endpoint in the OpenAPI schema is called, as the site's admin and as a student, with junk
in every query parameter people tend to send ids or numbers in, and (for writes) a body of junk
values. A 4xx is fine; a 500 is a bug (and a line of noise in the production log).
"""
import re

import pytest
from drf_spectacular.generators import SchemaGenerator
from rest_framework.test import APIClient

from apps.accounts.models import User
from apps.courses.models import Category, ClassSession, Course, Lesson
from apps.enrollments.models import Enrollment
from apps.instructors.models import InstructorProfile
from apps.messaging import services as messaging

pytestmark = pytest.mark.django_db

JUNK = "abc'\"<>"
QUERY = {name: JUNK for name in (
    "after", "before", "since", "days", "page", "page_size", "course", "lesson", "student", "status",
    "ordering", "search", "category", "level", "min_price", "max_price", "limit", "offset", "q", "kind",
)}
BODY = {name: JUNK for name in (
    "student_id", "message_id", "course", "lesson", "order", "direction", "user_id", "members", "amount",
    "code", "course_ids", "items", "position_seconds", "completed", "seconds", "price", "status", "reason",
)}


@pytest.fixture
def site():
    admin = User.objects.create_user(email="admin@fz.test", password="x", role=User.Role.ADMIN)
    InstructorProfile.objects.create(user=admin, is_site_owner=True)
    student = User.objects.create_user(email="s@fz.test", password="x")
    course = Course.objects.create(
        instructor=admin.instructor_profile, category=Category.objects.create(name="c", slug="c"),
        title="C", slug="c", status=Course.Status.PUBLISHED,
    )
    Lesson.objects.create(course=course, title="L", order=1)
    ClassSession.objects.create(course=course, title="S", starts_at="2030-01-01T10:00:00Z")
    Enrollment.objects.create(student=student, course=course)
    messaging.get_or_create_direct(student)
    return admin, student, course


def endpoints():
    schema = SchemaGenerator().get_schema(request=None, public=True)
    for path, operations in schema["paths"].items():
        for method in operations:
            if method in ("get", "post", "patch", "put", "delete"):
                yield path, method


def fill(path, course):
    path = path.replace("{slug}", course.slug)
    return re.sub(r"\{[^}]+\}", "1", path)


@pytest.mark.parametrize("role", ["admin", "student"])
def test_junk_input_never_causes_a_server_error(site, role):
    admin, student, course = site
    client = APIClient(raise_request_exception=False)
    client.force_authenticate(admin if role == "admin" else student)
    errors = []
    calls = 0
    for path, method in endpoints():
        if method == "delete":
            continue  # destructive and takes no input worth fuzzing
        url = fill(path, course)
        if method == "get":
            response = client.get(url, QUERY)
        else:
            response = getattr(client, method)(url + "?" + "&".join(f"{k}=x" for k in ("after", "course")), BODY, format="json")
        calls += 1
        if response.status_code >= 500:
            errors.append(f"{method.upper()} {url} -> {response.status_code}")
    print(f"{role}: {calls} calls")
    for error in errors:
        print(error)
    assert calls > 50  # the schema really was walked
    assert errors == []


# ---------- throttling: a classroom behind one IP ----------

def test_anonymous_visitors_are_not_held_by_the_per_account_cap(settings):
    """The per-account "user" cap used to apply per IP to anonymous traffic too (DRF's fallback),
    so anonymous visitors got min(anon, user). Only "anon" governs them now."""
    from django.core.cache import cache
    from rest_framework.settings import api_settings

    cache.clear()
    rates = dict(api_settings.DEFAULT_THROTTLE_RATES, user="3/hour", anon="50/hour")
    with pytest.MonkeyPatch.context() as mp:
        from rest_framework.throttling import SimpleRateThrottle

        mp.setattr(SimpleRateThrottle, "THROTTLE_RATES", rates)
        client = APIClient()
        codes = [client.get("/api/v1/courses/").status_code for _ in range(10)]
    assert codes == [200] * 10


def test_signed_in_users_still_have_their_per_account_cap():
    from django.core.cache import cache
    from rest_framework.settings import api_settings
    from rest_framework.throttling import SimpleRateThrottle

    cache.clear()
    user = User.objects.create_user(email="t@fz.test", password="x")
    rates = dict(api_settings.DEFAULT_THROTTLE_RATES, user="3/hour")
    with pytest.MonkeyPatch.context() as mp:
        mp.setattr(SimpleRateThrottle, "THROTTLE_RATES", rates)
        client = APIClient()
        client.force_authenticate(user)
        codes = [client.get("/api/v1/courses/").status_code for _ in range(5)]
    assert codes == [200, 200, 200, 429, 429]
