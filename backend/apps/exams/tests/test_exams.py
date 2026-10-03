from datetime import timedelta

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from django.utils import timezone
from rest_framework.test import APIClient

from apps.accounts.models import User
from apps.courses.models import Category, Course
from apps.enrollments.models import Enrollment
from apps.exams.models import Answer, Attempt, Exam
from apps.exams.services import normalize_answer
from apps.instructors.models import InstructorProfile
from apps.messaging.models import Message

pytestmark = pytest.mark.django_db


@pytest.fixture
def teacher():
    user = User.objects.create_user(email="t@example.com", password="x", role=User.Role.ADMIN)
    InstructorProfile.objects.create(user=user, is_site_owner=True)
    return user


@pytest.fixture
def course(teacher):
    category = Category.objects.create(name="c", slug="c")
    return Course.objects.create(instructor=teacher.instructor_profile, category=category, title="Python")


@pytest.fixture
def student(course):
    user = User.objects.create_user(email="s@example.com", password="x")
    Enrollment.objects.create(student=user, course=course)
    return user


def as_(user):
    client = APIClient()
    client.force_authenticate(user)
    return client


def build_exam(teacher, course, **exam_fields):
    """An exam with one question of each auto-graded kind, published."""
    client = as_(teacher)
    exam = client.post("/api/v1/exams/manage/", {"course": course.id, "title": "میان‌ترم", **exam_fields}, format="json").data
    q = "/api/v1/exam-questions/"
    single = client.post(q, {
        "exam": exam["id"], "kind": "single_choice", "text": "۲+۲؟", "example": "مثلاً ۱+۱=۲",
        "explanation": "جمع ساده: ۲ و ۲ می‌شود ۴.",
        "choices": [{"text": "۳"}, {"text": "۴", "is_correct": True}],
    }, format="json").data
    short = client.post(q, {
        "exam": exam["id"], "kind": "short_answer", "text": "پایتخت ایران؟", "answer_key": "تهران\nTehran",
        "explanation": "پایتخت ایران تهران است.", "points": "2",
    }, format="json").data
    multi = client.post(q, {
        "exam": exam["id"], "kind": "multiple_choice", "text": "اعداد زوج؟",
        "choices": [{"text": "۲", "is_correct": True}, {"text": "۳"}, {"text": "۴", "is_correct": True}],
    }, format="json").data
    published = client.patch(f"/api/v1/exams/manage/{exam['id']}/", {"status": "published"}, format="json")
    assert published.status_code == 200, published.data
    return exam["id"], single, short, multi


def test_teacher_question_validation_and_publish_needs_questions(teacher, course):
    client = as_(teacher)
    exam = client.post("/api/v1/exams/manage/", {"course": course.id, "title": "خالی"}, format="json").data
    assert client.patch(f"/api/v1/exams/manage/{exam['id']}/", {"status": "published"}, format="json").status_code == 400

    no_correct = client.post("/api/v1/exam-questions/", {
        "exam": exam["id"], "kind": "single_choice", "text": "?", "choices": [{"text": "a"}, {"text": "b"}],
    }, format="json")
    assert no_correct.status_code == 400 and "choices" in no_correct.data
    no_key = client.post("/api/v1/exam-questions/", {"exam": exam["id"], "kind": "short_answer", "text": "?"}, format="json")
    assert no_key.status_code == 400 and "answer_key" in no_key.data

    media = client.post("/api/v1/exam-question-media/", {
        "question": client.post("/api/v1/exam-questions/", {"exam": exam["id"], "kind": "essay", "text": "توضیح بده"}, format="json").data["id"],
        "role": "answer",
        "file": SimpleUploadedFile("key.mp3", b"ID3" + b"\0" * 100, content_type="audio/mpeg"),
    }, format="multipart")
    assert media.status_code == 201 and media.data["kind"] == "audio" and media.data["role"] == "answer"

    student = User.objects.create_user(email="x@example.com", password="x")
    assert as_(student).get("/api/v1/exams/manage/").status_code == 403


