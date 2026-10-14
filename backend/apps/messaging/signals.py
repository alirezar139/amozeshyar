from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver

from apps.enrollments.models import Enrollment

from . import versions
from .models import Conversation, ConversationMember, ConversationRead, Message, MessageReaction


@receiver(post_delete, sender=Message)
def delete_attachment_from_storage(sender, instance: Message, **kwargs):
    if instance.attachment:
        instance.attachment.delete(save=False)


# ---- change counter for chat polls (see versions.py) ----

@receiver([post_save, post_delete], sender=Message)
@receiver([post_save, post_delete], sender=ConversationRead)
@receiver([post_save, post_delete], sender=ConversationMember)
def bump_conversation_of(sender, instance, **kwargs):
    versions.bump(instance.conversation_id)


@receiver([post_save, post_delete], sender=MessageReaction)
def bump_on_reaction(sender, instance: MessageReaction, **kwargs):
    versions.bump(Message.objects.filter(pk=instance.message_id).values_list("conversation_id", flat=True).first())


@receiver(post_save, sender=Conversation)
def bump_on_settings(sender, instance: Conversation, created, **kwargs):
    if not created:
        versions.bump(instance.pk)


@receiver([post_save, post_delete], sender=Enrollment)
def bump_course_group(sender, instance: Enrollment, **kwargs):
    # A course group's member count follows its enrollments.
    for conversation_id in Conversation.objects.filter(kind=Conversation.Kind.COURSE, course_id=instance.course_id).values_list("pk", flat=True):
        versions.bump(conversation_id)
