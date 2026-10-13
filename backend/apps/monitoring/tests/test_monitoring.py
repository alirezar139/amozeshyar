import pytest
from django.core.cache import cache
from django.test import override_settings
from rest_framework.test import APIClient

from apps.accounts.models import User
from apps.monitoring.models import ErrorEvent, SupportReport

pytestmark = pytest.mark.django_db


@pytest.fixture(autouse=True)
def fresh_cache():
    cache.clear()


def client_for(user=None):
    client = APIClient()
    if user:
        client.force_authenticate(user)
    return client


@pytest.fixture
def instructor():
    return User.objects.create_user(email="i@example.com", password="x", role=User.Role.ADMIN)


@pytest.fixture
def developer():
    return User.objects.create_user(
        email="d@example.com", password="x", role=User.Role.ADMIN, is_staff=True, is_superuser=True,
    )


def test_api_error_responses_are_recorded_with_the_server_message(instructor):
    client_for(instructor).post("/api/v1/courses/manage/", {}, format="json")

    event = ErrorEvent.objects.get()
    assert event.source == "api" and event.status == 400 and event.user == instructor
    assert "category" in event.detail


def test_expired_tokens_and_throttling_are_not_recorded():
    client_for().get("/api/v1/auth/me/")

    assert not ErrorEvent.objects.exists()


@override_settings(DEBUG=False)
def test_browser_errors_need_a_signed_in_user_in_production(instructor):
    body = {"level": "error", "kind": "js", "message": "boom", "url": "/admin"}

    assert client_for().post("/api/v1/monitoring/client-log/", body, format="json").status_code == 401
    assert client_for(instructor).post("/api/v1/monitoring/client-log/", body, format="json").status_code == 204
    assert ErrorEvent.objects.get().source == "browser"


def test_only_the_developer_sees_the_live_log(instructor, developer):
    ErrorEvent.objects.create(source="api", level="warning", message="first")
    newer = ErrorEvent.objects.create(source="api", level="warning", message="second")

    res = client_for(developer).get(f"/api/v1/monitoring/events/?after={newer.id - 1}")
    assert [e["message"] for e in res.data] == ["second"]
    assert client_for(instructor).get("/api/v1/monitoring/events/").status_code == 403


def test_support_report_attaches_the_instructors_own_recent_errors(instructor, developer):
    mine = ErrorEvent.objects.create(source="api", level="warning", message="mine", user=instructor)
    ErrorEvent.objects.create(source="api", level="warning", message="someone else", user=developer)

    res = client_for(instructor).post(
        "/api/v1/support/reports/",
        {"message": " دکمه ذخیره کار نمی‌کند ", "page_url": "/admin/courses", "resolved": True,
         "browser_events": [{"level": "error", "message": "x", "junk": "dropped"}]},
        format="json",
    )

    assert res.status_code == 201
    report = SupportReport.objects.get()
    assert report.message == "دکمه ذخیره کار نمی‌کند" and report.resolved is False
    assert list(report.events.all()) == [mine]
    assert "junk" not in report.browser_events[0]

    inbox = client_for(developer).get("/api/v1/monitoring/reports/?resolved=false")
    assert inbox.data["results"][0]["events"][0]["message"] == "mine"
    assert client_for(developer).patch(f"/api/v1/monitoring/reports/{report.id}/", {"resolved": True}, format="json").status_code == 200
    report.refresh_from_db()
    assert report.resolved and report.resolved_at


def test_students_cannot_send_support_reports():
    student = User.objects.create_user(email="s@example.com", password="x")

    assert client_for(student).post("/api/v1/support/reports/", {"message": "x"}, format="json").status_code == 403


def test_me_tells_the_frontend_who_the_developer_is(instructor, developer):
    assert client_for(instructor).get("/api/v1/auth/me/").data["is_developer"] is False
    assert client_for(developer).get("/api/v1/auth/me/").data["is_developer"] is True