def test_student_takes_exam_early_submit_auto_grades_and_gets_bot_message(teacher, course, student):
    exam_id, single, short, multi = build_exam(teacher, course, duration_minutes=30)
    client = as_(student)

    listed = client.get("/api/v1/exams/").data
    assert [e["id"] for e in listed] == [exam_id] and listed[0]["is_open"] and listed[0]["my_attempt"] is None

    attempt = client.post(f"/api/v1/exams/{exam_id}/start/").data
    assert attempt["status"] == "in_progress" and attempt["deadline"]
    first = attempt["questions"][0]
    assert "correct_choices" not in first and "explanation" not in first and "is_correct" not in str(first["choices"])
    assert first["example"] == "مثلاً ۱+۱=۲"

    wrong_choice = next(c["id"] for c in single["choices"] if not c["is_correct"])
    url = f"/api/v1/exam-attempts/{attempt['id']}/"
    assert client.post(url + "answer/", {"question": single["id"], "choices": [wrong_choice]}, format="json").status_code == 200
    assert client.post(url + "answer/", {"question": short["id"], "text": " تِهران. "}, format="json").status_code == 200
    evens = [c["id"] for c in multi["choices"] if c["is_correct"]]
    assert client.post(url + "answer/", {"question": multi["id"], "choices": evens}, format="json").status_code == 200

    result = client.post(url + "submit/").data
    assert result["status"] == "graded" and result["submit_reason"] == "student"
    assert float(result["score"]) == 3 and float(result["max_score"]) == 4 and result["passed"]
    by_id = {q["id"]: q for q in result["questions"]}
    assert by_id[single["id"]]["is_correct"] is False and by_id[single["id"]]["explanation"]
    assert by_id[short["id"]]["is_correct"] is True

    # Locked after submitting; starting again just returns the same finished attempt.
    assert client.post(url + "answer/", {"question": single["id"], "choices": []}, format="json").status_code == 400
    assert client.post(f"/api/v1/exams/{exam_id}/start/").data["id"] == attempt["id"]

    bot = Message.objects.get(bot="exam")
    assert bot.conversation.student == student and bot.sender == teacher
    assert "۳ از ۴" in bot.text and "سوال ۱: جمع ساده" in bot.text


def test_time_up_auto_submits_and_refuses_late_answers(teacher, course, student):
    exam_id, single, *_ = build_exam(teacher, course, duration_minutes=10)
    client = as_(student)
    attempt_id = client.post(f"/api/v1/exams/{exam_id}/start/").data["id"]
    Attempt.objects.filter(pk=attempt_id).update(deadline=timezone.now() - timedelta(minutes=1))

    late = client.post(f"/api/v1/exam-attempts/{attempt_id}/answer/", {"question": single["id"], "choices": []}, format="json")
    assert late.status_code == 400
    result = client.get(f"/api/v1/exam-attempts/{attempt_id}/").data
    assert result["status"] == "graded" and result["submit_reason"] == "timeout" and float(result["score"]) == 0


def test_closing_time_caps_the_deadline(teacher, course, student):
    closes = timezone.now() + timedelta(minutes=5)
    exam_id, *_ = build_exam(teacher, course, duration_minutes=60, available_until=closes.isoformat())
    attempt = as_(student).post(f"/api/v1/exams/{exam_id}/start/").data
    assert abs((Attempt.objects.get(pk=attempt["id"]).deadline - closes).total_seconds()) < 1

    Exam.objects.filter(pk=exam_id).update(available_until=timezone.now() - timedelta(seconds=1))
    other = User.objects.create_user(email="late@example.com", password="x")
    Enrollment.objects.create(student=other, course=course)
    assert as_(other).post(f"/api/v1/exams/{exam_id}/start/").status_code == 400


