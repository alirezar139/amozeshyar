"""Smallest real files of each kind, for upload tests.

Uploads are checked by their bytes (apps/common/file_types.py), so a test
can't send b"%PDF" and call it a PDF any more. These headers are what
libmagic recognises on both its Linux (CI, production) and Windows builds.
"""
from io import BytesIO

from django.core.files.uploadedfile import SimpleUploadedFile
from PIL import Image

PDF = b"%PDF-1.4\n1 0 obj<<>>endobj\ntrailer<<>>\n%%EOF\n"
# EBML header with DocType "webm" (what Chrome's and Firefox's MediaRecorder write).
WEBM = bytes.fromhex("1A45DFA39F4286810142F7810142F2810442F38108428284") + b"webm" + bytes.fromhex("4287810242858102") + b"\0" * 64
# ID3v2 tag followed by an MPEG-1 Layer III frame header.
MP3 = b"ID3\x03\x00\x00\x00\x00\x00\x00" + bytes.fromhex("FFFB9064") + b"\0" * 400
WAV = (
    b"RIFF" + (36).to_bytes(4, "little") + b"WAVEfmt " + (16).to_bytes(4, "little")
    + bytes.fromhex("0100010044AC00008858010002001000") + b"data" + (0).to_bytes(4, "little")
)
HTML = b"<html><body><script>alert(document.domain)</script></body></html>"
SVG = b'<svg xmlns="http://www.w3.org/2000/svg"><script>alert(1)</script></svg>'


def image(fmt: str = "PNG") -> bytes:
    buffer = BytesIO()
    Image.new("RGB", (8, 8), (21, 126, 108)).save(buffer, fmt)
    return buffer.getvalue()


def upload(name: str, content: bytes, content_type: str = "application/octet-stream") -> SimpleUploadedFile:
    """`content_type` is what the (possibly lying) client claims."""
    return SimpleUploadedFile(name, content, content_type=content_type)
