from rest_framework import generics, permissions, viewsets

from apps.accounts.permissions import IsAdminRole, IsInstructor

from .filters import CourseFilter
from .models import Category, Course, Lesson
from .permissions import IsCourseOwner
from .serializers import (
    AdminCourseWriteSerializer,
    CategorySerializer,
    CourseModerationSerializer,
    CourseWriteSerializer,
    LessonSerializer,
    PublicCourseDetailSerializer,
    PublicCourseListSerializer,
)


class CategoryViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Category.objects.all()
    serializer_class = CategorySerializer
    permission_classes = (permissions.AllowAny,)


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
            from rest_framework.exceptions import PermissionDenied

            raise PermissionDenied("You do not own this course.")
        serializer.save()
