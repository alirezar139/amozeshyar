import pytest
from rest_framework.test import APIClient

from apps.accounts.models import User
from apps.courses.models import Category, Course, Lesson
from apps.instructors.models import InstructorProfile
from apps.videos.models import VideoAsset

pytestmark = pytest.mark.django_db

Status = VideoAsset.Status


@pytest.fixture
def course():
    teacher = User.objects.create_user(email="t@example.com", password="x", role=User.Role.ADMIN)
    InstructorProfile.objects.create(user=teacher, is_site_owner=True)
    category = Category.objects.create(name="c", slug="c")
    return Course.objects.create(
        instructor=teacher.instructor_profile, category=category, title="Python", status=Course.Status.PUBLISHED
    )


def video(course, order, status):
    lesson = Lesson.objects.create(course=course, title=f"L{order}", order=order)
    return VideoAsset.objects.create(lesson=lesson, original_filename="v.mp4", storage_key="k", status=status)


def test_queue_counts_the_running_video_and_earlier_uploads(course):
    video(course, 1, Status.READY)
    video(course, 2, Status.PROCESSING)
    first = video(course, 3, Status.UPLOADING)
    second = video(course, 4, Status.UPLOADING)
    video(course, 5, Status.FAILED)

    assert first.queue_ahead() == 1  # only the one being transcoded
    assert second.queue_ahead() == 2
    assert Lesson.objects.get(order=2).video_asset.queue_ahead() is None  # no longer waiting


def test_lesson_list_shows_the_admin_the_queue_position(course):
    running = video(course, 1, Status.PROCESSING)
    queued = video(course, 2, Status.UPLOADING)
    admin = APIClient()
    admin.force_authenticate(course.instructor.user)

    lessons = {row["id"]: row for row in admin.get(f"/api/v1/lessons/?course={course.id}").data}

    assert lessons[queued.lesson_id]["video_queue_ahead"] == 1
    assert lessons[running.lesson_id]["video_queue_ahead"] is None
