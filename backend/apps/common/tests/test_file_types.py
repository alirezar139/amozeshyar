"""The server, not the client, decides what an uploaded file is and how it's served (SEC-01)."""
import io
import zipfile

import pytest
from django.core.exceptions import ValidationError

from apps.common import file_types
from apps.common.file_types import check_file_type, storage_headers
from apps.common.storage import SharedSessionS3Storage
from apps.common.validators import ALLOWED_COURSE_FILE_EXTENSIONS

from . import file_samples

ATTACHMENT = {"ContentType": "application/octet-stream", "ContentDisposition": "attachment"}


def docx() -> bytes:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as z:
        z.writestr("[Content_Types].xml", "<Types/>")
        z.writestr("word/document.xml", "<w:document/>")
    return buffer.getvalue()


@pytest.mark.parametrize(
    ("name", "content"),
    [
        ("notes.pdf", file_samples.HTML),  # HTML disguised as a PDF
        ("notes.txt", file_samples.HTML),
        ("photo.png", file_samples.HTML),
        ("icon.png", file_samples.SVG),
        ("data.txt", file_samples.SVG),
        ("page.txt", b'<?xml version="1.0"?><html xmlns="http://www.w3.org/1999/xhtml"><script>alert(1)</script></html>'),
        ("photo.pdf", file_samples.image()),  # a real image under a document's name
        ("voice.webm", file_samples.PDF),
        ("archive.zip", file_samples.PDF),
    ],
)
def test_content_that_does_not_match_its_extension_is_refused(name, content):
    with pytest.raises(ValidationError):
        check_file_type(file_samples.upload(name, content, "application/pdf"), ALLOWED_COURSE_FILE_EXTENSIONS | {"webm"})


@pytest.mark.parametrize("name", ["page.html", "icon.svg", "run.js", "setup.exe", "noextension"])
def test_extensions_outside_the_list_are_refused(name):
    with pytest.raises(ValidationError):
        check_file_type(file_samples.upload(name, b"hello"), ALLOWED_COURSE_FILE_EXTENSIONS)


@pytest.mark.parametrize(
    ("name", "content"),
    [
        ("جزوه.pdf", file_samples.PDF),
        ("a.png", file_samples.image("PNG")),
        ("a.jpg", file_samples.image("JPEG")),
        ("a.webp", file_samples.image("WEBP")),
        ("a.gif", file_samples.image("GIF")),
        ("a.mp3", file_samples.MP3),
        ("a.wav", file_samples.WAV),
        ("a.docx", docx()),
        ("a.zip", docx()),
        ("notes.txt", "سلام، این جزوه است.".encode()),
        ("main.py", b"def main():\n    return 42\n"),
        ("data.json", b'{"a": [1, 2]}'),
        ("table.csv", b"a,b\n1,2\n"),
        ("config.xml", b'<?xml version="1.0"?><config><a>1</a></config>'),
    ],
)
def test_genuine_files_are_accepted(name, content):
    check_file_type(file_samples.upload(name, content, "text/html"), ALLOWED_COURSE_FILE_EXTENSIONS)


def test_voice_formats_are_accepted():
    check_file_type(file_samples.upload("voice.webm", file_samples.WEBM), {"webm"})


def test_every_allowed_course_extension_has_a_content_rule():
    known = set(file_types.BINARY_EXTENSION_MIME_TYPES) | file_types.TEXT_EXTENSIONS
    assert ALLOWED_COURSE_FILE_EXTENSIONS <= known


def test_checking_leaves_the_file_position_alone():
    upload = file_samples.upload("a.pdf", file_samples.PDF)
    upload.seek(5)
    check_file_type(upload, {"pdf"})
    assert upload.tell() == 5


# ---------- how a file is stored, and therefore served ----------

@pytest.mark.parametrize(
    ("name", "content", "expected"),
    [
        ("chat/a.png", file_samples.image(), {"ContentType": "image/png"}),
        ("chat/a.mp3", file_samples.MP3, {"ContentType": "audio/mpeg"}),
        ("chat/voice.webm", file_samples.WEBM, {"ContentType": "video/webm"}),
        ("chat/a.pdf", file_samples.PDF, ATTACHMENT),
        ("chat/a.pdf", file_samples.HTML, ATTACHMENT),
        ("chat/a.png", file_samples.SVG, ATTACHMENT),
        ("chat/a.txt", b"plain", ATTACHMENT),
        ("lessons/1/original_a/hls/master.m3u8", b"#EXTM3U\n", {"ContentType": "application/vnd.apple.mpegurl"}),
        ("lessons/1/original_a/hls/master0.ts", b"\x47" + b"\0" * 187, {"ContentType": "video/mp2t"}),
        ("apps/android/app.apk", docx(), {"ContentType": "application/vnd.android.package-archive", "ContentDisposition": "attachment"}),
    ],
)
def test_storage_headers_come_from_the_bytes(name, content, expected):
    assert storage_headers(name, io.BytesIO(content)) == expected


def test_s3_storage_ignores_the_content_type_the_client_sent():
    """The audit's proof of concept: before the fix this returned {'ContentType': 'text/html'}."""
    storage = SharedSessionS3Storage()
    html_as_pdf = file_samples.upload("notes.pdf", file_samples.HTML, "text/html")
    assert storage._get_write_parameters("chat/notes.pdf", html_as_pdf) == {**ATTACHMENT, "ACL": "private"}

    png_claimed_html = file_samples.upload("a.png", file_samples.image(), "text/html")
    assert storage._get_write_parameters("chat/a.png", png_claimed_html) == {"ContentType": "image/png", "ACL": "private"}


def test_s3_storage_drops_the_gzip_encoding_guessed_from_the_name():
    params = SharedSessionS3Storage()._get_write_parameters("lesson_files/code.tar.gz", io.BytesIO(b"\x1f\x8b\x08\0"))
    assert "ContentEncoding" not in params and params["ContentDisposition"] == "attachment"
