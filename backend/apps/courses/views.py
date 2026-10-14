from django.db import transaction
from django.db.models import Count, Max, Q
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import generics, permissions, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.response import Response

from apps.accounts.authentication import UploadJWTAuthentication
from apps.accounts.permissions import IsAdminRole
from apps.common import public_cache

from .filters import CourseFilter
from .models import Category, ClassSession, Course, Lesson, LessonFile
from .serializers import (
    CategorySerializer,
    ClassSessionSerializer,
    CourseManageSerializer,
    LessonFileSerializer,
    LessonSerializer,
    PublicCourseDetailSerializer,
    PublicCourseListSerializer,
    StudentScheduleSerializer,
)


class CategoryViewSet(viewsets.ModelViewSet):
    """Anyone can list categories; only the site admin creates, renames or deletes them.

    `course_count` only counts published courses, so an empty or all-pending category still
    shows up here (the instructor needs it when creating a course) while the homepage grid
    filters those out client-side to avoid dead-end links."""

    serializer_class = CategorySerializer

    def list(self, request, *args, **kwargs):
        # Same answer for everyone, and loaded by every homepage visit.
        return public_cache.cached_response(request, lambda: super(CategoryViewSet, self).list(request, *args, **kwargs).data)

    def get_permissions(self):
        if self.request.method in permissions.SAFE_METHODS:
            return [permissions.AllowAny()]
        return [permissions.IsAuthenticated(), IsAdminRole()]

    def get_queryset(self):
        return Category.objects.annotate(
            course_count=Count("courses", filter=Q(courses__status=Course.Status.PUBLISHED))
        )

    def perform_destroy(self, instance):
        if instance.courses.exists():
            raise ValidationError({"detail": "این دسته‌بندی دوره دارد؛ اول دوره‌هایش را به دسته‌ی دیگری منتقل کنید."})
        instance.delete()


