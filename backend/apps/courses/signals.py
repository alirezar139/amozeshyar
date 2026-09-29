from django.db.models.signals import post_delete
from django.dispatch import receiver

from .models import LessonFile


@receiver(post_delete, sender=LessonFile)
def delete_lesson_file_from_storage(sender, instance: LessonFile, **kwargs):
    if instance.file:
        instance.file.delete(save=False)
