import pytest
from django.core.cache import cache
from rest_framework.test import APIClient

pytestmark = pytest.mark.django_db


@pytest.fixture(autouse=True)
def fresh_throttle_counters():
    cache.clear()
    yield
    cache.clear()


@pytest.mark.parametrize("url", ["/api/v1/auth/login/", "/api/v1/auth/register/"])
def test_password_endpoints_are_capped_per_ip(url):
    client = APIClient()
    codes = [client.post(url, {}, format="json").status_code for _ in range(11)]

    assert 429 not in codes[:10]
    assert codes[10] == 429


def test_spoofed_forwarded_for_does_not_reset_the_cap(settings):
    settings.REST_FRAMEWORK = {**settings.REST_FRAMEWORK, "NUM_PROXIES": 1}
    client = APIClient()
    codes = [
        client.post(
            "/api/v1/auth/login/", {}, format="json",
            HTTP_X_FORWARDED_FOR=f"10.0.0.{i}, 203.0.113.7",
        ).status_code
        for i in range(11)
    ]

    assert codes[10] == 429
