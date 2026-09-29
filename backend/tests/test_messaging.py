import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from rest_framework.test import APIClient

from apps.accounts.models import User
from apps.courses.models import Category, Course
from apps.enrollments.models import Enrollment
from apps.instructors.models import InstructorProfile

pytestmark = pytest.mark.django_db


@pytest.fixture
def world():
    teacher = User.objects.create_user(email="t@example.com", password="x", role=User.Role.ADMIN, first_name="مهدی")
    InstructorProfile.objects.create(user=teacher, is_site_owner=True)
    developer = User.objects.create_user(email="d@example.com", password="x", role=User.Role.ADMIN, is_superuser=True)
    category = Category.objects.create(name="c", slug="c")
    course = Course.objects.create(instructor=teacher.instructor_profile, category=category, title="Python", status=Course.Status.PUBLISHED)
    alice = User.objects.create_user(email="a@example.com", password="x", first_name="Alice")
    bob = User.objects.create_user(email="b@example.com", password="x", first_name="Bob")
    Enrollment.objects.create(student=alice, course=course)
    return {"teacher": teacher, "developer": developer, "course": course, "alice": alice, "bob": bob}


def as_(user):
    client = APIClient()
    client.force_authenticate(user)
    return client


def conversations(user):
    return as_(user).get("/api/v1/conversations/").data


def send(user, conversation_id, **data):
    return as_(user).post(f"/api/v1/conversations/{conversation_id}/messages/", data, format="multipart")


def test_student_sees_own_direct_and_enrolled_groups_only(world):
    alice = {c["kind"]: c for c in conversations(world["alice"])}
    assert set(alice) == {"direct", "course"}
    assert alice["direct"]["title"] == "مهدی"
    assert alice["course"]["title"] == "Python"

    bob_kinds = [c["kind"] for c in conversations(world["bob"])]
    assert bob_kinds == ["direct"]  # not enrolled -> no course group

    group_id = alice["course"]["id"]
    assert as_(world["bob"]).get(f"/api/v1/conversations/{group_id}/messages/").status_code == 404
    assert send(world["bob"], alice["direct"]["id"], text="hi").status_code == 404  # someone else's DM


def test_direct_chat_roundtrip_unread_and_read_receipts(world):
    alice_direct = next(c for c in conversations(world["alice"]) if c["kind"] == "direct")
    cid = alice_direct["id"]

    # teacher doesn't see an empty DM yet
    assert all(c["kind"] == "course" for c in conversations(world["teacher"]))

    sent = send(world["alice"], cid, text="سلام استاد")
    assert sent.status_code == 201 and sent.data["is_mine"]

    teacher_view = next(c for c in conversations(world["teacher"]) if c["kind"] == "direct")
    assert teacher_view["title"] == "Alice" and teacher_view["unread"] == 1
    assert as_(world["teacher"]).get("/api/v1/conversations/unread/").data["total"] == 1

    # the developer reading doesn't count as the teacher reading
    as_(world["developer"]).post(f"/api/v1/conversations/{cid}/read/", {})
    history = as_(world["alice"]).get(f"/api/v1/conversations/{cid}/messages/").data
    assert history["others_last_read"] == 0

    as_(world["teacher"]).post(f"/api/v1/conversations/{cid}/read/", {})
    assert as_(world["teacher"]).get("/api/v1/conversations/unread/").data["total"] == 0
    history = as_(world["alice"]).get(f"/api/v1/conversations/{cid}/messages/").data
    assert history["others_last_read"] == sent.data["id"]

    reply = send(world["teacher"], cid, text="سلام!")
    new = as_(world["alice"]).get(f"/api/v1/conversations/{cid}/messages/?after={sent.data['id']}").data["messages"]
    assert [m["id"] for m in new] == [reply.data["id"]] and new[0]["sender"]["is_teacher"]


def test_group_chat_reaches_enrolled_students(world):
    group = next(c for c in conversations(world["teacher"]) if c["kind"] == "course")
    send(world["teacher"], group["id"], text="جلسه‌ی بعد پنجشنبه است")
    alice_group = next(c for c in conversations(world["alice"]) if c["kind"] == "course")
    assert alice_group["unread"] == 1 and alice_group["members"] == 2
    assert send(world["alice"], group["id"], text="ممنون").status_code == 201


def test_attachments_image_file_voice_and_rejections(world):
    cid = next(c for c in conversations(world["alice"]) if c["kind"] == "direct")["id"]

    image = send(world["alice"], cid, file=SimpleUploadedFile("shot.png", b"\x89PNG..."))
    assert image.status_code == 201 and image.data["attachment_kind"] == "image" and image.data["attachment_url"]

    doc = send(world["alice"], cid, file=SimpleUploadedFile("تمرین.pdf", b"%PDF"), text="تمرین من")
    assert doc.data["attachment_kind"] == "file" and doc.data["attachment_name"] == "تمرین.pdf"

    voice = send(world["alice"], cid, file=SimpleUploadedFile("voice.webm", b"webm"), voice="true", duration_seconds=7)
    assert voice.data["attachment_kind"] == "voice" and voice.data["duration_seconds"] == 7

    assert send(world["alice"], cid, file=SimpleUploadedFile("x.html", b"<script>")).status_code == 400
    assert send(world["alice"], cid, text="   ").status_code == 400


def test_teacher_can_start_a_conversation_with_a_student(world):
    response = as_(world["teacher"]).post("/api/v1/conversations/start/", {"student_id": world["bob"].id})
    assert response.status_code == 200 and response.data["title"] == "Bob"
    # students can't start one with someone else
    other = as_(world["bob"]).post("/api/v1/conversations/start/", {"student_id": world["alice"].id})
    assert other.data["id"] == response.data["id"]  # always their own


def test_board_cards_crud_move_and_admin_only(world):
    teacher = as_(world["teacher"])
    a = teacher.post("/api/v1/board/cards/", {"title": "ضبط جلسه ۳", "course": world["course"].id}, format="json").data
    b = teacher.post("/api/v1/board/cards/", {"title": "جزوه"}, format="json").data
    assert a["column"] == "idea" and b["position"] > a["position"] and a["course_title"] == "Python"

    moved = teacher.patch(f"/api/v1/board/cards/{b['id']}/", {"column": "ready", "position": 10}, format="json").data
    assert moved["column"] == "ready"
    cards = teacher.get("/api/v1/board/cards/").data
    assert [c["title"] for c in cards] == ["ضبط جلسه ۳", "جزوه"]

    assert as_(world["alice"]).get("/api/v1/board/cards/").status_code == 403
    assert teacher.delete(f"/api/v1/board/cards/{a['id']}/").status_code == 204
