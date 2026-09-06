from django.db.models import Count, Q
from django.utils import timezone
from rest_framework import generics, permissions, viewsets
from rest_framework.exceptions import PermissionDenied

from apps.accounts.permissions import IsAdminRole, IsInstructor

from .filters import CourseFilter
from .models import Category, ClassSession, Course, Lesson
from .permissions import IsCourseOwner
from .serializers import (
    AdminCourseWriteSerializer,
    CategorySerializer,
    ClassSessionSerializer,
    CourseModerationSerializer,
    CourseWriteSerializer,
    LessonSerializer,
    PublicCourseDetailSerializer,
    PublicCourseListSerializer,
    StudentScheduleSerializer,
)


class CategoryViewSet(viewsets.ReadOnlyModelViewSet):
    """Public category list — `course_count` only counts published courses, so an empty
    or all-pending category still shows up (for future admin category management) but
    the homepage grid can filter those out client-side to avoid dead-end links."""

    serializer_class = CategorySerializer
    permission_classes = (permissions.AllowAny,)

    def get_queryset(self):
        return Category.objects.annotate(
            course_count=Count("courses", filter=Q(courses__status=Course.Status.PUBLISHED))
        )


class PublicCourseViewSet(viewsets.ReadOnlyModelViewSet):
    """Public catalog/detail — only ever exposes admin-approved, published courses."""

    permission_classes = (permissions.AllowAny,)
    lookup_field = "slug"
    filterset_class = CourseFilter
    queryset = Course.objects.filter(status=Course.Status.PUBLISHED).select_related("instructor__user", "category")

    def get_serializer_class(self):
        if self.action == "retrieve":
            return PublicCourseDetailSerializer
        return PublicCourseListSerializer


class MyCoursesViewSet(viewsets.ModelViewSet):
    """Instructor panel CRUD for their own courses, including drafts/pending/rejected."""

    serializer_class = CourseWriteSerializer
    permission_classes = (permissions.IsAuthenticated, IsInstructor, IsCourseOwner)

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):
            return Course.objects.none()
        return Course.objects.filter(instructor__user=self.request.user)


class AdminCourseCreateView(generics.CreateAPIView):
    """Admin-only: author a course directly on behalf of any instructor, published immediately."""

    serializer_class = AdminCourseWriteSerializer
    permission_classes = (permissions.IsAuthenticated, IsAdminRole)


class CourseModerationViewSet(viewsets.ModelViewSet):
    """Admin-only approve/reject queue for courses awaiting review."""

    serializer_class = CourseModerationSerializer
    permission_classes = (permissions.IsAuthenticated, IsAdminRole)
    http_method_names = ("get", "patch", "head", "options")
    queryset = Course.objects.filter(status=Course.Status.PENDING_REVIEW)


class AdminAllCoursesViewSet(viewsets.ReadOnlyModelViewSet):
    """Admin-only: every course regardless of status, so the admin can jump into
    lesson/video management for a course they just authored (which — being
    published immediately — never appears in the moderation queue above)."""

    serializer_class = CourseModerationSerializer
    permission_classes = (permissions.IsAuthenticated, IsAdminRole)
    queryset = Course.objects.all().select_related("instructor__user")


class LessonViewSet(viewsets.ModelViewSet):
    serializer_class = LessonSerializer
    permission_classes = (permissions.IsAuthenticated,)

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):
            return Lesson.objects.none()
        if self.request.user.role == "admin":
            return Lesson.objects.all()
        return Lesson.objects.filter(course__instructor__user=self.request.user)

    def perform_create(self, serializer):
        course = serializer.validated_data["course"]
        is_owner = course.instructor.user_id == self.request.user.id
        if not (is_owner or self.request.user.role == "admin"):
            raise PermissionDenied("You do not own this course.")
        serializer.save()


class ClassSessionViewSet(viewsets.ModelViewSet):
    """Instructor/admin CRUD for a course's scheduled (live) sessions — same
    ownership shape as LessonViewSet: an instructor only ever sees/edits
    sessions for their own courses, admin sees everything."""

    serializer_class = ClassSessionSerializer
    permission_classes = (permissions.IsAuthenticated,)

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):
            return ClassSession.objects.none()
        if self.request.user.role == "admin":
            return ClassSession.objects.all()
        return ClassSession.objects.filter(course__instructor__user=self.request.user)

    def perform_create(self, serializer):
        course = serializer.validated_data["course"]
        is_owner = course.instructor.user_id == self.request.user.id
        if not (is_owner or self.request.user.role == "admin"):
            raise PermissionDenied("You do not own this course.")
        serializer.save()


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
            .select_related("course", "course__instructor__user")
            .order_by("starts_at")
        )
