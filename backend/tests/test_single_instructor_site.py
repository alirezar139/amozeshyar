"""One install = one instructor's site: the instructor is the admin, public
sign-up only makes students, and the developer account stays out of the
instructor's reach."""
import pytest
from django.core.management import call_command
from rest_framework.test import APIClient

from apps.accounts.models import User
from apps.courses.models import Category, Course
from apps.instructors.models import InstructorProfile

pytestmark = pytest.mark.django_db


@pytest.fixture
def site(monkeypatch):
    monkeypatch.setenv("DEVELOPER_EMAIL", "dev@example.com")
    monkeypatch.setenv("DEVELOPER_PASSWORD", "dev-pass-123!")
    call_command(
        "setup_site", email="ali@example.com", password="ali-pass-123!",
        first_name="علی", last_name="احمدی", headline="مدرس پایتون",
    )
    return InstructorProfile.objects.get(is_site_owner=True)


def client_for(user):
    client = APIClient()
    client.force_authenticate(user)
    return client


def test_setup_site_creates_owner_and_developer(site):
    assert site.user.email == "ali@example.com"
    assert site.user.role == User.Role.ADMIN and not site.user.is_superuser
    assert site.headline == "مدرس پایتون"
    dev = User.objects.get(email="dev@example.com")
    assert dev.is_superuser and dev.role == User.Role.ADMIN


def test_setup_site_is_rerunnable_and_keeps_passwords(site):
    call_command("setup_site", email="ali@example.com", password="something-else")
    site.user.refresh_from_db()
    assert site.user.check_password("ali-pass-123!")
    assert InstructorProfile.objects.filter(is_site_owner=True).count() == 1


def test_public_site_endpoint_returns_owner(site):
    response = APIClient().get("/api/v1/site/")
    assert response.status_code == 200
    assert response.data["display_name"] == "علی احمدی"


def test_registration_always_creates_student(site):
    response = APIClient().post("/api/v1/auth/register/", {
        "email": "s@example.com", "password": "Very-long-pass-42", "role": "admin",
    })
    assert response.status_code == 201
    assert User.objects.get(email="s@example.com").role == User.Role.STUDENT


def test_developer_hidden_from_instructor(site):
    dev = User.objects.get(email="dev@example.com")
    owner_client = client_for(site.user)
    emails = [u["email"] for u in owner_client.get("/api/v1/auth/admin/users/").data["results"]]
    assert "dev@example.com" not in emails
    assert owner_client.patch(f"/api/v1/auth/admin/users/{dev.id}/", {"is_active": False}).status_code == 404

    dev_emails = [u["email"] for u in client_for(dev).get("/api/v1/auth/admin/users/").data["results"]]
    assert "ali@example.com" in dev_emails


def test_admin_course_belongs_to_owner_and_publishes(site):
    category = Category.objects.create(name="برنامه‌نویسی", slug="programming")
    client = client_for(site.user)
    response = client.post("/api/v1/courses/manage/", {"category": category.id, "title": "پایتون مقدماتی"})
    assert response.status_code == 201
    course = Course.objects.get(id=response.data["id"])
    assert course.instructor == site and course.status == Course.Status.PUBLISHED and course.published_at

    assert client.patch(f"/api/v1/courses/manage/{course.id}/", {"status": "draft"}).status_code == 200
    assert APIClient().get(f"/api/v1/courses/{course.slug}/").status_code == 404
    assert client.patch(f"/api/v1/courses/manage/{course.id}/", {"status": "rejected"}).status_code == 400


def test_students_cannot_manage(site):
    student = User.objects.create_user(email="s@example.com", password="x")
    client = client_for(student)
    assert client.get("/api/v1/courses/manage/").status_code == 403
    assert client.get("/api/v1/class-sessions/").status_code == 403
    assert client.get("/api/v1/site/settings/").status_code == 403


def test_site_settings_edit_links_and_remove_photo(site):
    from django.core.files.uploadedfile import SimpleUploadedFile

    site.cover_image = SimpleUploadedFile("me.jpg", b"fake", content_type="image/jpeg")
    site.save()
    client = client_for(site.user)
    response = client.patch(
        "/api/v1/site/settings/",
        {"social_links": {"اینستاگرام": "https://instagram.com/ali"}, "cover_image": None},
        format="json",
    )
    assert response.status_code == 200
    site.refresh_from_db()
    assert site.social_links == {"اینستاگرام": "https://instagram.com/ali"}
    assert not site.cover_image
