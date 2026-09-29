from django.conf import settings
from django.db import models
from django.db.models import Q

from apps.common.models import TimeStampedModel


class Conversation(TimeStampedModel):
    """A chat on the site. Four kinds:
      - direct: one student <-> the teacher side (every admin); `student` set.
      - course: a group per course — the teacher plus every student actively
        enrolled in it (`course` set). Membership is derived from enrollment,
        so it follows purchases and refunds automatically.
      - custom: a group with explicit members (ConversationMember). Made by
        the teacher (the teacher side is in it), or by a student for their
        classmates (`private`: the teacher side isn't in it and can't see it).
      - peer: a private chat between two classmates (two ConversationMember
        rows). The teacher side does not see these.
    """

    class Kind(models.TextChoices):
        DIRECT = "direct", "Direct"
        COURSE = "course", "Course group"
        CUSTOM = "custom", "Custom group"
        PEER = "peer", "Peer"

    kind = models.CharField(max_length=10, choices=Kind.choices)
    student = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.CASCADE, related_name="direct_conversations"
    )
    course = models.ForeignKey(
        "courses.Course", null=True, blank=True, on_delete=models.CASCADE, related_name="conversations"
    )
    last_message_at = models.DateTimeField(null=True, blank=True, db_index=True)
    # Group settings (course and custom groups).
    title = models.CharField(max_length=120, blank=True)
    avatar = models.ImageField(upload_to="chat_groups/", blank=True, null=True)
    announcement_only = models.BooleanField(default=False)
    pinned_message = models.ForeignKey("Message", null=True, blank=True, on_delete=models.SET_NULL, related_name="+")
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="+")
    private = models.BooleanField(default=False)

    class Meta:
        ordering = ("-last_message_at", "-created_at")
        constraints = [
            models.UniqueConstraint(fields=("student",), condition=Q(kind="direct"), name="one_direct_per_student"),
            models.UniqueConstraint(fields=("course",), condition=Q(kind="course"), name="one_group_per_course"),
            models.CheckConstraint(
                condition=(Q(kind="direct", student__isnull=False, course__isnull=True))
                | (Q(kind="course", course__isnull=False, student__isnull=True))
                | (Q(kind__in=("custom", "peer"), student__isnull=True, course__isnull=True)),
                name="conversation_kind_matches_subject",
            ),
        ]

    def __str__(self):
        return f"{self.kind}: {self.title or self.student or self.course or self.pk}"

    @property
    def is_group(self) -> bool:
        return self.kind in (self.Kind.COURSE, self.Kind.CUSTOM)


class ConversationMember(models.Model):
    """Explicit membership, for custom groups and peer chats."""

    conversation = models.ForeignKey(Conversation, on_delete=models.CASCADE, related_name="members")
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="chat_memberships")
    added_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=("conversation", "user"), name="one_membership_per_user")]


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
    reply_to = models.ForeignKey("self", null=True, blank=True, on_delete=models.SET_NULL, related_name="replies")

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
    # When the marker last moved forward — i.e. roughly when they saw it.
    read_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=("conversation", "user"), name="one_read_marker_per_user")]
