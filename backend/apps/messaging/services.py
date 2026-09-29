"""Who can see which conversation, and unread/read bookkeeping.

The "teacher side" is every admin account (the site's instructor, plus the
developer for support). Developer (superuser) activity never counts as the
teacher having *read* something, so a student's ✓✓ always means the
instructor saw it.
"""
from django.db.models import Count, Max, OuterRef, Q, Subquery
from django.db.models.functions import Coalesce

from apps.accounts.models import User
from apps.courses.models import Course
from apps.enrollments.models import Enrollment

from .models import Conversation, ConversationRead, Message


def is_teacher(user) -> bool:
    return user.is_authenticated and user.role == User.Role.ADMIN


def enrolled_course_ids(user):
    return Enrollment.objects.filter(student=user, is_active=True).values_list("course_id", flat=True)


def ensure_course_groups(course_ids) -> None:
    existing = set(Conversation.objects.filter(kind=Conversation.Kind.COURSE, course_id__in=course_ids).values_list("course_id", flat=True))
    Conversation.objects.bulk_create(
        [Conversation(kind=Conversation.Kind.COURSE, course_id=cid) for cid in set(course_ids) - existing],
        ignore_conflicts=True,
    )


def get_or_create_direct(student) -> Conversation:
    conversation, _ = Conversation.objects.get_or_create(kind=Conversation.Kind.DIRECT, student=student)
    return conversation


def visible_conversations(user):
    """Conversations `user` may open. Also makes sure the groups they should
    see exist (created lazily, the first time anyone looks)."""
    if is_teacher(user):
        ensure_course_groups(Course.objects.filter(status=Course.Status.PUBLISHED).values_list("id", flat=True))
        return Conversation.objects.filter(
            Q(kind=Conversation.Kind.COURSE) | Q(kind=Conversation.Kind.DIRECT, last_message_at__isnull=False)
        )
    course_ids = list(enrolled_course_ids(user))
    ensure_course_groups(course_ids)
    get_or_create_direct(user)
    return Conversation.objects.filter(
        Q(kind=Conversation.Kind.DIRECT, student=user) | Q(kind=Conversation.Kind.COURSE, course_id__in=course_ids)
    )


def can_access(user, conversation: Conversation) -> bool:
    if is_teacher(user):
        return True
    if conversation.kind == Conversation.Kind.DIRECT:
        return conversation.student_id == user.id
    return Enrollment.objects.filter(student=user, course_id=conversation.course_id, is_active=True).exists()


def annotate_for(queryset, user):
    """unread count, my read marker and how far *others* have read (for ✓✓)."""
    my_read = ConversationRead.objects.filter(conversation=OuterRef("pk"), user=user).values("last_read_message_id")[:1]
    others_read = (
        ConversationRead.objects.filter(conversation=OuterRef("pk"))
        .exclude(user=user)
        .exclude(user__is_superuser=True)
        .values("conversation")
        .annotate(m=Max("last_read_message_id"))
        .values("m")[:1]
    )
    queryset = queryset.annotate(
        my_last_read=Coalesce(Subquery(my_read), 0),
        others_last_read=Coalesce(Subquery(others_read), 0),
    )
    return queryset.annotate(
        unread=Count(
            "messages",
            filter=Q(messages__id__gt=Coalesce(Subquery(my_read), 0)) & ~Q(messages__sender=user),
            distinct=True,
        )
    )


def unread_total(user) -> int:
    return sum(c.unread for c in annotate_for(visible_conversations(user), user))


def mark_read(conversation: Conversation, user, message_id: int | None = None) -> int:
    if message_id is None:
        message_id = conversation.messages.aggregate(m=Max("id"))["m"] or 0
    marker, _ = ConversationRead.objects.get_or_create(conversation=conversation, user=user)
    if message_id > marker.last_read_message_id:
        marker.last_read_message_id = message_id
        marker.save(update_fields=["last_read_message_id"])
    return marker.last_read_message_id


def member_count(conversation: Conversation) -> int:
    if conversation.kind == Conversation.Kind.DIRECT:
        return 2
    return Enrollment.objects.filter(course_id=conversation.course_id, is_active=True).count() + 1


def last_message(conversation: Conversation) -> Message | None:
    return conversation.messages.select_related("sender").order_by("-id").first()
