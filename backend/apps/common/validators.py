from django.core.exceptions import ValidationError

from .file_types import check_file_type, sniff_mime_type

ALLOWED_VIDEO_MIME_TYPES = {
    "video/mp4",
    "video/quicktime",
    "video/x-matroska",
    "video/webm",
}
ALLOWED_IMAGE_MIME_TYPES = {"image/jpeg", "image/png", "image/webp"}
MAX_VIDEO_SIZE_BYTES = 2 * 1024 * 1024 * 1024  # 2 GB, same as nginx client_max_body_size for uploads
MAX_IMAGE_SIZE_BYTES = 5 * 1024 * 1024  # 5 MB


def validate_video_file(file_obj):
    if file_obj.size > MAX_VIDEO_SIZE_BYTES:
        raise ValidationError("حجم ویدیو بیشتر از ۲ گیگابایت است.")
    mime_type = sniff_mime_type(file_obj)
    if mime_type not in ALLOWED_VIDEO_MIME_TYPES:
        raise ValidationError(f"این فایل ویدیوی قابل‌قبول نیست ({mime_type}). فرمت‌های مجاز: MP4، MOV، MKV، WEBM.")


def validate_image_file(file_obj):
    if file_obj.size > MAX_IMAGE_SIZE_BYTES:
        raise ValidationError("حجم تصویر بیشتر از ۵ مگابایت است.")
    mime_type = sniff_mime_type(file_obj)
    if mime_type not in ALLOWED_IMAGE_MIME_TYPES:
        raise ValidationError(f"این فایل تصویر قابل‌قبول نیست ({mime_type}). فرمت‌های مجاز: JPG، PNG، WEBP.")


# Course files (handouts, exercises, source code...), also what may be sent
# as a file in chat. Stored as forced downloads (see file_types.storage_headers);
# html, svg and other formats a browser would run are refused outright, and
# the content must really be what the extension says.
ALLOWED_COURSE_FILE_EXTENSIONS = {
    "pdf", "doc", "docx", "ppt", "pptx", "xls", "xlsx", "csv", "txt", "md", "rtf", "odt", "ods", "odp",
    "zip", "rar", "7z", "tar", "gz",
    "png", "jpg", "jpeg", "webp", "gif",
    "mp3", "m4a", "wav", "ogg",
    "py", "ipynb", "java", "c", "cpp", "h", "cs", "go", "rs", "php", "rb", "sql", "json", "xml", "yaml", "yml",
    "psd", "ai", "fig", "sketch", "dwg",
}
MAX_COURSE_FILE_SIZE_BYTES = 500 * 1024 * 1024  # 500 MB


def validate_course_file(file_obj):
    if file_obj.size > MAX_COURSE_FILE_SIZE_BYTES:
        raise ValidationError("حجم فایل بیشتر از ۵۰۰ مگابایت است.")
    check_file_type(file_obj, ALLOWED_COURSE_FILE_EXTENSIONS)
