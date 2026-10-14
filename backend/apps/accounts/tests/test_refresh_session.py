"""The refresh-cookie session (docs/adr/0002-jwt-cookie-auth.md).

Each of these guards a way the session broke, or could break, without any
visible error: a cookie scoped too narrowly for SSR, a rotated token that
still works, a deactivated account that keeps refreshing.
"""
import pytest
from django.core.cache import cache
from rest_framework.test import APIClient

from apps.accounts import views
from apps.accounts.models import User

pytestmark = pytest.mark.django_db

PASSWORD = "a-long-test-password"


@pytest.fixture(autouse=True)
def no_puzzle_and_fresh_throttles(monkeypatch):
    monkeypatch.setattr(views.captcha, "consume_pass", lambda token: True)
    cache.clear()
    yield
    cache.clear()


@pytest.fixture
def student():
    return User.objects.create_user(email="s@example.com", password=PASSWORD)


def login(client, email="s@example.com"):
    return client.post("/api/v1/auth/login/", {"email": email, "password": PASSWORD, "captcha_pass_token": "x"}, format="json")


def refresh_with(raw_token):
    client = APIClient()
    client.cookies[views.REFRESH_COOKIE_NAME] = raw_token
    return client.post("/api/v1/auth/refresh/")


def test_login_puts_refresh_only_in_an_http_only_site_wide_cookie(student):
    response = login(APIClient())

    assert response.status_code == 200
    assert "access" in response.data and "refresh" not in response.data
    cookie = response.cookies[views.REFRESH_COOKIE_NAME]
    assert cookie["httponly"] is True
    assert cookie["samesite"] == "Lax"
    assert cookie["path"] == "/"  # SSR forwards it from page requests, not only /api/v1/auth/


def test_refresh_rotates_and_the_old_token_stops_working(student):
    first = login(APIClient()).cookies[views.REFRESH_COOKIE_NAME].value

    rotated = refresh_with(first)
    assert rotated.status_code == 200 and rotated.data["access"]
    second = rotated.cookies[views.REFRESH_COOKIE_NAME].value
    assert second != first

    assert refresh_with(first).status_code == 401  # replaying the old cookie is refused
    assert refresh_with(second).status_code == 200  # the new one carries on


def test_new_access_token_authenticates(student):
    access = refresh_with(login(APIClient()).cookies[views.REFRESH_COOKIE_NAME].value).data["access"]

    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {access}")
    assert client.get("/api/v1/auth/me/").data["email"] == "s@example.com"


def test_logout_revokes_the_refresh_cookie(student):
    client = APIClient()
    token = login(client).cookies[views.REFRESH_COOKIE_NAME].value

    client.cookies[views.REFRESH_COOKIE_NAME] = token
    assert client.post("/api/v1/auth/logout/").status_code == 205
    assert refresh_with(token).status_code == 401


def test_deactivated_account_cannot_refresh(student):
    token = login(APIClient()).cookies[views.REFRESH_COOKIE_NAME].value
    student.is_active = False
    student.save(update_fields=["is_active"])

    response = refresh_with(token)

    assert response.status_code == 401
    assert views.REFRESH_COOKIE_NAME not in response.cookies or not response.cookies[views.REFRESH_COOKIE_NAME].value


def test_deleted_account_gets_401_not_a_server_error(student):
    token = login(APIClient()).cookies[views.REFRESH_COOKIE_NAME].value
    student.delete()

    assert refresh_with(token).status_code == 401


def test_garbage_and_missing_cookies_are_401():
    assert refresh_with("not-a-jwt").status_code == 401
    assert APIClient().post("/api/v1/auth/refresh/").status_code == 401
