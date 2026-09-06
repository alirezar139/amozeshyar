from django.contrib import admin

from .models import PreviewPolicy, VideoAsset, WatchSession


@admin.register(VideoAsset)
class VideoAssetAdmin(admin.ModelAdmin):
    list_display = ("lesson", "status", "duration_seconds", "created_at")
    list_filter = ("status",)
    readonly_fields = ("storage_key", "hls_master_key", "preview_clip_key", "checksum_sha256")


@admin.register(PreviewPolicy)
class PreviewPolicyAdmin(admin.ModelAdmin):
    def has_add_permission(self, request):
        return not PreviewPolicy.objects.exists()


@admin.register(WatchSession)
class WatchSessionAdmin(admin.ModelAdmin):
    list_display = ("video", "user", "has_full_access", "expires_at", "created_at")
    list_filter = ("has_full_access",)
    readonly_fields = [f.name for f in WatchSession._meta.fields]
