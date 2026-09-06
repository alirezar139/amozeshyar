from django.urls import path

from . import views

urlpatterns = [
    path("videos/upload/", views.VideoUploadView.as_view(), name="video-upload"),
    path("videos/<int:video_id>/preview/", views.PreviewStreamView.as_view(), name="video-preview"),
    path("videos/<int:video_id>/manifest/", views.ManifestView.as_view(), name="video-manifest"),
    path("videos/<int:video_id>/download/", views.VideoDownloadView.as_view(), name="video-download"),
]
