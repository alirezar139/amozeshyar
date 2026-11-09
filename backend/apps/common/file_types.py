"""What a stored file really is, decided by the server from its bytes.

Two things depend on this, and neither may trust the client:

* **Accepting an upload.** The extension must be one we allow, and the
  file's magic bytes must match what that extension claims. A "notes.pdf"
  that is really HTML is refused, whatever Content-Type the browser sent.
* **Serving it.** User files are served from the site's own host (signed
  MinIO links under /modaresyar-media/). If a browser were ever told a
  file is text/html, it would run it as a page of this site, with access
  to the user's session. So the Content-Type stored with the object comes
  from `storage_headers()` below: images, audio and video keep their real
  type so <img>, <audio> and the player work; everything else is stored
  as application/octet-stream with Content-Disposition: attachment, so
  opening it only ever downloads it.
"""
import magic
from django.core.exceptions import ValidationError

SNIFF_BYTES = 2048

# Formats a browser executes as a document or script. Refused for every
# upload, whatever the extension (libmagic names SVG differently per build).
EXECUTABLE_MIME_TYPES = {
    "text/html",
    "application/xhtml+xml",
    "image/svg",
    "image/svg+xml",
    "text/javascript",
    "application/javascript",
    "application/x-javascript",
    "text/ecmascript",
    "text/xsl",
}

_ZIP = {"application/zip", "application/x-zip-compressed"}
_OLE = {"application/CDFV2", "application/x-ole-storage", "application/vnd.ms-office"}

# Extension -> MIME types libmagic may report for a genuine file of that kind.
# Several entries list more than one: libmagic versions (Linux in CI and
# production, the Windows build in dev) and encoders name the same format
# differently, and Office/OpenDocument files are often seen as plain zip.
BINARY_EXTENSION_MIME_TYPES = {
    # images
    "jpg": {"image/jpeg"},
    "jpeg": {"image/jpeg"},
    "png": {"image/png"},
    "webp": {"image/webp"},
    "gif": {"image/gif"},
    # audio (voice notes come from MediaRecorder: webm/ogg on Chrome and Firefox, mp4 on Safari)
    "mp3": {"audio/mpeg", "audio/mp3"},
    "wav": {"audio/x-wav", "audio/wav", "audio/vnd.wave"},
    "ogg": {"audio/ogg", "application/ogg", "video/ogg"},
    "oga": {"audio/ogg", "application/ogg"},
    "webm": {"video/webm", "audio/webm"},
    "m4a": {"audio/x-m4a", "audio/mp4", "video/mp4"},
    "mp4": {"video/mp4", "audio/mp4", "audio/x-m4a"},
    "aac": {"audio/x-hx-aac-adts", "audio/aac", "audio/x-aac"},
    # documents
    "pdf": {"application/pdf"},
    "doc": {"application/msword", *_OLE},
    "xls": {"application/vnd.ms-excel", *_OLE},
    "ppt": {"application/vnd.ms-powerpoint", *_OLE},
    "docx": {"application/vnd.openxmlformats-officedocument.wordprocessingml.document", *_ZIP},
    "xlsx": {"application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", *_ZIP},
    "pptx": {"application/vnd.openxmlformats-officedocument.presentationml.presentation", *_ZIP},
    "odt": {"application/vnd.oasis.opendocument.text", *_ZIP},
    "ods": {"application/vnd.oasis.opendocument.spreadsheet", *_ZIP},
    "odp": {"application/vnd.oasis.opendocument.presentation", *_ZIP},
    "rtf": {"text/rtf", "application/rtf"},
    # archives
    "zip": _ZIP,
    "rar": {"application/x-rar", "application/vnd.rar", "application/x-rar-compressed"},
    "7z": {"application/x-7z-compressed"},
    "tar": {"application/x-tar"},
    "gz": {"application/gzip", "application/x-gzip"},
    # design files: libmagic often has no name for these, hence octet-stream
    "psd": {"image/vnd.adobe.photoshop", "application/x-photoshop", "application/octet-stream"},
    "ai": {"application/pdf", "application/postscript", "application/illustrator"},
    "fig": {"application/octet-stream", *_ZIP},
    "sketch": {"application/octet-stream", *_ZIP},
    "dwg": {"image/vnd.dwg", "application/acad", "application/x-dwg", "application/octet-stream"},
}

