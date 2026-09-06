from django.urls import path
from rest_framework.routers import DefaultRouter

from . import views

router = DefaultRouter()
router.register("enrollments", views.MyEnrollmentsViewSet, basename="enrollment")
router.register("wishlist", views.WishlistViewSet, basename="wishlist")

urlpatterns = router.urls + [
    path("progress/", views.LessonProgressView.as_view(), name="lesson-progress"),
]
