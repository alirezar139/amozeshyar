import io

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from PIL import Image
from rest_framework.test import APIClient

from apps.accounts.models import User
from apps.common import validators
from apps.courses.models import Category, Course
from apps.instructors.models import InstructorProfile

pytestmark = pytest.mark.django_db


def png(name="cover.png"):
    buffer = io.BytesIO()
    Image.new("RGB", (32, 20), "teal").save(buffer, format="PNG")
    return SimpleUploadedFile(name, buffer.getvalue(), content_type="image/png")


@pytest.fixture
def admin():
    user = User.objects.create_user(email="t@example.com", password="x", role=User.Role.ADMIN)
    InstructorProfile.objects.create(user=user, is_site_owner=True)
    client = APIClient()
    client.force_authenticate(user)
    return client


@pytest.fixture
def course():
    owner = InstructorProfile.objects.get(is_site_owner=True)
    category = Category.objects.create(name="c", slug="c")
    return Course.objects.create(instructor=owner, category=category, title="Python", status=Course.Status.PUBLISHED)


def test_admin_sets_and_removes_a_course_cover(admin, course):
    response = admin.patch(f"/api/v1/courses/manage/{course.id}/", {"cover_image": png()}, format="multipart")
    assert response.status_code == 200, response.data
    assert response.data["cover_image"].endswith(".png")
    assert APIClient().get(f"/api/v1/courses/{course.slug}/").data["cover_image"].endswith(".png")

    response = admin.patch(f"/api/v1/courses/manage/{course.id}/", {"cover_image": None}, format="json")
    assert response.status_code == 200 and response.data["cover_image"] is None


def test_category_photo_upload(admin, course):
    category = course.category
    response = admin.patch(f"/api/v1/categories/{category.id}/", {"image": png("cat.png")}, format="multipart")
    assert response.status_code == 200, response.data
    assert response.data["image"].endswith(".png")


def test_images_over_the_limit_are_refused(admin, course, monkeypatch):
    monkeypatch.setattr(validators, "MAX_IMAGE_SIZE_BYTES", 10)

    response = admin.patch(f"/api/v1/courses/manage/{course.id}/", {"cover_image": png()}, format="multipart")

    assert response.status_code == 400
    assert "۵ مگابایت" in str(response.data["cover_image"])


def test_non_images_are_refused(admin, course):
    fake = SimpleUploadedFile("cover.png", b"<svg onload=alert(1)>", content_type="image/png")

    response = admin.patch(f"/api/v1/courses/manage/{course.id}/", {"cover_image": fake}, format="multipart")

    assert response.status_code == 400
