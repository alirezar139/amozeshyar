import pytest

from apps.accounts.models import User
from apps.courses.models import Category, Course
from apps.instructors.models import InstructorProfile


@pytest.fixture
def course():
    teacher = User.objects.create_user(email="t@example.com", password="x", role=User.Role.ADMIN)
    InstructorProfile.objects.create(user=teacher, is_site_owner=True)
    category = Category.objects.create(name="c", slug="c")
    return Course.objects.create(
        instructor=teacher.instructor_profile, category=category, title="Python", status=Course.Status.PUBLISHED
    )
