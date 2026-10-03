"""Who can see which conversation, and unread/read bookkeeping.

The "teacher side" is every admin account (the site's instructor, plus the
developer for support). Developer (superuser) activity never counts as the
teacher having *read* something, so a student's ✓✓ always means the
instructor saw it. Peer chats between classmates are private: the teacher
side can't see them (the teacher can switch the feature off instead).
"""
from django.db.models import Count, Max, OuterRef, Q, Subquery
from django.db.models.functions import Coalesce
from django.utils import timezone

from apps.accounts.models import User
from apps.courses.models import Course
from apps.enrollments.models import Enrollment

from .models import Conversation, ConversationMember, ConversationRead, Message


def is_teacher(user) -> bool:
    return user.is_authenticated and user.role == User.Role.ADMIN


def peer_chat_allowed() -> bool:
    from apps.instructors.site import get_site_owner

    owner = get_site_owner()
    return owner.allow_peer_chat if owner else False


def enrolled_course_ids(user):
    return Enrollment.objects.filter(student=user, is_active=True).values_list("course_id", flat=True)


def classmates(user):
    """Students sharing at least one active course with `user`."""
    return (
        User.objects.filter(
            role=User.Role.STUDENT,
            is_active=True,
            enrollments__course_id__in=list(enrolled_course_ids(user)),
            enrollments__is_active=True,
        )
        .exclude(pk=user.pk)
        .distinct()
    )


def ensure_course_groups(course_ids) -> None:
    existing = set(Conversation.objects.filter(kind=Conversation.Kind.COURSE, course_id__in=course_ids).values_list("course_id", flat=True))
    Conversation.objects.bulk_create(
        [Conversation(kind=Conversation.Kind.COURSE, course_id=cid) for cid in set(course_ids) - existing],
        ignore_conflicts=True,
    )


def get_or_create_direct(student) -> Conversation:
    conversation, _ = Conversation.objects.get_or_create(kind=Conversation.Kind.DIRECT, student=student)
    return conversation


def send_bot_message(student, text: str, bot: str) -> Message | None:
    """Post an automated message into `student`'s direct chat with the teacher.

    Sent as the site owner (any admin as a fallback) and tagged with `bot`, so
    the chat shows it as that bot. Returns None if there's no teacher account.
    """
    from apps.instructors.site import get_site_owner

    owner = get_site_owner()
    sender = owner.user if owner else User.objects.filter(role=User.Role.ADMIN, is_active=True).first()
    if sender is None:
        return None
    conversation = get_or_create_direct(student)
    message = Message.objects.create(conversation=conversation, sender=sender, text=text, bot=bot)
    Conversation.objects.filter(pk=conversation.pk).update(last_message_at=timezone.now())
    return message


def announce_joined(conversation: Conversation, by, users) -> Message:
    """A system line in the chat ("X joined the group"), shown centered rather than as a bubble."""
    from .serializers import display_name

    names = [display_name(u) for u in users]
    who = names[0] if len(names) == 1 else "، ".join(names[:-1]) + " و " + names[-1]
    verb = "به گروه اضافه شد" if len(names) == 1 else "به گروه اضافه شدند"
    message = Message.objects.create(conversation=conversation, sender=by, text=f"{who} {verb}", bot="system")
    Conversation.objects.filter(pk=conversation.pk).update(last_message_at=timezone.now())
    return message


def get_or_create_peer(a, b) -> Conversation:
    existing = (
        Conversation.objects.filter(kind=Conversation.Kind.PEER, members__user=a)
        .filter(members__user=b)
        .first()
    )
    if existing:
        return existing
    conversation = Conversation.objects.create(kind=Conversation.Kind.PEER, created_by=a)
    ConversationMember.objects.bulk_create([ConversationMember(conversation=conversation, user=u) for u in (a, b)])
    return conversation


