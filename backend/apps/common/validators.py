import magic
from django.core.exceptions import ValidationError

ALLOWED_VIDEO_MIME_TYPES = {
    "video/mp4",
    "video/quicktime",
    "video/x-matroska",
    "video/webm",
}
ALLOWED_IMAGE_MIME_TYPES = {"image/jpeg", "image/png", "image/webp"}
MAX_VIDEO_SIZE_BYTES = 5 * 1024 * 1024 * 1024  # 5 GB
MAX_IMAGE_SIZE_BYTES = 5 * 1024 * 1024  # 5 MB


def _sniff_mime_type(file_obj) -> str:
    """Read the real magic-byte MIME type instead of trusting the filename/extension."""
    position = file_obj.tell()
    file_obj.seek(0)
    mime_type = magic.from_buffer(file_obj.read(2048), mime=True)
    file_obj.seek(position)
    return mime_type


def validate_video_file(file_obj):
    if file_obj.size > MAX_VIDEO_SIZE_BYTES:
        raise ValidationError("Video file exceeds the maximum allowed size.")
    mime_type = _sniff_mime_type(file_obj)
    if mime_type not in ALLOWED_VIDEO_MIME_TYPES:
        raise ValidationError(f"Unsupported video format detected: {mime_type}.")


def validate_image_file(file_obj):
    if file_obj.size > MAX_IMAGE_SIZE_BYTES:
        raise ValidationError("Image file exceeds the maximum allowed size.")
    mime_type = _sniff_mime_type(file_obj)
    if mime_type not in ALLOWED_IMAGE_MIME_TYPES:
        raise ValidationError(f"Unsupported image format detected: {mime_type}.")