class PublicCourseViewSet(viewsets.ReadOnlyModelViewSet):
    """Public catalog/detail — only ever exposes published courses."""

    permission_classes = (permissions.AllowAny,)
    lookup_field = "slug"
    filterset_class = CourseFilter
    queryset = Course.objects.filter(status=Course.Status.PUBLISHED).select_related("category")

    def get_serializer_class(self):
        if self.action == "retrieve":
            return PublicCourseDetailSerializer
        return PublicCourseListSerializer

    # Anonymous visitors all get the same catalog and course pages, so those are
    # cached; a signed-in student's answer carries their own enrollment and progress.
    def list(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            return super().list(request, *args, **kwargs)
        return public_cache.cached_response(request, lambda: super(PublicCourseViewSet, self).list(request, *args, **kwargs).data)

    def retrieve(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            return super().retrieve(request, *args, **kwargs)
        return public_cache.cached_response(request, lambda: super(PublicCourseViewSet, self).retrieve(request, *args, **kwargs).data)


class CourseManageViewSet(viewsets.ModelViewSet):
    """Admin (the site's instructor): every course in any status — create,
    edit, and publish/unpublish by patching `status`. No approval step: the
    instructor owns the site, so what they publish goes live."""

    serializer_class = CourseManageSerializer
    permission_classes = (permissions.IsAuthenticated, IsAdminRole)
    http_method_names = ("get", "post", "patch", "head", "options")
    queryset = Course.objects.all().select_related("category")


class LessonViewSet(viewsets.ModelViewSet):
    """Admin CRUD for lessons. `?course=<id>` scopes to one course; not
    paginated, since a course's lesson list is always shown whole."""

    serializer_class = LessonSerializer
    permission_classes = (permissions.IsAuthenticated, IsAdminRole)
    pagination_class = None

    def get_queryset(self):
        lessons = Lesson.objects.select_related("video_asset").prefetch_related("files").order_by("course", "order")
        course_id = self.request.query_params.get("course")
        return lessons.filter(course_id=course_id) if course_id else lessons

    def perform_create(self, serializer):
        course = serializer.validated_data["course"]
        order = serializer.validated_data.get("order")
        if not order or course.lessons.filter(order=order).exists():
            order = (course.lessons.aggregate(m=Max("order"))["m"] or 0) + 1
        serializer.save(order=order)

    @action(detail=True, methods=["post"])
    def move(self, request, pk=None):
        """Swap this lesson with its neighbour: body {"direction": "up" | "down"}."""
        lesson = self.get_object()
        siblings = Lesson.objects.filter(course=lesson.course)
        if request.data.get("direction") == "up":
            neighbour = siblings.filter(order__lt=lesson.order).order_by("-order").first()
        else:
            neighbour = siblings.filter(order__gt=lesson.order).order_by("order").first()
        if neighbour:
            with transaction.atomic():
                # Park one row outside the range first: (course, order) is unique.
                parked = (siblings.aggregate(m=Max("order"))["m"] or 0) + 1
                a, b = lesson.order, neighbour.order
                Lesson.objects.filter(pk=lesson.pk).update(order=parked)
                Lesson.objects.filter(pk=neighbour.pk).update(order=a)
                Lesson.objects.filter(pk=lesson.pk).update(order=b)
                public_cache.invalidate()  # .update() sends no post_save
        return Response(self.get_serializer(self.get_queryset(), many=True).data)


class LessonFileViewSet(viewsets.ModelViewSet):
    """Admin: upload, rename and delete lesson files (`?lesson=` / `?course=`).
    `download` is also open to enrolled students — see its docstring."""

    serializer_class = LessonFileSerializer
    permission_classes = (permissions.IsAuthenticated, IsAdminRole)
    http_method_names = ("get", "post", "patch", "delete", "head", "options")
    pagination_class = None

    def get_authenticators(self):
        # Uploads can outlive the access token; see UploadJWTAuthentication.
        if self.request and self.request.method == "POST":
            return [UploadJWTAuthentication()]
        return super().get_authenticators()

    def get_queryset(self):
        files = LessonFile.objects.select_related("lesson__course")
        params = self.request.query_params
        if params.get("lesson"):
            files = files.filter(lesson_id=params["lesson"])
        if params.get("course"):
            files = files.filter(lesson__course_id=params["course"])
        return files

    @action(detail=True, methods=["get"], permission_classes=[permissions.IsAuthenticated])
    def download(self, request, pk=None):
        """A short-lived signed download link — only for the admin, anyone on
        a free-preview lesson, or a student actively enrolled in the course."""
        lesson_file = get_object_or_404(LessonFile.objects.select_related("lesson__course"), pk=pk)
        lesson = lesson_file.lesson
        user = request.user
        allowed = (
            user.role == "admin"
            or lesson.is_free_preview
            or lesson.course.enrollments.filter(student=user, is_active=True).exists()
        )
        if not allowed:
            raise PermissionDenied("برای دانلود این فایل باید در دوره ثبت‌نام کرده باشید.")
        return Response({"url": _download_url(lesson_file)})


def _download_url(lesson_file: LessonFile) -> str:
    storage = lesson_file.file.storage
    if hasattr(storage, "bucket"):  # S3/MinIO: signed, forced-download link
        from apps.videos.services.signing import get_download_url

        return get_download_url(lesson_file.file.name, lesson_file.original_name)
    return lesson_file.file.url


class ClassSessionViewSet(viewsets.ModelViewSet):
    """Admin CRUD for courses' scheduled (live) sessions. `join` is the one
    action open to enrolled students too."""

    serializer_class = ClassSessionSerializer
    permission_classes = (permissions.IsAuthenticated, IsAdminRole)
    queryset = ClassSession.objects.select_related("course")

    @action(detail=True, methods=["get"], permission_classes=[permissions.IsAuthenticated])
    def join(self, request, pk=None):
        """The room name is only ever handed out here — never embedded in
        the plain session list — and only to people who should actually be
        in the room: an admin (the instructor) or a student with an active
        enrollment. The public Jitsi server itself doesn't
        check any of that; an unguessable room name plus this gate is the
        access control."""
        session = get_object_or_404(ClassSession.objects.select_related("course"), pk=pk)
        user = request.user
        is_enrolled = session.course.enrollments.filter(student=user, is_active=True).exists()
        if not (user.role == "admin" or is_enrolled):
            raise PermissionDenied("شما به این دوره‌ی آنلاین دسترسی ندارید.")
        return Response({
            "room_name": session.room_slug,
            "display_name": user.get_full_name() or user.email,
            "title": session.title,
            "course_title": session.course.title,
        })


class MyScheduleView(generics.ListAPIView):
    """The logged-in student's calendar: every upcoming session across all
    courses they're enrolled in, soonest first."""

    serializer_class = StudentScheduleSerializer
    permission_classes = (permissions.IsAuthenticated,)

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):
            return ClassSession.objects.none()
        return (
            ClassSession.objects.filter(
                course__enrollments__student=self.request.user,
                course__enrollments__is_active=True,
                starts_at__gte=timezone.now(),
            )
            .select_related("course")
            .order_by("starts_at")
        )