def visible_conversations(user):
    """Conversations `user` may open. Also makes sure the groups they should
    see exist (created lazily, the first time anyone looks)."""
    if is_teacher(user):
        ensure_course_groups(Course.objects.filter(status=Course.Status.PUBLISHED).values_list("id", flat=True))
        return Conversation.objects.filter(
            Q(kind=Conversation.Kind.COURSE)
            | Q(kind=Conversation.Kind.CUSTOM, private=False)
            | Q(kind=Conversation.Kind.DIRECT, last_message_at__isnull=False)
        )
    course_ids = list(enrolled_course_ids(user))
    ensure_course_groups(course_ids)
    get_or_create_direct(user)
    peers_on = peer_chat_allowed()
    student_made = Q(kind=Conversation.Kind.PEER) | Q(kind=Conversation.Kind.CUSTOM, private=True)
    return Conversation.objects.filter(
        Q(kind=Conversation.Kind.DIRECT, student=user)
        | Q(kind=Conversation.Kind.COURSE, course_id__in=course_ids)
        | Q(kind=Conversation.Kind.COURSE, members__user=user)
        | (Q(kind=Conversation.Kind.CUSTOM, private=False, members__user=user))
        | ((student_made & Q(members__user=user)) if peers_on else Q(pk__in=[]))
    ).distinct()


def can_access(user, conversation: Conversation) -> bool:
    kind = conversation.kind
    if kind == Conversation.Kind.PEER or (kind == Conversation.Kind.CUSTOM and conversation.private):
        return peer_chat_allowed() and conversation.members.filter(user=user).exists()
    if is_teacher(user):
        return True
    if kind == Conversation.Kind.DIRECT:
        return conversation.student_id == user.id
    if kind == Conversation.Kind.CUSTOM:
        return conversation.members.filter(user=user).exists()
    return (
        Enrollment.objects.filter(student=user, course_id=conversation.course_id, is_active=True).exists()
        or conversation.members.filter(user=user).exists()
    )


def can_send(user, conversation: Conversation) -> bool:
    return not (conversation.is_group and conversation.announcement_only and not can_manage(user, conversation))


def can_manage(user, conversation: Conversation) -> bool:
    """The teacher manages course groups and their own groups; a student
    manages a group they created for their classmates."""
    if conversation.kind == Conversation.Kind.CUSTOM and conversation.private:
        return conversation.created_by_id == user.id
    return is_teacher(user) and conversation.is_group


def members(conversation: Conversation):
    """Everyone in the conversation, the teacher (site owner) first."""
    from apps.instructors.site import get_site_owner

    owner = get_site_owner()
    teacher_side = conversation.kind != Conversation.Kind.PEER and not conversation.private
    teacher = [owner.user] if owner and teacher_side else []
    if conversation.kind == Conversation.Kind.DIRECT:
        others = [conversation.student]
    elif conversation.kind == Conversation.Kind.COURSE:
        # Enrolled students, plus anyone the teacher added to the group by hand.
        others = list(
            User.objects.filter(
                Q(enrollments__course_id=conversation.course_id, enrollments__is_active=True)
                | Q(chat_memberships__conversation=conversation)
            ).distinct().order_by("first_name")
        )
    else:
        others = [m.user for m in conversation.members.select_related("user").order_by("added_at")]
    return teacher + [u for u in others if not teacher or u.pk != teacher[0].pk]


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
    kind = conversation.kind
    if kind in (Conversation.Kind.DIRECT, Conversation.Kind.PEER):
        return 2
    if kind == Conversation.Kind.CUSTOM:
        return conversation.members.count() + (0 if conversation.private else 1)
    return (
        User.objects.filter(
            Q(enrollments__course_id=conversation.course_id, enrollments__is_active=True)
            | Q(chat_memberships__conversation=conversation)
        ).distinct().count() + 1
    )


def removable_member_ids(conversation: Conversation) -> set[int]:
    """Who the group's manager may remove: anyone in a custom group; in a
    course group only people added by hand — enrolled students stay."""
    added = set(conversation.members.values_list("user_id", flat=True))
    if conversation.kind == Conversation.Kind.COURSE:
        added -= set(enrolled_student_ids(conversation.course_id))
    return added


def enrolled_student_ids(course_id):
    return Enrollment.objects.filter(course_id=course_id, is_active=True).values_list("student_id", flat=True)


def last_message(conversation: Conversation) -> Message | None:
    return conversation.messages.select_related("sender").order_by("-id").first()
