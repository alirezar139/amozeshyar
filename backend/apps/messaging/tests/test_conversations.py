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
    # a student who shares no course with alice can't open a chat with her
    assert as_(world["bob"]).post("/api/v1/conversations/start/", {"student_id": world["alice"].id}).status_code == 403
    # and without an id, a student gets their own chat with the teacher
    own = as_(world["bob"]).post("/api/v1/conversations/start/", {})
    assert own.data["kind"] == "direct" and own.data["id"] == response.data["id"]


def enroll(user, course):
    Enrollment.objects.create(student=user, course=course)


def test_classmates_can_chat_privately_and_teacher_cannot_see_it(world):
    enroll(world["bob"], world["course"])
    classmates = as_(world["alice"]).get("/api/v1/conversations/classmates/").data
    assert classmates["allowed"] and [p["email"] for p in classmates["people"]] == ["b@example.com"]

    chat = as_(world["alice"]).post("/api/v1/conversations/start/", {"student_id": world["bob"].id}).data
    assert chat["kind"] == "peer" and chat["title"] == "Bob"
    again = as_(world["bob"]).post("/api/v1/conversations/start/", {"student_id": world["alice"].id}).data
    assert again["id"] == chat["id"]

    send(world["alice"], chat["id"], text="سلام")
    assert next(c for c in conversations(world["bob"]) if c["kind"] == "peer")["unread"] == 1
    assert all(c["kind"] != "peer" for c in conversations(world["teacher"]))
    assert as_(world["teacher"]).get(f"/api/v1/conversations/{chat['id']}/messages/").status_code == 404

    # the teacher switches the feature off: peer chats disappear
    world["teacher"].instructor_profile.allow_peer_chat = False
    world["teacher"].instructor_profile.save()
    assert all(c["kind"] != "peer" for c in conversations(world["alice"]))
    assert as_(world["alice"]).post("/api/v1/conversations/start/", {"student_id": world["bob"].id}).status_code == 403


def test_custom_group_members_settings_pin_and_delete(world):
    teacher = as_(world["teacher"])
    group = teacher.post(
        "/api/v1/conversations/groups/",
        {"title": "پروژه‌ی نهایی", "member_ids": [world["alice"].id]},
        format="json",
    ).data
    assert group["kind"] == "custom" and group["title"] == "پروژه‌ی نهایی" and group["members"] == 2 and group["can_manage"]

    assert any(c["id"] == group["id"] for c in conversations(world["alice"]))
    assert all(c["id"] != group["id"] for c in conversations(world["bob"]))
    assert not next(c for c in conversations(world["alice"]) if c["id"] == group["id"])["can_manage"]

    teacher.post(f"/api/v1/conversations/{group['id']}/members/", {"user_ids": [world["bob"].id]}, format="json")
    names = [m["name"] for m in teacher.get(f"/api/v1/conversations/{group['id']}/members/").data]
    assert names == ["مهدی", "Alice", "Bob"]

    msg = send(world["teacher"], group["id"], text="قوانین گروه").data
    pinned = teacher.post(f"/api/v1/conversations/{group['id']}/pin/", {"message_id": msg["id"]}, format="json").data
    assert pinned["pinned"]["text"] == "قوانین گروه"

    teacher.patch(f"/api/v1/conversations/{group['id']}/settings/", {"announcement_only": True, "title": "اطلاعیه‌ها"}, format="json")
    assert send(world["alice"], group["id"], text="سوال").status_code == 403
    alice_view = next(c for c in conversations(world["alice"]) if c["id"] == group["id"])
    assert alice_view["title"] == "اطلاعیه‌ها" and not alice_view["can_send"]

    assert as_(world["alice"]).patch(f"/api/v1/conversations/{group['id']}/settings/", {"title": "x"}, format="json").status_code == 403
    teacher.delete(f"/api/v1/conversations/{group['id']}/members/{world['bob'].id}/")
    assert all(c["id"] != group["id"] for c in conversations(world["bob"]))

    assert teacher.delete(f"/api/v1/conversations/{group['id']}/").status_code == 204
    course_group = next(c for c in conversations(world["teacher"]) if c["kind"] == "course")
    assert teacher.delete(f"/api/v1/conversations/{course_group['id']}/").status_code == 400


def test_course_group_announcement_only(world):
    teacher = as_(world["teacher"])
    group = next(c for c in conversations(world["teacher"]) if c["kind"] == "course")
    teacher.patch(f"/api/v1/conversations/{group['id']}/settings/", {"announcement_only": True}, format="json")
    assert send(world["alice"], group["id"], text="hi").status_code == 403
    assert send(world["teacher"], group["id"], text="اطلاعیه").status_code == 201


