from django.db.models.signals import post_delete
from django.dispatch import receiver

from .models import AnswerFile, QuestionMedia


@receiver(post_delete, sender=QuestionMedia)
@receiver(post_delete, sender=AnswerFile)
def delete_exam_file_from_storage(sender, instance, **kwargs):
    if instance.file:
        instance.file.delete(save=False)
