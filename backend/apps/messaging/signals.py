from django.db.models.signals import post_delete
from django.dispatch import receiver

from .models import Message


@receiver(post_delete, sender=Message)
def delete_attachment_from_storage(sender, instance: Message, **kwargs):
    if instance.attachment:
        instance.attachment.delete(save=False)
