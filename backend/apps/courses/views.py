from rest_framework import permissions, viewsets

from apps.accounts.permissions import IsAdminRole, IsInstructor

from .filters import CourseFilter
from .models import Category, Course, Lesson
from .permissions import IsCourseOwner
from .serializers import (
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


class CourseModerationViewSet(viewsets.ModelViewSet):
    """Admin-only approve/reject queue for courses awaiting review."""

    serializer_class = CourseModerationSerializer
    permission_classes = (permissions.IsAuthenticated, IsAdminRole)
    http_method_names = ("get", "patch", "head", "options")
    queryset = Course.objects.filter(status=Course.Status.PENDING_REVIEW)


class LessonViewSet(viewsets.ModelViewSet):
    serializer_class = LessonSerializer
    permission_classes = (permissions.IsAuthenticated, IsInstructor)

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):
            return Lesson.objects.none()
        return Lesson.objects.filter(course__instructor__user=self.request.user)

    def perform_create(self, serializer):
        course = serializer.validated_data["course"]
        if course.instructor.user_id != self.request.user.id:
            from rest_framework.exceptions import PermissionDenied

            raise PermissionDenied("You do not own this course.")
        serializer.save()
