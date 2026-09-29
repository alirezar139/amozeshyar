from drf_spectacular.utils import extend_schema
from rest_framework import generics, permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView

from django.db.models import Sum
from django.utils import timezone

from apps.courses.models import ClassSession, Lesson, LessonFile

from .models import Enrollment, LessonProgress, WishlistItem
from .serializers import (
    ContinueLearningSerializer,
    DashboardSummarySerializer,
    EnrollmentSerializer,
    LessonProgressResponseSerializer,
    LessonProgressUpdateSerializer,
    WishlistItemSerializer,
)


class MyEnrollmentsViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = EnrollmentSerializer
    permission_classes = (permissions.IsAuthenticated,)

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):
            return Enrollment.objects.none()
        return Enrollment.objects.filter(student=self.request.user, is_active=True).select_related("course__category")

    @extend_schema(responses=DashboardSummarySerializer)
    @action(detail=False, methods=["get"])
    def summary(self, request):
        """Everything the student dashboard's home shows, in one call."""
        user = request.user
        course_ids = list(
            Enrollment.objects.filter(student=user, is_active=True).values_list("course_id", flat=True)
        )
        progress = LessonProgress.objects.filter(student=user, lesson__course_id__in=course_ids)
        next_session = (
            ClassSession.objects.filter(course_id__in=course_ids, starts_at__gte=timezone.now())
            .select_related("course")
            .order_by("starts_at")
            .first()
        )
        recent_files = (
            LessonFile.objects.filter(lesson__course_id__in=course_ids)
            .select_related("lesson__course")
            .order_by("-created_at")[:5]
        )
        data = {
            "courses": len(course_ids),
            "completed_lessons": progress.filter(completed=True).count(),
            "total_lessons": Lesson.objects.filter(course_id__in=course_ids).count(),
            "watched_minutes": (progress.aggregate(s=Sum("position_seconds"))["s"] or 0) // 60,
            "next_session": next_session and {
                "id": next_session.id,
                "title": next_session.title,
                "course_title": next_session.course.title,
                "starts_at": next_session.starts_at,
                "is_online": next_session.is_online,
            },
            "recent_files": [
                {
                    "id": f.id,
                    "title": f.title or f.original_name,
                    "extension": f.extension,
                    "size_bytes": f.size_bytes,
                    "lesson_title": f.lesson.title,
                    "course_title": f.lesson.course.title,
                    "course_slug": f.lesson.course.slug,
                    "created_at": f.created_at,
                }
                for f in recent_files
            ],
        }
        return Response(DashboardSummarySerializer(data).data)

    @extend_schema(responses=ContinueLearningSerializer)
    @action(detail=False, methods=["get"], url_path="continue")
    def continue_learning(self, request):
        """Where should the "continue learning" button on the dashboard go?

        Prefers the most recently watched, not-yet-finished lesson; falls
        back to the first lesson of the most recently purchased course for
        a student who hasn't started watching anything yet.
        """
        progress = (
            LessonProgress.objects.filter(student=request.user, completed=False, position_seconds__gt=0)
            .select_related("lesson__course")
            .order_by("-updated_at")
            .first()
        )
        if progress:
            lesson = progress.lesson
            return Response(
                ContinueLearningSerializer(
                    {
                        "course_slug": lesson.course.slug,
                        "course_title": lesson.course.title,
                        "lesson_id": lesson.id,
                        "lesson_title": lesson.title,
                        "position_seconds": progress.position_seconds,
                    }
                ).data
            )

        enrollment = (
            Enrollment.objects.filter(student=request.user, is_active=True)
            .select_related("course")
            .order_by("-access_granted_at")
            .first()
        )
        if enrollment:
            first_lesson = enrollment.course.lessons.order_by("order").first()
            if first_lesson:
                return Response(
                    ContinueLearningSerializer(
                        {
                            "course_slug": enrollment.course.slug,
                            "course_title": enrollment.course.title,
                            "lesson_id": first_lesson.id,
                            "lesson_title": first_lesson.title,
                            "position_seconds": 0,
                        }
                    ).data
                )
        return Response(None)


class WishlistViewSet(viewsets.ModelViewSet):
    serializer_class = WishlistItemSerializer
    permission_classes = (permissions.IsAuthenticated,)
    http_method_names = ("get", "post", "delete", "head", "options")

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):
            return WishlistItem.objects.none()
        return WishlistItem.objects.filter(student=self.request.user)


class LessonProgressView(APIView):
    """Upserts how far the current student got into one lesson's video.

    Called periodically by the player, not on every timeupdate tick — see
    the frontend player component for the throttling. No enrollment check
    here: the manifest/preview endpoints already gate which video URL a
    given user can actually fetch, so a progress row for a lesson someone
    can't play is harmless.
    """

    permission_classes = (permissions.IsAuthenticated,)

    @extend_schema(request=LessonProgressUpdateSerializer, responses=LessonProgressResponseSerializer)
    def post(self, request):
        payload = LessonProgressUpdateSerializer(data=request.data)
        payload.is_valid(raise_exception=True)

        lesson = generics.get_object_or_404(Lesson, id=payload.validated_data["lesson_id"])
        position_seconds = payload.validated_data["position_seconds"]
        explicit = payload.validated_data["completed"]
        existing = LessonProgress.objects.filter(student=request.user, lesson=lesson).first()
        if explicit is not None:
            completed = explicit
            position_seconds = existing.position_seconds if existing and not position_seconds else position_seconds
        else:
            video = getattr(lesson, "video_asset", None)
            watched_enough = bool(
                video and video.duration_seconds and position_seconds >= video.duration_seconds * 0.9
            )
            # Watching a finished lesson again from the start shouldn't un-finish it.
            completed = watched_enough or bool(existing and existing.completed)

        obj, _ = LessonProgress.objects.update_or_create(
            student=request.user,
            lesson=lesson,
            defaults={"position_seconds": position_seconds, "completed": completed},
        )
        return Response(LessonProgressResponseSerializer(obj).data, status=status.HTTP_200_OK)
