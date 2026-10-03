import pytest
from rest_framework.test import APIClient
from rest_framework_simplejwt.token_blacklist.models import BlacklistedToken
from rest_framework_simplejwt.tokens import RefreshToken

from apps.accounts.models import User
from apps.courses.models import Category, Course
from apps.instructors.models import InstructorProfile

pytestmark = pytest.mark.django_db


def as_(user):
    client = APIClient()
    client.force_authenticate(user)
    return client


@pytest.fixture
def admin():
    return User.objects.create_user(email="t@example.com", password="x", role=User.Role.ADMIN)


def test_admin_sets_a_student_password_and_signs_them_out(admin):
    student = User.objects.create_user(email="s@example.com", password="old-password-1")
    session = RefreshToken.for_user(student)
    url = f"/api/v1/auth/admin/users/{student.id}/set-password/"

    weak = as_(admin).post(url, {"password": "123"}, format="json")
    assert weak.status_code == 400 and weak.data["password"]
    assert as_(admin).post(url, {"password": "Nice-Horse-42"}, format="json").status_code == 204

    student.refresh_from_db()
    assert student.check_password("Nice-Horse-42")
    assert BlacklistedToken.objects.filter(token__jti=session["jti"]).exists()


def test_set_password_is_admin_only_and_developer_is_untouchable(admin):
    student = User.objects.create_user(email="s@example.com", password="x")
    developer = User.objects.create_user(email="d@example.com", password="x", role=User.Role.ADMIN, is_superuser=True)
    assert as_(student).post(f"/api/v1/auth/admin/users/{student.id}/set-password/", {"password": "Nice-Horse-42"}, format="json").status_code == 403
    assert as_(admin).post(f"/api/v1/auth/admin/users/{developer.id}/set-password/", {"password": "Nice-Horse-42"}, format="json").status_code == 404
    # POST on the list still doesn't create users.
    assert as_(admin).post("/api/v1/auth/admin/users/", {"email": "n@example.com"}, format="json").status_code == 405


def test_admin_enrolls_a_student_by_hand(admin):
    InstructorProfile.objects.create(user=admin, is_site_owner=True)
    course = Course.objects.create(instructor=admin.instructor_profile, category=Category.objects.create(name="c", slug="c"), title="Python")
    student = User.objects.create_user(email="s@example.com", password="x")
    url = f"/api/v1/auth/admin/users/{student.id}/courses/"

    assert as_(admin).get(url).data == [{"id": course.id, "title": "Python", "status": "draft", "enrolled": False}]
    assert as_(admin).post(url, {"course": course.id, "enrolled": True}, format="json").data[0]["enrolled"] is True
    assert student.enrollments.get().is_active
    assert as_(admin).post(url, {"course": course.id, "enrolled": False}, format="json").data[0]["enrolled"] is False
    assert not student.enrollments.get().is_active
    assert as_(admin).post(url, {"course": course.id, "enrolled": True}, format="json").data[0]["enrolled"] is True
    assert as_(admin).get(f"/api/v1/auth/admin/users/{admin.id}/courses/").status_code == 400
