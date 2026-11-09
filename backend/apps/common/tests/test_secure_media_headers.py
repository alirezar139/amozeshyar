"""`manage.py secure_media_headers` re-types files stored before the fix, without touching their bytes."""
from io import BytesIO, StringIO

import pytest
from django.core.management import call_command
from django.core.management.base import CommandError

from apps.common.storage import SharedSessionS3Storage

from . import file_samples


class FakeS3Client:
    def __init__(self, objects):
        self.objects = objects  # key -> {"body": bytes, "ContentType": ..., ...}
        self.copies = []

    def get_paginator(self, _operation):
        client = self

        class _Paginator:
            def paginate(self, Bucket, Prefix=""):  # noqa: N803
                yield {"Contents": [{"Key": k, "Size": len(v["body"])} for k, v in client.objects.items() if k.startswith(Prefix)]}

        return _Paginator()

    def head_object(self, Bucket, Key):  # noqa: N803
        return {k: v for k, v in self.objects[Key].items() if k != "body"}

    def get_object(self, Bucket, Key, Range):  # noqa: N803
        end = int(Range.split("-")[1]) + 1
        return {"Body": BytesIO(self.objects[Key]["body"][:end])}

    def copy_object(self, **kwargs):
        self.copies.append(kwargs)


@pytest.fixture
def client(settings, monkeypatch):
    settings.STORAGES = {**settings.STORAGES, "default": {"BACKEND": "apps.common.storage.SharedSessionS3Storage"}}
    fake = FakeS3Client({
        "chat/evil.pdf": {"body": file_samples.HTML, "ContentType": "text/html", "Metadata": {}},
        "chat/photo.png": {"body": file_samples.image(), "ContentType": "image/png", "Metadata": {}},
        "lesson_files/a.pdf": {"body": file_samples.PDF, "ContentType": "application/pdf", "Metadata": {"x": "1"}},
    })

    class _Bucket:
        class meta:  # noqa: N801
            client = fake

    monkeypatch.setattr(SharedSessionS3Storage, "bucket", property(lambda self: _Bucket()))
    return fake


def test_dry_run_reports_but_changes_nothing(client):
    out = StringIO()
    call_command("secure_media_headers", stdout=out)
    assert client.copies == []
    assert "chat/evil.pdf: text/html" in out.getvalue() and "2 would fix" in out.getvalue()
    assert "chat/photo.png" not in out.getvalue()


def test_apply_rewrites_only_the_headers_of_wrong_objects(client):
    call_command("secure_media_headers", "--apply", stdout=StringIO())
    by_key = {c["Key"]: c for c in client.copies}
    assert set(by_key) == {"chat/evil.pdf", "lesson_files/a.pdf"}
    evil = by_key["chat/evil.pdf"]
    assert evil["CopySource"] == {"Bucket": evil["Bucket"], "Key": "chat/evil.pdf"}  # in place
    assert evil["MetadataDirective"] == "REPLACE"
    assert evil["ContentType"] == "application/octet-stream" and evil["ContentDisposition"] == "attachment"
    assert by_key["lesson_files/a.pdf"]["Metadata"] == {"x": "1"}  # user metadata kept


def test_prefix_limits_the_scan(client):
    call_command("secure_media_headers", "--apply", "--prefix", "lesson_files/", stdout=StringIO())
    assert [c["Key"] for c in client.copies] == ["lesson_files/a.pdf"]


def test_refuses_to_run_without_s3_storage():
    with pytest.raises(CommandError):
        call_command("secure_media_headers")
