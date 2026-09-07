from django.conf import settings
from django.db import models

from apps.common.models import TimeStampedModel
from apps.courses.models import Course


class Enrollment(TimeStampedModel):
    student = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="enrollments")
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name="enrollments")
    order_item = models.ForeignKey(
        "payments.OrderItem", on_delete=models.SET_NULL, null=True, blank=True, related_name="enrollments"
    )
    access_granted_at = models.DateTimeField(auto_now_add=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        unique_together = ("student", "course")
        ordering = ("-access_granted_at",)

    def __str__(self):
        return f"{self.student} -> {self.course}"


class WishlistItem(TimeStampedModel):
    student = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="wishlist_items")
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name="wishlisted_by")

    class Meta:
        unique_together = ("student", "course")


class LessonProgress(TimeStampedModel):
    """How far a student has watched one lesson's video.

    Powers the "continue learning" resume flow: `updated_at` (from
    TimeStampedModel) says which lesson was watched most recently, and
    `position_seconds` says where to seek back to.
    """

    student = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="lesson_progress")
    lesson = models.ForeignKey("courses.Lesson", on_delete=models.CASCADE, related_name="progress_records")
    position_seconds = models.PositiveIntegerField(default=0)
    completed = models.BooleanField(default=False)

    class Meta:
        unique_together = ("student", "lesson")

    def __str__(self):
        return f"{self.student} @ {self.lesson} ({self.position_seconds}s)"
