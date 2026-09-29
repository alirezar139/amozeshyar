import pytest
from rest_framework.test import APIClient

from apps.accounts.models import User
from apps.courses.models import Category, Course
from apps.instructors.models import InstructorProfile

pytestmark = pytest.mark.django_db


@pytest.fixture
def teacher():
    user = User.objects.create_user(email="t@example.com", password="x", role=User.Role.ADMIN)
    InstructorProfile.objects.create(user=user, is_site_owner=True)
    return user


def as_(user):
    client = APIClient()
    client.force_authenticate(user)
    return client


def test_board_cards_crud_move_and_admin_only(teacher):
    category = Category.objects.create(name="c", slug="c")
    course = Course.objects.create(instructor=teacher.instructor_profile, category=category, title="Python")
    client = as_(teacher)

    a = client.post("/api/v1/board/cards/", {"title": "ضبط جلسه ۳", "course": course.id}, format="json").data
    b = client.post("/api/v1/board/cards/", {"title": "جزوه"}, format="json").data
    assert a["column"] == "idea" and b["position"] > a["position"] and a["course_title"] == "Python"

    moved = client.patch(f"/api/v1/board/cards/{b['id']}/", {"column": "ready", "position": 10}, format="json").data
    assert moved["column"] == "ready"
    assert [c["title"] for c in client.get("/api/v1/board/cards/").data] == ["ضبط جلسه ۳", "جزوه"]

    student = User.objects.create_user(email="s@example.com", password="x")
    assert as_(student).get("/api/v1/board/cards/").status_code == 403
    assert client.delete(f"/api/v1/board/cards/{a['id']}/").status_code == 204
