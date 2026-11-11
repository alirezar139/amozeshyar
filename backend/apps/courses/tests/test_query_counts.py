"""PERF-01: the pages a buyer opens cost the same number of queries whatever the course's size.

The course page is the sales page; a signed-in student skips the public cache, so every lesson
used to cost 4 queries (video, files, and its progress twice): 103 for a 25-lesson course.
"""
import pytest
from django.db import connection
from django.test.utils import CaptureQueriesContext
from rest_framework.test import APIClient

from apps.accounts.models import User
from apps.courses.models import Category, Course, Lesson, LessonFile
from apps.enrollments.models import Enrollment, LessonProgress
from apps.instructors.models import InstructorProfile
from apps.videos.models import VideoAsset

pytestmark = pytest.mark.django_db


def make_course(slug, lessons, student=None):
    owner = User.objects.filter(email="owner@q.test").first()
    if owner is None:
        owner = User.objects.create_user(email="owner@q.test", password="x", role=User.Role.ADMIN)
        InstructorProfile.objects.create(user=owner, is_site_owner=True)
    category, _ = Category.objects.get_or_create(slug="q", defaults={"name": "q"})
    course = Course.objects.create(
        instructor=owner.instructor_profile, category=category, title=slug, slug=slug, status=Course.Status.PUBLISHED
    )
    for n in range(1, lessons + 1):
        lesson = Lesson.objects.create(course=course, title=f"L{n}", order=n)
        VideoAsset.objects.create(lesson=lesson, original_filename="v.mp4", storage_key=f"lessons/{lesson.id}/k/v.mp4",
                                  status=VideoAsset.Status.READY)
        LessonFile.objects.create(lesson=lesson, title="f", file=f"lesson-files/{n}.pdf", original_name=f"{n}.pdf")
        if student:
            LessonProgress.objects.create(student=student, lesson=lesson, position_seconds=10, completed=n % 2 == 0)
    if student:
        Enrollment.objects.create(student=student, course=course)
    return course


def count(client, url):
    with CaptureQueriesContext(connection) as ctx:
        response = client.get(url)
    assert response.status_code == 200, response.content[:200]
    return len(ctx.captured_queries)


@pytest.fixture
def student():
    return User.objects.create_user(email="s@q.test", password="x")


def signed_in(user):
    client = APIClient()
    client.force_authenticate(user)
    return client


def test_course_page_queries_do_not_grow_with_lessons(student):
    small, big = make_course("small", 5, student), make_course("big", 40, student)
    client = signed_in(student)
    n_small = count(client, f"/api/v1/courses/{small.slug}/")
    n_big = count(client, f"/api/v1/courses/{big.slug}/")
    print(f"course page, signed-in student: 5 lessons {n_small} queries, 40 lessons {n_big} queries")
    assert n_big == n_small
    assert n_big <= 10


def test_course_page_still_shows_each_lessons_own_progress(student):
    course = make_course("p", 4, student)
    lessons = signed_in(student).get(f"/api/v1/courses/{course.slug}/").json()["lessons"]
    assert [(lesson["progress_seconds"], lesson["completed"], len(lesson["files"]), lesson["has_video"]) for lesson in lessons] == [
        (10, False, 1, True), (10, True, 1, True), (10, False, 1, True), (10, True, 1, True)
    ]
    other = User.objects.create_user(email="o@q.test", password="x")
    assert {lesson["progress_seconds"] for lesson in signed_in(other).get(f"/api/v1/courses/{course.slug}/").json()["lessons"]} == {0}


def test_catalog_queries_do_not_grow_with_courses(student):
    for n in range(3):
        make_course(f"a{n}", 2, student)
    client = signed_in(student)
    n_few = count(client, "/api/v1/courses/")
    for n in range(12):
        make_course(f"b{n}", 2, student)
    n_many = count(client, "/api/v1/courses/")
    print(f"catalog, signed-in student: 3 courses {n_few} queries, 15 courses {n_many} queries")
    assert n_many == n_few


def test_my_enrollments_queries_do_not_grow_with_courses(student):
    for n in range(2):
        make_course(f"e{n}", 3, student)
    client = signed_in(student)
    n_few = count(client, "/api/v1/enrollments/")
    for n in range(10):
        make_course(f"f{n}", 3, student)
    n_many = count(client, "/api/v1/enrollments/")
    print(f"my enrollments: 2 courses {n_few} queries, 12 courses {n_many} queries")
    assert n_many == n_few
    progress = client.get("/api/v1/enrollments/").json()["results"][0]["progress"]
    assert progress == {"total_lessons": 3, "completed_lessons": 1, "percent": 33}
