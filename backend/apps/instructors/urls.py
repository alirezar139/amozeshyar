from rest_framework.routers import DefaultRouter

from django.urls import path

from . import views

router = DefaultRouter()
router.register("moderation", views.InstructorModerationViewSet, basename="instructor-moderation")
router.register("", views.PublicInstructorViewSet, basename="instructor-public")

urlpatterns = [
    path("me/", views.MyInstructorProfileView.as_view(), name="instructor-me"),
    *router.urls,
]
