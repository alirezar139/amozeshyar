import pytest
from rest_framework.test import APIClient

from apps.accounts.models import User
from apps.courses.models import Category, Course
from apps.instructors.models import InstructorProfile

pytestmark = pytest.mark.django_db
URL = "/api/v1/categories/"


def client_for(user=None):
    client = APIClient()
    if user:
        client.force_authenticate(user)
    return client


@pytest.fixture
def admin():
    return User.objects.create_user(email="a@example.com", password="x", role=User.Role.ADMIN)


def test_admin_creates_a_category_and_anyone_can_list_it(admin):
    res = client_for(admin).post(URL, {"name": " پایتون "}, format="json")

    assert res.status_code == 201
    assert res.data["name"] == "پایتون" and res.data["slug"] == "پایتون"
    assert client_for().get(URL).data["results"][0]["name"] == "پایتون"


def test_students_and_visitors_cannot_create():
    student = User.objects.create_user(email="s@example.com", password="x")

    assert client_for().post(URL, {"name": "x"}, format="json").status_code == 401
    assert client_for(student).post(URL, {"name": "x"}, format="json").status_code == 403


def test_duplicate_name_is_a_validation_error_not_a_crash(admin):
    Category.objects.create(name="Python")

    res = client_for(admin).post(URL, {"name": "python"}, format="json")

    assert res.status_code == 400 and "name" in res.data


def test_cannot_delete_a_category_that_has_courses(admin):
    category = Category.objects.create(name="وب")
    owner = InstructorProfile.objects.create(user=admin, is_site_owner=True)
    Course.objects.create(instructor=owner, category=category, title="t", description="d", price=0)

    res = client_for(admin).delete(f"{URL}{category.id}/")

    assert res.status_code == 400
    assert Category.objects.filter(pk=category.pk).exists()
