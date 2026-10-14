import pytest
from rest_framework.test import APIClient

from apps.common import views

pytestmark = pytest.mark.django_db


def test_health_is_public_and_ok_when_everything_answers():
    response = APIClient().get("/api/v1/health/")

    assert response.status_code == 200
    assert response.data == {"status": "ok", "checks": {"database": "ok", "cache": "ok"}}


def test_health_names_the_failing_check_without_leaking_the_error(monkeypatch):
    def broken():
        raise ConnectionError("redis://secret-host:6379 refused")

    monkeypatch.setitem(views.CHECKS, "cache", broken)

    response = APIClient().get("/api/v1/health/")

    assert response.status_code == 503
    assert response.data["checks"] == {"database": "ok", "cache": "failed"}
    assert "secret-host" not in response.content.decode()
