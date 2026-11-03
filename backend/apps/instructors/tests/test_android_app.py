from io import StringIO
from urllib.parse import unquote

import pytest
from django.core.files.storage import default_storage
from django.core.management import CommandError, call_command
from rest_framework.test import APIClient

from apps.accounts.models import User
from apps.instructors import android_app
from apps.instructors.models import InstructorProfile

pytestmark = pytest.mark.django_db

FAKE_APK = b"PK\x03\x04 not really an apk, but zip-shaped"


@pytest.fixture(autouse=True)
def clean_storage():
    # The in-memory test storage outlives a single test.
    yield
    default_storage.delete(android_app.APK_KEY)


@pytest.fixture
def site():
    teacher = User.objects.create_user(email="t@example.com", password="x", role=User.Role.ADMIN)
    return InstructorProfile.objects.create(user=teacher, is_site_owner=True, site_name="آموزش‌یار")


@pytest.fixture
def apk_file(tmp_path):
    path = tmp_path / "app-release.apk"
    path.write_bytes(FAKE_APK)
    return path


def site_info():
    return APIClient().get("/api/v1/site/").data


def test_nothing_to_download_until_published(site):
    assert site_info()["android_app"] is False
    assert APIClient().get("/api/v1/site/android.apk").status_code == 404


def test_published_app_is_offered_and_downloads_under_the_site_name(site, apk_file):
    call_command("publish_android_app", str(apk_file), stdout=StringIO())

    assert default_storage.open(android_app.APK_KEY).read() == FAKE_APK
    response = APIClient().get("/api/v1/site/android.apk")
    assert response.status_code == 302
    assert android_app.APK_KEY in response["Location"]
    # The Content-Disposition filename is itself percent-encoded inside the query string.
    assert "آموزش‌یار.apk" in unquote(unquote(response["Location"]))


def test_republishing_replaces_the_previous_build(site, apk_file):
    call_command("publish_android_app", str(apk_file), stdout=StringIO())
    apk_file.write_bytes(FAKE_APK + b" v2")

    call_command("publish_android_app", str(apk_file), stdout=StringIO())

    assert default_storage.open(android_app.APK_KEY).read().endswith(b" v2")


def test_rejects_a_file_that_isnt_an_apk(site, tmp_path):
    bogus = tmp_path / "notes.txt"
    bogus.write_text("hello")

    with pytest.raises(CommandError):
        call_command("publish_android_app", str(bogus), stdout=StringIO())
    assert not android_app.is_published()
