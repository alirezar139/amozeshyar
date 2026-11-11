from django.db import transaction
from django.db.models.signals import post_delete
from django.dispatch import receiver

from .models import VideoAsset
from .services.cleanup import video_prefixes


@receiver(post_delete, sender=VideoAsset)
def delete_video_files_from_storage(sender, instance: VideoAsset, **kwargs):
    """Deleting or replacing a lesson's video also removes its original, HLS and preview files.

    After commit (a rolled-back delete keeps them), in the background (HLS can be a thousand
    segment files), and only what no remaining video uses (see services/cleanup.py).
    """
    prefixes = video_prefixes(instance.storage_key)
    if prefixes:
        from .tasks import delete_video_files

        transaction.on_commit(lambda: delete_video_files.delay(prefixes))
