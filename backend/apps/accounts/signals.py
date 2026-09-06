from django.db.models.signals import post_save
from django.dispatch import receiver

from .models import User


@receiver(post_save, sender=User)
def create_instructor_profile_on_role_change(sender, instance: User, created, **kwargs):
    """Auto-create a blank, pending-review InstructorProfile the first time a user becomes an instructor.

    Avoids a manual admin step and guarantees every instructor has exactly
    one profile row before they try to create a course.
    """
    if instance.role != User.Role.INSTRUCTOR:
        return
    from apps.instructors.models import InstructorProfile

    InstructorProfile.objects.get_or_create(user=instance)
