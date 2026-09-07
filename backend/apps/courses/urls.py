from django.urls import path
from rest_framework.routers import DefaultRouter

from . import views

router = DefaultRouter()
router.register("categories", views.CategoryViewSet, basename="category")
router.register("courses/moderation", views.CourseModerationViewSet, basename="course-moderation")
router.register("courses/admin-all", views.AdminAllCoursesViewSet, basename="course-admin-all")
router.register("courses/mine", views.MyCoursesViewSet, basename="course-mine")
router.register("lessons", views.LessonViewSet, basename="lesson")
router.register("class-sessions", views.ClassSessionViewSet, basename="class-session")
router.register("courses", views.PublicCourseViewSet, basename="course-public")

urlpatterns = [
    path("courses/admin-create/", views.AdminCourseCreateView.as_view(), name="course-admin-create"),
    path("schedule/upcoming/", views.MyScheduleView.as_view(), name="my-schedule"),
    path("reports/instructor-classes/", views.InstructorClassReportView.as_view(), name="instructor-class-report"),
    *router.urls,
]
