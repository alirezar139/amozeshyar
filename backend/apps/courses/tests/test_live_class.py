"""Live classes: who gets into a class's room, and the Jitsi entry token (live_class.py)."""
from datetime import timedelta

import jwt
import pytest
from django.utils import timezone
from rest_framework.test import APIClient

from apps.accounts.models import User
from apps.courses.models import Category, ClassSession, Course
from apps.enrollments.models import Enrollment
from apps.instructors.models import InstructorProfile

pytestmark = pytest.mark.django_db
SECRET = "test-secret-not-real"


@pytest.fixture
def site():
    admin = User.objects.create_user(email="t@lc.test", password="x", role=User.Role.ADMIN, first_name="استاد")
    InstructorProfile.objects.create(user=admin, is_site_owner=True)
    category = Category.objects.create(name="c", slug="c")
    course = Course.objects.create(instructor=admin.instructor_profile, category=category, title="Python", slug="py",
                                   status=Course.Status.PUBLISHED)
    other = Course.objects.create(instructor=admin.instructor_profile, category=category, title="Go", slug="go",
                                  status=Course.Status.PUBLISHED)
    session = ClassSession.objects.create(course=course, title="Week 1", starts_at=timezone.now() + timedelta(hours=1))
    student = User.objects.create_user(email="s@lc.test", password="x", first_name="دانشجو")
    Enrollment.objects.create(student=student, course=course)
    return admin, student, course, other, session


@pytest.fixture
def self_hosted(settings):
    settings.JITSI_DOMAIN = "meet.example.ir"
    settings.JITSI_APP_ID = "amozeshyar"
    settings.JITSI_APP_SECRET = SECRET


def as_user(user):
    client = APIClient()
    client.force_authenticate(user)
    return client


def join(user, session):
    return as_user(user).get(f"/api/v1/class-sessions/{session.id}/join/")


def decode(token):
    return jwt.decode(token, SECRET, algorithms=["HS256"], audience="jitsi")


def test_public_jitsi_stays_exactly_as_before(site):
    _, student, _, _, session = site
    data = join(student, session).json()
    assert data["domain"] == "meet.jit.si"
    assert data["room_name"] == session.room_slug
    assert "jwt" not in data


def test_self_hosted_jitsi_gives_a_token_for_this_room_and_person(site, self_hosted):
    _, student, _, _, session = site
    data = join(student, session).json()
    claims = decode(data["jwt"])
    assert data["domain"] == "meet.example.ir"
    assert claims["room"] == data["room_name"] == session.room_slug.lower()  # Jitsi lower-cases rooms
    assert claims["iss"] == "amozeshyar" and claims["sub"] == "meet.example.ir"
    assert claims["context"]["user"]["id"] == str(student.id)
    assert claims["moderator"] is False and claims["context"]["user"]["moderator"] is False
    assert 0 < claims["exp"] - timezone.now().timestamp() <= 3600


def test_only_the_instructor_enters_as_moderator(site, self_hosted):
    admin, _, _, _, session = site
    claims = decode(join(admin, session).json()["jwt"])
    assert claims["moderator"] is True and claims["context"]["user"]["affiliation"] == "owner"


def test_a_token_signed_with_another_secret_is_not_ours(site, self_hosted):
    _, student, _, _, session = site
    token = join(student, session).json()["jwt"]
    with pytest.raises(jwt.InvalidSignatureError):
        jwt.decode(token, "someone-elses-secret", algorithms=["HS256"], audience="jitsi")


@pytest.mark.parametrize("mode", ["public", "self_hosted"])
def test_students_not_enrolled_in_that_course_get_nothing(site, settings, mode):
    _, _, _, other, session = site
    if mode == "self_hosted":
        settings.JITSI_APP_SECRET = SECRET
    outsider = User.objects.create_user(email="o@lc.test", password="x")
    other_student = User.objects.create_user(email="g@lc.test", password="x")
    Enrollment.objects.create(student=other_student, course=other)  # enrolled, but in another course
    lapsed = User.objects.create_user(email="l@lc.test", password="x")
    Enrollment.objects.create(student=lapsed, course=session.course, is_active=False)  # e.g. refunded
    for user in (outsider, other_student, lapsed):
        response = join(user, session)
        assert response.status_code == 403
        assert "jwt" not in response.json() and "room_name" not in response.json()
    assert APIClient().get(f"/api/v1/class-sessions/{session.id}/join/").status_code == 401


def test_schedules_never_carry_the_room_or_a_token(site, self_hosted):
    admin, student, _, _, session = site
    schedule = as_user(student).get("/api/v1/schedule/upcoming/").content.decode()
    sessions = as_user(admin).get("/api/v1/class-sessions/").content.decode()
    for body in (schedule, sessions):
        assert "Week 1" in body  # the session is listed, so the check below means something
        assert session.room_slug not in body and session.room_slug.lower() not in body
        assert "eyJ" not in body
