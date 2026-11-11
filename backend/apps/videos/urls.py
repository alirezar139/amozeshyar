from django.urls import path

from . import views

urlpatterns = [
    path("videos/upload/", views.VideoUploadView.as_view(), name="video-upload"),
    path("videos/<int:video_id>/", views.VideoDeleteView.as_view(), name="video-delete"),
    path("videos/<int:video_id>/retry/", views.VideoRetryView.as_view(), name="video-retry"),
    path("videos/<int:video_id>/preview/", views.PreviewStreamView.as_view(), name="video-preview"),
    path("videos/<int:video_id>/manifest/", views.ManifestView.as_view(), name="video-manifest"),
    path("videos/<int:video_id>/playlist.m3u8", views.playlist_view, name="video-playlist"),
    path("videos/<int:video_id>/download/", views.VideoDownloadView.as_view(), name="video-download"),
]
