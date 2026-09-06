from celery import shared_task

from apps.videos.services.transcoder import transcode_video_asset


@shared_task(bind=True, max_retries=2)
def transcode_video_asset_task(self, video_asset_id: int):
    transcode_video_asset(video_asset_id)