def test_question_timer(teacher, course, student):
    exam_id, single, short, _ = build_exam(teacher, course)
    as_(teacher).patch(f"/api/v1/exam-questions/{short['id']}/", {"time_limit_seconds": 30}, format="json")
    client = as_(student)
    attempt_id = client.post(f"/api/v1/exams/{exam_id}/start/").data["id"]
    url = f"/api/v1/exam-attempts/{attempt_id}/"

    assert client.post(url + "answer/", {"question": short["id"], "text": "تهران"}, format="json").status_code == 400  # not opened
    opened = client.post(url + "open/", {"question": short["id"]}, format="json").data
    assert opened["deadline"]
    assert client.post(url + "answer/", {"question": short["id"], "text": "تهران"}, format="json").status_code == 200

    Answer.objects.filter(attempt_id=attempt_id, question_id=short["id"]).update(opened_at=timezone.now() - timedelta(minutes=1))
    late = client.post(url + "answer/", {"question": short["id"], "text": "شیراز"}, format="json")
    assert late.status_code == 400 and late.data["code"] == "question_closed"
    # The rest of the exam is still open.
    choice = next(c["id"] for c in single["choices"] if c["is_correct"])
    assert client.post(url + "answer/", {"question": single["id"], "choices": [choice]}, format="json").status_code == 200


def test_essay_with_voice_waits_for_teacher_then_notifies(teacher, course, student):
    client = as_(teacher)
    exam = client.post("/api/v1/exams/manage/", {"course": course.id, "title": "شفاهی"}, format="json").data
    essay = client.post("/api/v1/exam-questions/", {
        "exam": exam["id"], "kind": "essay", "text": "خودتان را معرفی کنید", "points": "5",
        "answer_key": "نمونه‌ی پاسخ…", "explanation": "به تلفظ دقت کنید.",
    }, format="json").data
    client.patch(f"/api/v1/exams/manage/{exam['id']}/", {"status": "published"}, format="json")

    s = as_(student)
    attempt_id = s.post(f"/api/v1/exams/{exam['id']}/start/").data["id"]
    voice = SimpleUploadedFile("voice.webm", b"\x1aE\xdf\xa3" + b"\0" * 100, content_type="audio/webm")
    uploaded = s.post(f"/api/v1/exam-attempts/{attempt_id}/files/", {"question": essay["id"], "file": voice, "duration_seconds": "12"}, format="multipart")
    assert uploaded.status_code == 201 and uploaded.data["kind"] == "audio"
    bad = SimpleUploadedFile("x.exe", b"MZ", content_type="application/octet-stream")
    assert s.post(f"/api/v1/exam-attempts/{attempt_id}/files/", {"question": essay["id"], "file": bad}, format="multipart").status_code == 400

    result = s.post(f"/api/v1/exam-attempts/{attempt_id}/submit/").data
    assert result["status"] == "submitted" and result["questions"][0]["score"] is None
    assert not Message.objects.filter(bot="exam").exists()

    summary = client.get(f"/api/v1/exams/manage/{exam['id']}/attempts/").data
    assert summary[0]["pending_count"] == 1
    answer_id = result["questions"][0]["answer_id"]
    assert client.post(f"/api/v1/exam-attempts/manage/{attempt_id}/grade/", {"answer": answer_id, "score": 9}, format="json").status_code == 400
    graded = client.post(
        f"/api/v1/exam-attempts/manage/{attempt_id}/grade/", {"answer": answer_id, "score": 3, "feedback": "حروف r را واضح‌تر بگویید."}, format="json"
    ).data
    assert graded["status"] == "graded" and float(graded["score"]) == 3
    assert "حروف r" in Message.objects.get(bot="exam").text

    # Deleting the attempt lets the student retake it.
    assert client.delete(f"/api/v1/exam-attempts/manage/{attempt_id}/").status_code == 204
    assert s.post(f"/api/v1/exams/{exam['id']}/start/").data["status"] == "in_progress"


def test_not_enrolled_student_sees_nothing(teacher, course):
    exam_id, *_ = build_exam(teacher, course)
    outsider = User.objects.create_user(email="o@example.com", password="x")
    client = as_(outsider)
    assert client.get("/api/v1/exams/").data == []
    assert client.post(f"/api/v1/exams/{exam_id}/start/").status_code == 404


def test_normalize_answer():
    assert normalize_answer("  كتاب‌ها ") == normalize_answer("کتاب ها")
    assert normalize_answer("۱۲۳.") == "123"
    assert normalize_answer("Tehran!") == normalize_answer("tehran")
