from django.apps import AppConfig, apps
from django.db.models.signals import post_delete, post_save

# Everything the cached public pages are built from (see public_cache.py).
PUBLIC_MODELS = (
    "courses.Course",
    "courses.Category",
    "courses.Lesson",
    "courses.LessonFile",
    "videos.VideoAsset",
    "instructors.InstructorProfile",
    "accounts.User",  # the owner's name and photo
)


class CommonConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.common"

    def ready(self):
        from .public_cache import invalidate

        for label in PUBLIC_MODELS:
            model = apps.get_model(label)
            post_save.connect(invalidate, sender=model, dispatch_uid=f"public-cache-save-{label}")
            post_delete.connect(invalidate, sender=model, dispatch_uid=f"public-cache-delete-{label}")
