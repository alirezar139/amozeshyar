from drf_spectacular.utils import extend_schema
from rest_framework import generics, permissions, status
from rest_framework.exceptions import PermissionDenied
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView

from apps.accounts.authentication import UploadJWTAuthentication
from apps.accounts.permissions import IsAdminRole

from .models import VideoAsset, WatchSession
from .serializers import SignedUrlResponseSerializer, VideoUploadSerializer


def _client_ip(request) -> str | None:
    return request.META.get("REMOTE_ADDR")


class VideoUploadView(generics.CreateAPIView):
    """Admin (the site's instructor) uploads a video for a lesson slot."""

    serializer_class = VideoUploadSerializer
    permission_classes = (permissions.IsAuthenticated, IsAdminRole)
    authentication_classes = (UploadJWTAuthentication,)


class VideoDeleteView(generics.DestroyAPIView):
    """Admin: remove a lesson's video (the lesson itself stays)."""

    permission_classes = (permissions.IsAuthenticated, IsAdminRole)
    queryset = VideoAsset.objects.all()
    lookup_url_kwarg = "video_id"


class PreviewStreamView(APIView):
    """Public endpoint: always resolves to the physically-truncated preview clip, never the full file.

    No enrollment check needed here by design — the object it points at
    simply does not contain more than the configured preview length.
    """

    permission_classes = (permissions.AllowAny,)
    throttle_classes = (ScopedRateThrottle,)
    throttle_scope = "video_manifest"
    serializer_class = SignedUrlResponseSerializer

    @extend_schema(responses=SignedUrlResponseSerializer)
    def get(self, request, video_id):
        video = generics.get_object_or_404(VideoAsset, id=video_id, status=VideoAsset.Status.READY)
        if not video.preview_clip_key:
            return Response({"detail": "Preview not available yet."}, status=status.HTTP_404_NOT_FOUND)

        from .services.signing import get_presigned_url

        WatchSession.issue(video, request.user, has_full_access=False, client_ip=_client_ip(request))
        return Response({"url": get_presigned_url(video.preview_clip_key)})


class ManifestView(APIView):
    """Re-checks enrollment on every call before handing out a signed HLS URL.

    Re-checking here (rather than trusting a token minted once at page
    load) means a refund or access revocation takes effect on the very
    next manifest fetch, not just at the next login. AllowAny (not
    IsAuthenticated) on purpose: a lesson can be `is_free_preview`, and an
    anonymous visitor must be able to watch that one in full without
    logging in first — the frontend only ever requests this endpoint (vs.
    PreviewStreamView) when it already believes access is allowed, so the
    real gate is the enrolled-or-free-preview check below, not login.
    """

    permission_classes = (permissions.AllowAny,)
    throttle_classes = (ScopedRateThrottle,)
    throttle_scope = "video_manifest"
    serializer_class = SignedUrlResponseSerializer

    @extend_schema(responses=SignedUrlResponseSerializer)
    def get(self, request, video_id):
        video = generics.get_object_or_404(VideoAsset, id=video_id, status=VideoAsset.Status.READY)
        course = video.lesson.course

        is_enrolled = False
        if request.user.is_authenticated:
            from apps.enrollments.models import Enrollment

            is_enrolled = Enrollment.objects.filter(
                student=request.user, course=course, is_active=True
            ).exists()
        if not (is_enrolled or video.lesson.is_free_preview):
            raise PermissionDenied("Enrollment required to watch the full video.")
        if not video.hls_master_key:
            return Response({"detail": "Video not processed yet."}, status=status.HTTP_404_NOT_FOUND)

        from .services.signing import get_presigned_url

        WatchSession.issue(video, request.user, has_full_access=True, client_ip=_client_ip(request))
        return Response({"url": get_presigned_url(video.hls_master_key)})


class VideoDownloadView(APIView):
    """Admin-only: streams the *original* uploaded file with a forced download disposition.

    Deliberately separate from the playback endpoints above — students
    never reach this, regardless of enrollment status.
    """

    permission_classes = (permissions.IsAuthenticated, IsAdminRole)
    serializer_class = SignedUrlResponseSerializer

    @extend_schema(responses=SignedUrlResponseSerializer)
    def get(self, request, video_id):
        video = generics.get_object_or_404(VideoAsset, id=video_id)

        from .services.signing import get_download_url

        url = get_download_url(video.storage_key, video.original_filename)
        return Response({"url": url})
