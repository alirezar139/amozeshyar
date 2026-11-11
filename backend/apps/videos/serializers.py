import secrets

from django.db import transaction
from rest_framework import serializers

from apps.common.validators import validate_video_file

from .models import VideoAsset


class VideoUploadSerializer(serializers.ModelSerializer):
    file = serializers.FileField(write_only=True, validators=[validate_video_file])

    class Meta:
        model = VideoAsset
        fields = ("id", "lesson", "file", "status", "duration_seconds")
        read_only_fields = ("id", "status", "duration_seconds")
        # Uploading for a lesson that already has a video replaces it (create() below). Without
        # this, DRF's automatic one-to-one uniqueness check refused every replacement with a 400,
        # after the whole file had been uploaded. The database constraint still holds.
        extra_kwargs = {"lesson": {"validators": []}}

    def create(self, validated_data):
        file_obj = validated_data.pop("file")
        lesson = validated_data["lesson"]
        # A folder per upload, so a replacement never lands on (and is then deleted with) the
        # previous video's key, even with the same file name.
        storage_key = f"lessons/{lesson.id}/{secrets.token_hex(6)}/original_{file_obj.name}"

        from django.core.files.storage import default_storage

        # Stored first: if this fails, the lesson keeps its current video untouched.
        saved_key = default_storage.save(storage_key, file_obj)

        with transaction.atomic():
            # Re-uploading replaces the lesson's video (the relation is one-to-one); the old one's
            # files are removed once this commits (signals.py).
            VideoAsset.objects.filter(lesson=lesson).delete()
            video_asset = VideoAsset.objects.create(
                lesson=lesson,
                original_filename=file_obj.name,
                storage_key=saved_key,
                file_size_bytes=file_obj.size,
                status=VideoAsset.Status.UPLOADING,
            )

        from .tasks import enqueue_transcode

        transaction.on_commit(lambda: enqueue_transcode(video_asset.id))
        return video_asset


class SignedUrlResponseSerializer(serializers.Serializer):
    url = serializers.URLField()


class VideoStatusSerializer(serializers.ModelSerializer):
    class Meta:
        model = VideoAsset
        fields = ("id", "lesson", "status", "duration_seconds", "processing_error")
