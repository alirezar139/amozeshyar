from django.conf import settings
from django.db import models

from apps.common.models import TimeStampedModel


class BoardCard(TimeStampedModel):
    """One card on the teacher's kanban board of their own work (planning
    courses, recording lessons, preparing handouts...). Only admins see it."""

    class Column(models.TextChoices):
        IDEA = "idea", "Idea"
        IN_PROGRESS = "in_progress", "In progress"
        READY = "ready", "Ready"
        PUBLISHED = "published", "Published"

    class Color(models.TextChoices):
        NONE = "", "None"
        RED = "red", "Red"
        AMBER = "amber", "Amber"
        GREEN = "green", "Green"
        BLUE = "blue", "Blue"
        PURPLE = "purple", "Purple"

    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    column = models.CharField(max_length=20, choices=Column.choices, default=Column.IDEA, db_index=True)
    # Fractional ordering within a column: a drop between two cards takes the
    # midpoint, so reordering touches only the moved card.
    position = models.FloatField(default=0)
    color = models.CharField(max_length=10, choices=Color.choices, blank=True, default="")
    due_date = models.DateField(null=True, blank=True)
    course = models.ForeignKey("courses.Course", null=True, blank=True, on_delete=models.SET_NULL, related_name="board_cards")
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL, related_name="+")

    class Meta:
        ordering = ("column", "position", "id")

    def __str__(self):
        return self.title
