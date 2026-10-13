from django.conf import settings
from django.db import models


class ErrorEvent(models.Model):
    """One thing that went wrong: an API error response, a server crash, or a browser error.

    Shown live to the developer account and attached to support reports. Kept short-lived and
    capped (see recorder.prune) so a flood of bad requests can't fill the disk.
    """

    class Source(models.TextChoices):
        API = "api", "API"
        SERVER = "server", "Server"
        BROWSER = "browser", "Browser"

    class Level(models.TextChoices):
        ERROR = "error", "Error"
        WARNING = "warning", "Warning"

    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    source = models.CharField(max_length=10, choices=Source.choices)
    level = models.CharField(max_length=10, choices=Level.choices)
    method = models.CharField(max_length=10, blank=True)
    path = models.CharField(max_length=300, blank=True)
    status = models.PositiveSmallIntegerField(null=True, blank=True)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="+")
    user_label = models.CharField(max_length=254, blank=True)
    message = models.TextField()
    detail = models.TextField(blank=True)
    page_url = models.CharField(max_length=300, blank=True)

    class Meta:
        ordering = ("-id",)

    def __str__(self):
        return f"[{self.source}/{self.level}] {self.message[:80]}"


class SupportReport(models.Model):
    """A "something is wrong" note from the instructor, with their recent errors attached."""

    created_at = models.DateTimeField(auto_now_add=True)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL, related_name="+")
    user_label = models.CharField(max_length=254, blank=True)
    message = models.TextField()
    page_url = models.CharField(max_length=300, blank=True)
    user_agent = models.CharField(max_length=300, blank=True)
    # What the browser had caught on the page (it may never have reached the server).
    browser_events = models.JSONField(default=list, blank=True)
    events = models.ManyToManyField(ErrorEvent, blank=True, related_name="reports")
    resolved = models.BooleanField(default=False)
    resolved_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ("-id",)

    def __str__(self):
        return f"#{self.id} {self.user_label}: {self.message[:60]}"
