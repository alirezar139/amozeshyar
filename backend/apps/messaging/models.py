from django.conf import settings
from django.db import models
from django.db.models import Q

from apps.common.models import TimeStampedModel


class Conversation(TimeStampedModel):
    """A chat between the site's teacher side (every admin) and students.

    Two kinds, one per subject:
      - direct: one student <-> the teacher (`student` set);
      - course: a group per course — the teacher plus every student actively
        enrolled in it (`course` set). Membership is derived from enrollment,
        not stored, so it follows purchases and refunds automatically.
    """

    class Kind(models.TextChoices):
        DIRECT = "direct", "Direct"
        COURSE = "course", "Course group"

    kind = models.CharField(max_length=10, choices=Kind.choices)
    student = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.CASCADE, related_name="direct_conversations"
    )
    course = models.ForeignKey(
        "courses.Course", null=True, blank=True, on_delete=models.CASCADE, related_name="conversations"
    )
    last_message_at = models.DateTimeField(null=True, blank=True, db_index=True)

    class Meta:
        ordering = ("-last_message_at", "-created_at")
        constraints = [
            models.UniqueConstraint(fields=("student",), condition=Q(kind="direct"), name="one_direct_per_student"),
            models.UniqueConstraint(fields=("course",), condition=Q(kind="course"), name="one_group_per_course"),
            models.CheckConstraint(
                condition=(Q(kind="direct", student__isnull=False, course__isnull=True))
                | (Q(kind="course", course__isnull=False, student__isnull=True)),
                name="conversation_kind_matches_subject",
            ),
        ]

    def __str__(self):
        return f"{self.kind}: {self.student or self.course}"


class Message(TimeStampedModel):
    class AttachmentKind(models.TextChoices):
        IMAGE = "image", "Image"
        FILE = "file", "File"
        VOICE = "voice", "Voice"

    conversation = models.ForeignKey(Conversation, on_delete=models.CASCADE, related_name="messages")
    sender = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="sent_messages")
    text = models.TextField(blank=True)
    attachment = models.FileField(upload_to="chat/", blank=True, null=True)
    attachment_kind = models.CharField(max_length=10, choices=AttachmentKind.choices, blank=True)
    attachment_name = models.CharField(max_length=255, blank=True)
    attachment_size = models.PositiveBigIntegerField(default=0)
    # Voice notes: length in seconds, as measured by the recorder.
    duration_seconds = models.PositiveIntegerField(null=True, blank=True)

    class Meta:
        ordering = ("created_at", "id")
        indexes = [models.Index(fields=("conversation", "id"))]

    def __str__(self):
        return f"{self.sender}: {self.text[:40] or self.attachment_kind}"


class ConversationRead(models.Model):
    """How far one user has read in one conversation (last message id seen)."""

    conversation = models.ForeignKey(Conversation, on_delete=models.CASCADE, related_name="reads")
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="conversation_reads")
    last_read_message_id = models.PositiveBigIntegerField(default=0)

    class Meta:
        constraints = [models.UniqueConstraint(fields=("conversation", "user"), name="one_read_marker_per_user")]
