"""Idle chat polls are answered from the change counter, without the full queries."""
import pytest
from django.core.cache import cache
from django.db import connection
from django.test.utils import CaptureQueriesContext
from rest_framework.test import APIClient

from apps.accounts.models import User
from apps.courses.models import Category, Course
from apps.enrollments.models import Enrollment
from apps.instructors.models import InstructorProfile

# on_commit callbacks (where the counter is bumped) only run when transactions really commit.
pytestmark = pytest.mark.django_db(transaction=True)


@pytest.fixture(autouse=True)
def fresh_cache():
    cache.clear()
    yield
    cache.clear()


@pytest.fixture
def chat():
    teacher = User.objects.create_user(email="t@example.com", password="x", role=User.Role.ADMIN, first_name="مهدی")
    InstructorProfile.objects.create(user=teacher, is_site_owner=True)
    category = Category.objects.create(name="c", slug="c")
    course = Course.objects.create(instructor=teacher.instructor_profile, category=category, title="Python", status=Course.Status.PUBLISHED)
    alice = User.objects.create_user(email="a@example.com", password="x", first_name="Alice")
    Enrollment.objects.create(student=alice, course=course)
    clients = {}
    for name, user in (("teacher", teacher), ("alice", alice)):
        clients[name] = APIClient()
        clients[name].force_authenticate(user)
    group = next(c for c in clients["alice"].get("/api/v1/conversations/").data if c["kind"] == "course")
    return clients, group["id"]


def url(cid):
    return f"/api/v1/conversations/{cid}/messages/"


def first_load(client, cid):
    data = client.get(url(cid)).data
    last_id = data["messages"][-1]["id"] if data["messages"] else 0
    return data["version"], data["server_time"], last_id


def poll(client, cid, after, version, since=None):
    params = {"after": after, "v": version}
    if since:
        params["since"] = since
    return client.get(url(cid), params).data


def test_idle_poll_is_unchanged_and_costs_almost_nothing(chat):
    clients, cid = chat
    version, _, last_id = first_load(clients["alice"], cid)

    with CaptureQueriesContext(connection) as queries:
        data = poll(clients["alice"], cid, last_id, version)

    assert data == {"unchanged": True, "version": version}
    assert len(queries) <= 4  # just "may this user see this chat?", not the message/marker/row queries


def test_a_new_message_changes_the_version_and_arrives(chat):
    clients, cid = chat
    version, _, last_id = first_load(clients["alice"], cid)

    clients["teacher"].post(url(cid), {"text": "سلام"}, format="json")
    data = poll(clients["alice"], cid, last_id, version)

    assert "unchanged" not in data
    assert [m["text"] for m in data["messages"]] == ["سلام"]
    assert data["version"] != version


def test_reactions_deletions_and_read_receipts_wake_the_poll(chat):
    clients, cid = chat
    message = clients["teacher"].post(url(cid), {"text": "hi"}, format="json").data
    version, since, last_id = first_load(clients["alice"], cid)

    clients["alice"].post(f"{url(cid)}{message['id']}/react/", {"emoji": "👍"}, format="json")
    data = poll(clients["teacher"], cid, last_id, version, since)
    assert "unchanged" not in data
    assert data["changed"][0]["reactions"]
    version, since = data["version"], data["server_time"]

    clients["alice"].post(f"/api/v1/conversations/{cid}/read/", {"message_id": message["id"]}, format="json")
    data = poll(clients["teacher"], cid, last_id, version, since)
    assert "unchanged" not in data and data["others_last_read"] == message["id"]
    version, since = data["version"], data["server_time"]

    clients["teacher"].delete(f"{url(cid)}{message['id']}/")
    data = poll(clients["alice"], cid, last_id, version, since)
    assert data["changed"][0]["is_deleted"] is True


def test_a_lost_counter_just_means_one_full_poll(chat):
    clients, cid = chat
    version, _, last_id = first_load(clients["alice"], cid)
    cache.clear()

    data = poll(clients["alice"], cid, last_id, version)

    assert "unchanged" not in data
    assert poll(clients["alice"], cid, last_id, data["version"]) == {"unchanged": True, "version": data["version"]}


def test_unchanged_answer_still_checks_access(chat):
    clients, cid = chat
    version, _, last_id = first_load(clients["alice"], cid)
    Enrollment.objects.filter(student__email="a@example.com").update(is_active=False)

    response = clients["alice"].get(url(cid), {"after": last_id, "v": version})

    assert response.status_code == 404
