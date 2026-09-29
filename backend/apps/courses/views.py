from django.db.models import Count, Q
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import generics, permissions, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied
from rest_framework.response import Response

from apps.accounts.permissions import IsAdminRole

from .filters import CourseFilter
from .models import Category, ClassSession, Course, Lesson
from .serializers import (
    CategorySerializer,
    ClassSessionSerializer,
    CourseManageSerializer,
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
    """Public catalog/detail — only ever exposes published courses."""

    permission_classes = (permissions.AllowAny,)
    lookup_field = "slug"
    filterset_class = CourseFilter
    queryset = Course.objects.filter(status=Course.Status.PUBLISHED).select_related("category")

    def get_serializer_class(self):
        if self.action == "retrieve":
            return PublicCourseDetailSerializer
        return PublicCourseListSerializer


class CourseManageViewSet(viewsets.ModelViewSet):
    """Admin (the site's instructor): every course in any status — create,
    edit, and publish/unpublish by patching `status`. No approval step: the
    instructor owns the site, so what they publish goes live."""

    serializer_class = CourseManageSerializer
    permission_classes = (permissions.IsAuthenticated, IsAdminRole)
    http_method_names = ("get", "post", "patch", "head", "options")
    queryset = Course.objects.all().select_related("category")


class LessonViewSet(viewsets.ModelViewSet):
    serializer_class = LessonSerializer
    permission_classes = (permissions.IsAuthenticated, IsAdminRole)
    queryset = Lesson.objects.all()


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
            raise PermissionDenied("شما به این کلاس دسترسی ندارید.")
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