def test_reply_seen_count_viewers_and_delete(world):
    enroll(world["bob"], world["course"])
    group = next(c for c in conversations(world["teacher"]) if c["kind"] == "course")
    gid = group["id"]
    question = send(world["alice"], gid, text="جلسه‌ی بعد کی است؟").data
    answer = send(world["teacher"], gid, text="پنجشنبه", reply_to=question["id"]).data
    assert answer["reply_to"]["id"] == question["id"] and answer["reply_to"]["sender_name"] == "Alice"

    # nobody else has seen the teacher's answer yet
    mine = as_(world["teacher"]).get(f"/api/v1/conversations/{gid}/messages/").data["messages"]
    assert next(m for m in mine if m["id"] == answer["id"])["seen_count"] == 0
    as_(world["alice"]).post(f"/api/v1/conversations/{gid}/read/", {})
    as_(world["bob"]).post(f"/api/v1/conversations/{gid}/read/", {})
    as_(world["developer"]).post(f"/api/v1/conversations/{gid}/read/", {})  # doesn't count
    mine = as_(world["teacher"]).get(f"/api/v1/conversations/{gid}/messages/").data["messages"]
    assert next(m for m in mine if m["id"] == answer["id"])["seen_count"] == 2
    assert next(m for m in mine if m["id"] == question["id"])["seen_count"] is None  # not mine

    viewers = as_(world["teacher"]).get(f"/api/v1/conversations/{gid}/messages/{answer['id']}/viewers/").data
    assert sorted(v["name"] for v in viewers) == ["Alice", "Bob"] and all(v["read_at"] for v in viewers)
    # a student can't list viewers of someone else's message
    assert as_(world["bob"]).get(f"/api/v1/conversations/{gid}/messages/{answer['id']}/viewers/").status_code == 403

    # bob can't delete alice's message; alice can; the teacher can delete any in a group
    assert as_(world["bob"]).delete(f"/api/v1/conversations/{gid}/messages/{question['id']}/").status_code == 403
    bob_msg = send(world["bob"], gid, text="سلام").data
    assert as_(world["teacher"]).delete(f"/api/v1/conversations/{gid}/messages/{bob_msg['id']}/").status_code == 204
    assert as_(world["alice"]).delete(f"/api/v1/conversations/{gid}/messages/{question['id']}/").status_code == 204
    remaining = as_(world["teacher"]).get(f"/api/v1/conversations/{gid}/messages/").data["messages"]
    assert [m["id"] for m in remaining] == [answer["id"]] and remaining[0]["reply_to"] is None


def test_students_create_private_groups_with_classmates(world):
    enroll(world["bob"], world["course"])
    outsider = User.objects.create_user(email="o@example.com", password="x", first_name="Out")
    group = as_(world["alice"]).post(
        "/api/v1/conversations/groups/",
        {"title": "گروه مطالعه", "member_ids": [world["bob"].id, outsider.id]},
        format="json",
    ).data
    assert group["kind"] == "custom" and group["can_manage"] and group["subtitle"] == "گروه هم‌کلاسی‌ها"
    names = sorted(m["name"] for m in as_(world["alice"]).get(f"/api/v1/conversations/{group['id']}/members/").data)
    assert names == ["Alice", "Bob"]  # the non-classmate was dropped; no teacher in a student group
    assert group["members"] == 2

    # bob is in it but doesn't manage it; the teacher can't see it
    bob_view = next(c for c in conversations(world["bob"]) if c["id"] == group["id"])
    assert not bob_view["can_manage"]
    assert all(c["id"] != group["id"] for c in conversations(world["teacher"]))
    assert as_(world["teacher"]).get(f"/api/v1/conversations/{group['id']}/messages/").status_code == 404

    # the creator can switch it to announcement-only; then bob can't post
    as_(world["alice"]).patch(f"/api/v1/conversations/{group['id']}/settings/", {"announcement_only": True}, format="json")
    assert send(world["bob"], group["id"], text="x").status_code == 403
    assert send(world["alice"], group["id"], text="x").status_code == 201

    # switching classmate chat off hides student groups and blocks new ones
    world["teacher"].instructor_profile.allow_peer_chat = False
    world["teacher"].instructor_profile.save()
    assert all(c["id"] != group["id"] for c in conversations(world["alice"]))
    assert as_(world["alice"]).post("/api/v1/conversations/groups/", {"title": "y"}, format="json").status_code == 403
