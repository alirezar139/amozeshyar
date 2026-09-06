from rest_framework import serializers

from apps.common.validators import validate_video_file

from .models import VideoAsset


class VideoUploadSerializer(serializers.ModelSerializer):
    file = serializers.FileField(write_only=True, validators=[validate_video_file])

    class Meta:
        model = VideoAsset
        fields = ("id", "lesson", "file", "status", "duration_seconds")
        read_only_fields = ("id", "status", "duration_seconds")

    def create(self, validated_data):
        file_obj = validated_data.pop("file")
        lesson = validated_data["lesson"]
        storage_key = f"lessons/{lesson.id}/original_{file_obj.name}"

        from django.core.files.storage import default_storage

        saved_key = default_storage.save(storage_key, file_obj)

        video_asset = VideoAsset.objects.create(
            lesson=lesson,
            original_filename=file_obj.name,
            storage_key=saved_key,
            file_size_bytes=file_obj.size,
            status=VideoAsset.Status.UPLOADING,
        )

        from .tasks import transcode_video_asset_task

        transcode_video_asset_task.delay(video_asset.id)
        return video_asset


class SignedUrlResponseSerializer(serializers.Serializer):
    url = serializers.URLField()


class VideoStatusSerializer(serializers.ModelSerializer):
    class Meta:
        model = VideoAsset
        fields = ("id", "lesson", "status", "duration_seconds", "processing_error")