# Plain-text formats: any text/* type (libmagic guesses text/x-python,
# text/x-c...) except the executable ones, plus a few application/* names.
TEXT_EXTENSIONS = {
    "txt", "md", "csv", "json", "yaml", "yml", "sql", "ipynb", "xml",
    "py", "java", "c", "cpp", "h", "cs", "go", "rs", "php", "rb",
}
_TEXT_EXTRA_MIME_TYPES = {"application/json", "application/csv", "application/x-empty", "inode/x-empty"}
# XML is only acceptable as itself; elsewhere text/xml may be XHTML in disguise.
_XML_MIME_TYPES = {"text/xml", "application/xml"}

# What may be stored with its real type and shown inline. Nothing here can run script.
INLINE_MIME_TYPES = {
    "image/jpeg", "image/png", "image/webp", "image/gif",
    "audio/mpeg", "audio/mp3", "audio/x-wav", "audio/wav", "audio/vnd.wave", "audio/ogg", "audio/webm",
    "audio/x-m4a", "audio/mp4", "audio/x-hx-aac-adts", "audio/aac", "audio/x-aac", "application/ogg",
    "video/mp4", "video/webm", "video/ogg", "video/quicktime", "video/x-matroska",
}
# Files the server itself writes (HLS output, the Android app). libmagic
# can't name them reliably, so their type follows the key the server chose.
SERVER_FILE_TYPES = {
    ".m3u8": ("application/vnd.apple.mpegurl", False),
    ".ts": ("video/mp2t", False),
    ".apk": ("application/vnd.android.package-archive", True),
}

DOWNLOAD_MIME_TYPE = "application/octet-stream"


def extension_of(name: str | None) -> str:
    name = (name or "").rsplit("/", 1)[-1].lower()
    return name.rsplit(".", 1)[-1] if "." in name else ""


def sniff_mime_type(file_obj) -> str:
    """The MIME type libmagic reads from the first bytes; the file position is left where it was."""
    position = file_obj.tell()
    file_obj.seek(0)
    head = file_obj.read(SNIFF_BYTES)
    file_obj.seek(position)
    if isinstance(head, str):
        head = head.encode("utf-8", "replace")
    return magic.from_buffer(head, mime=True)


def _content_matches_extension(extension: str, mime_type: str) -> bool:
    if extension in BINARY_EXTENSION_MIME_TYPES:
        return mime_type in BINARY_EXTENSION_MIME_TYPES[extension]
    if extension in TEXT_EXTENSIONS:
        if mime_type in _XML_MIME_TYPES:
            return extension == "xml"
        return mime_type.startswith("text/") or mime_type in _TEXT_EXTRA_MIME_TYPES
    return False


def check_file_type(file_obj, allowed_extensions) -> str:
    """Refuse `file_obj` unless its extension is allowed and its bytes match it.

    Returns the sniffed MIME type. Raises django's ValidationError (DRF
    serializers turn it into a 400 on the field).
    """
    extension = extension_of(getattr(file_obj, "name", ""))
    if extension not in allowed_extensions:
        raise ValidationError(f"این نوع فایل پشتیبانی نمی‌شود: .{extension or '?'}")
    mime_type = sniff_mime_type(file_obj)
    if mime_type in EXECUTABLE_MIME_TYPES or not _content_matches_extension(extension, mime_type):
        raise ValidationError(f"محتوای فایل با پسوند .{extension} آن هم‌خوانی ندارد.")
    return mime_type


def storage_headers(name: str, file_obj=None) -> dict:
    """ContentType (and, for downloads, ContentDisposition) to store with object `name`.

    Decided only from the bytes and the server-chosen key, never from the
    client's Content-Type header.
    """
    for suffix, (content_type, download) in SERVER_FILE_TYPES.items():
        if name.lower().endswith(suffix):
            return {"ContentType": content_type, **({"ContentDisposition": "attachment"} if download else {})}
    mime_type = ""
    if file_obj is not None and hasattr(file_obj, "seek"):
        try:
            mime_type = sniff_mime_type(file_obj)
        except (OSError, ValueError):
            mime_type = ""
    if mime_type in INLINE_MIME_TYPES:
        return {"ContentType": mime_type}
    return {"ContentType": DOWNLOAD_MIME_TYPE, "ContentDisposition": "attachment"}
