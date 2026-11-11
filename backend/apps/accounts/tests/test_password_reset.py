"""Forgotten password: a signed, time-limited, single-use link sent to the account's own email
(or phone, when an SMS provider is set up) (AUTH-01)."""
import logging
import re
from datetime import datetime, timedelta
from unittest import mock

import pytest
from django.contrib.auth.tokens import default_token_generator
from django.core import mail
from django.core.cache import cache
from rest_framework.test import APIClient
from rest_framework_simplejwt.token_blacklist.models import BlacklistedToken
from rest_framework_simplejwt.tokens import RefreshToken

from apps.accounts.models import User

pytestmark = pytest.mark.django_db(transaction=True)  # links are sent after commit

REQUEST = "/api/v1/auth/password-reset/"
CONFIRM = "/api/v1/auth/password-reset/confirm/"
NEW_PASSWORD = "a-much-better-passphrase-42"


@pytest.fixture(autouse=True)
def fresh_throttles():
    cache.clear()
    yield
    cache.clear()


@pytest.fixture
def user():
    return User.objects.create_user(email="sara@example.com", password="old-password-123", first_name="سارا")


def ask(email):
    return APIClient().post(REQUEST, {"email": email}, format="json")


def link_parts():
    (message,) = mail.outbox
    match = re.search(r"https://site\.test/auth/reset-password#uid=([\w-]+)&token=([\w-]+)", message.body)
    assert match, message.body
    return match.group(1), match.group(2)


def confirm(uid, token, password=NEW_PASSWORD):
    return APIClient().post(CONFIRM, {"uid": uid, "token": token, "password": password}, format="json")


def test_known_email_gets_a_link_and_the_answer_reveals_nothing(user):
    known, unknown = ask("Sara@Example.com"), ask("nobody@example.com")

    assert known.status_code == unknown.status_code == 200
    assert known.data == unknown.data  # no way to tell whether an account exists
    assert len(mail.outbox) == 1 and mail.outbox[0].to == ["sara@example.com"]
    assert "۳۰ دقیقه" in mail.outbox[0].body or "30 دقیقه" in mail.outbox[0].body


def test_inactive_accounts_get_nothing(user):
    user.is_active = False
    user.save()
    assert ask("sara@example.com").status_code == 200
    assert mail.outbox == []


def test_the_link_sets_a_new_password_and_signs_out_everywhere(user):
    refresh = RefreshToken.for_user(user)
    ask(user.email)
    uid, token = link_parts()

    response = confirm(uid, token)

    assert response.status_code == 200
    user.refresh_from_db()
    assert user.check_password(NEW_PASSWORD)
    assert BlacklistedToken.objects.filter(token__jti=refresh["jti"]).exists()
    assert any("عوض شد" in m.subject for m in mail.outbox)  # "your password was changed" notice


def test_a_link_works_only_once(user):
    ask(user.email)
    uid, token = link_parts()
    assert confirm(uid, token).status_code == 200

    again = confirm(uid, token, password="yet-another-passphrase-7")

    assert again.status_code == 400
    user.refresh_from_db()
    assert user.check_password(NEW_PASSWORD)


def test_a_link_expires(user, settings):
    ask(user.email)
    uid, token = link_parts()
    later = datetime.now() + timedelta(seconds=settings.PASSWORD_RESET_TIMEOUT + 60)

    with mock.patch.object(type(default_token_generator), "_now", return_value=later):
        response = confirm(uid, token)

    assert response.status_code == 400
    user.refresh_from_db()
    assert user.check_password("old-password-123")


@pytest.mark.parametrize(("uid", "token"), [("bad", "bad"), ("", ""), ("MQ", "x-y")])
def test_forged_links_are_refused(user, uid, token):
    assert confirm(uid, token).status_code == 400


def test_a_weak_new_password_is_refused_and_the_link_still_works(user):
    ask(user.email)
    uid, token = link_parts()

    weak = confirm(uid, token, password="123")

    assert weak.status_code == 400 and "password" in weak.data
    assert confirm(uid, token).status_code == 200


def test_requests_are_rate_limited(user):
    codes = [ask(user.email).status_code for _ in range(7)]
    assert codes[:5] == [200] * 5 and 429 in codes[5:]


def test_the_link_never_reaches_the_logs_or_the_in_app_chat(user, caplog):
    from apps.messaging.models import Message

    with caplog.at_level(logging.DEBUG):
        ask(user.email)
    uid, token = link_parts()
    assert all(token not in r.getMessage() for r in caplog.records)
    assert not Message.objects.filter(text__contains=token).exists()


def test_sms_is_used_when_a_provider_is_configured(user, settings):
    sent = []

    class Provider:
        def send(self, phone, text):
            sent.append((phone, text))

    user.phone_number = "09121234567"
    user.save()
    settings.SMS_PROVIDER = f"{__name__}.SmsProviderForTests"
    with mock.patch(f"{__name__}.SmsProviderForTests", Provider, create=True):
        ask(user.email)

    assert sent and sent[0][0] == "09121234567" and "reset-password" in sent[0][1]
