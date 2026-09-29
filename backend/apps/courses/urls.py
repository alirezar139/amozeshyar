from django.urls import path
from rest_framework.routers import DefaultRouter

from . import views

router = DefaultRouter()
router.register("categories", views.CategoryViewSet, basename="category")
router.register("courses/manage", views.CourseManageViewSet, basename="course-manage")
router.register("lessons", views.LessonViewSet, basename="lesson")
router.register("class-sessions", views.ClassSessionViewSet, basename="class-session")
router.register("courses", views.PublicCourseViewSet, basename="course-public")

urlpatterns = [
    path("schedule/upcoming/", views.MyScheduleView.as_view(), name="my-schedule"),
    *router.urls,
]
