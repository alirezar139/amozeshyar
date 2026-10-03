from django.db import transaction
from django.shortcuts import get_object_or_404
from django.utils import timezone
from drf_spectacular.utils import extend_schema
from rest_framework import mixins, permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import NotFound, PermissionDenied, ValidationError
from rest_framework.response import Response

from apps.accounts.authentication import UploadJWTAuthentication
from apps.accounts.models import User

from . import services
from .models import Conversation, ConversationMember, ConversationRead, Message, MessageReaction
from .serializers import (
    AuditMessageSerializer,
    ConversationSerializer,
    GroupSettingsSerializer,
    MemberSerializer,
    MessageSerializer,
    SendMessageSerializer,
)

PAGE = 40
REACTION_EMOJIS = {"👍", "❤️", "😂", "😮", "😢", "🙏", "🔥", "👏", "🎉", "💯", "✅", "🤔"}


class ConversationViewSet(mixins.DestroyModelMixin, viewsets.ReadOnlyModelViewSet):
    """Chat: private conversations with the teacher, course groups, the
    teacher's own groups and classmate-to-classmate chats. Clients poll
    `messages/?after=` for new messages."""

    serializer_class = ConversationSerializer
    permission_classes = (permissions.IsAuthenticated,)
    pagination_class = None

    def get_authenticators(self):
        # Sending a voice note or file is an upload; see UploadJWTAuthentication.
        if self.request and self.request.method == "POST" and self.request.path.endswith("/messages/"):
            return [UploadJWTAuthentication()]
        return super().get_authenticators()

    def _rows(self, queryset):
        return services.annotate_for(
            queryset.select_related("student", "course", "pinned_message__sender"), self.request.user
        )

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):
            return Conversation.objects.none()
        return self._rows(services.visible_conversations(self.request.user))

    def _conversation(self, pk) -> Conversation:
        conversation = get_object_or_404(Conversation.objects.select_related("student", "course"), pk=pk)
        if not services.can_access(self.request.user, conversation):
            raise NotFound()
        return conversation

    def _row(self, conversation):
        return self.get_serializer(self._rows(Conversation.objects.filter(pk=conversation.pk)).get()).data

    def _require_manager(self, conversation):
        if not services.can_manage(self.request.user, conversation):
            raise PermissionDenied("فقط استاد می‌تواند تنظیمات گروه را تغییر دهد.")

    # ---------- listing / starting ----------
    @action(detail=False, methods=["get"])
    def unread(self, request):
        return Response({"total": services.unread_total(request.user)})

    @action(detail=False, methods=["get"])
    def classmates(self, request):
        """Students a student may start a private chat with (shared course)."""
        if services.is_teacher(request.user):
            people = User.objects.filter(role=User.Role.STUDENT, is_active=True).order_by("first_name")
        elif services.peer_chat_allowed():
            people = services.classmates(request.user).order_by("first_name")
        else:
            people = User.objects.none()
        query = request.query_params.get("search", "").strip()
        if query:
            from django.db.models import Q

            people = people.filter(Q(first_name__icontains=query) | Q(last_name__icontains=query) | Q(email__icontains=query))
        return Response({"allowed": services.is_teacher(request.user) or services.peer_chat_allowed(), "people": MemberSerializer(people[:50], many=True).data})

    @action(detail=False, methods=["post"])
    def start(self, request):
        """Open (or create) a private conversation: the teacher with
        `student_id`, a student with the teacher (no id), or a student with
        a classmate (`student_id`, when peer chat is on)."""
        user = request.user
        other_id = request.data.get("student_id")
        if services.is_teacher(user):
            conversation = services.get_or_create_direct(get_object_or_404(User, pk=other_id, role=User.Role.STUDENT))
        elif other_id and int(other_id) != user.id:
            if not services.peer_chat_allowed():
                raise PermissionDenied("گفت‌وگوی دانشجویان با یکدیگر غیرفعال است.")
            classmate = services.classmates(user).filter(pk=other_id).first()
            if not classmate:
                raise PermissionDenied("فقط با هم‌کلاسی‌های خود می‌توانید گفت‌وگو کنید.")
            conversation = services.get_or_create_peer(user, classmate)
        else:
            conversation = services.get_or_create_direct(user)
        return Response(self._row(conversation))

    # ---------- groups ----------
    @action(detail=False, methods=["post"])
    def groups(self, request):
        """Create a group: {title, member_ids, announcement_only}. The teacher's
        groups can include any student; a student's group is private to them
        and their classmates (only while classmate chat is on)."""
        teacher = services.is_teacher(request.user)
        if not teacher and not services.peer_chat_allowed():
            raise PermissionDenied("ساخت گروه توسط دانشجویان غیرفعال است.")
        payload = GroupSettingsSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        title = (payload.validated_data.get("title") or "").strip()
        if not title:
            raise ValidationError({"title": "نام گروه را وارد کنید."})
        with transaction.atomic():
            conversation = Conversation.objects.create(
                kind=Conversation.Kind.CUSTOM,
                title=title,
                avatar=payload.validated_data.get("avatar"),
                announcement_only=payload.validated_data.get("announcement_only", False),
                created_by=request.user,
                private=not teacher,
                last_message_at=timezone.now(),
            )
            member_ids = payload.validated_data.get("member_ids", [])
            if not teacher:
                allowed = set(services.classmates(request.user).values_list("pk", flat=True))
                member_ids = [i for i in member_ids if i in allowed] + [request.user.id]
            self._add_members(conversation, member_ids)
        return Response(self._row(conversation), status=status.HTTP_201_CREATED)

    def _add_members(self, conversation, user_ids) -> list:
        """Adds the students among `user_ids`; returns the ones who weren't in it before."""
        already = {u.pk for u in services.members(conversation)}
        students = [u for u in User.objects.filter(pk__in=user_ids, role=User.Role.STUDENT) if u.pk not in already]
        ConversationMember.objects.bulk_create(
            [ConversationMember(conversation=conversation, user=u) for u in students], ignore_conflicts=True
        )
        return students

    @action(detail=True, methods=["patch"], url_path="settings")
    def update_settings(self, request, pk=None):
        conversation = self._conversation(pk)
        self._require_manager(conversation)
        payload = GroupSettingsSerializer(conversation, data=request.data, partial=True)
        payload.is_valid(raise_exception=True)
        data = payload.validated_data
        if "announcement_only" in data:
            conversation.announcement_only = data["announcement_only"]
        if conversation.kind == Conversation.Kind.CUSTOM:
            if "title" in data and data["title"].strip():
                conversation.title = data["title"].strip()
            if "avatar" in data:
                conversation.avatar = data["avatar"]
        conversation.save()
        return Response(self._row(conversation))

    @action(detail=True, methods=["get", "post"], url_path="members")
    def members_list(self, request, pk=None):
        conversation = self._conversation(pk)
        if request.method == "POST":
            self._require_manager(conversation)
            if conversation.kind not in (Conversation.Kind.CUSTOM, Conversation.Kind.COURSE):
                raise ValidationError("به این گفت‌وگو نمی‌توان عضو اضافه کرد.")
            # In a course group this only adds to the chat — no access to the course itself.
            user_ids = request.data.get("user_ids", [])
            if conversation.private:
                allowed = set(services.classmates(request.user).values_list("pk", flat=True))
                user_ids = [i for i in user_ids if i in allowed]
            added = self._add_members(conversation, user_ids)
            if added:
                services.announce_joined(conversation, request.user, added)
        return Response(self._members(conversation))

    def _members(self, conversation):
        context = {"removable": services.removable_member_ids(conversation)}
        return MemberSerializer(services.members(conversation), many=True, context=context).data

    @action(detail=True, methods=["delete"], url_path=r"members/(?P<user_id>\d+)")
    def remove_member(self, request, pk=None, user_id=None):
        conversation = self._conversation(pk)
        self._require_manager(conversation)
        if int(user_id) not in services.removable_member_ids(conversation):
            raise ValidationError("دانشجوهای ثبت‌نام‌شده در دوره عضو ثابت گروه دوره هستند و حذف نمی‌شوند.")
        conversation.members.filter(user_id=user_id).delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=True, methods=["post"])
    def pin(self, request, pk=None):
        """Pin a message in a group ({message_id}), or unpin ({message_id: null})."""
        conversation = self._conversation(pk)
        self._require_manager(conversation)
        message_id = request.data.get("message_id")
        conversation.pinned_message = conversation.messages.filter(pk=message_id).first() if message_id else None
        conversation.save(update_fields=["pinned_message"])
        return Response(self._row(conversation))

    def destroy(self, request, pk=None):
        """DELETE removes a custom group; course groups and chats can't be deleted."""
        conversation = self._conversation(pk)
        self._require_manager(conversation)
        if conversation.kind != Conversation.Kind.CUSTOM:
            raise ValidationError("گروه دوره قابل حذف نیست.")
        conversation.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

    # ---------- messages ----------
    @extend_schema(request=SendMessageSerializer, responses=MessageSerializer)
    @action(detail=True, methods=["get", "post"])
    def messages(self, request, pk=None):
        conversation = self._conversation(pk)
        if request.method == "POST":
            return self._send(request, conversation)

        messages = conversation.messages.select_related("sender", "reply_to__sender").prefetch_related("reactions")
        after, before = request.query_params.get("after"), request.query_params.get("before")
        since = self._parse_since(request.query_params.get("since"))
        changed = []
        if after:
            page = list(messages.filter(id__gt=int(after)).order_by("id")[:200])
            if since:
                # Already-loaded messages that changed (deleted, reactions) since the last poll.
                changed = list(messages.filter(id__lte=int(after), updated_at__gt=since).order_by("id")[:200])
        else:
            if before:
                messages = messages.filter(id__lt=int(before))
            page = list(messages.order_by("-id")[:PAGE])[::-1]
        row = self._rows(Conversation.objects.filter(pk=conversation.pk)).get()
        context = {"request": request, "read_markers": self._markers(conversation)}
        return Response({
            "server_time": timezone.now(),
            "changed": MessageSerializer(changed, many=True, context=context).data,
            "messages": MessageSerializer(page, many=True, context=context).data,
            "has_more": bool(page) and not after and conversation.messages.filter(id__lt=page[0].id).exists(),
            "others_last_read": row.others_last_read,
            "conversation": self.get_serializer(row).data,
        })

    @staticmethod
    def _parse_since(raw):
        """ISO timestamp from the last poll. A '+' in the offset arrives as a
        space when the client didn't URL-encode it; restore it rather than fail."""
        if not raw:
            return None
        from django.utils.dateparse import parse_datetime

        value = parse_datetime(raw.strip().replace(" ", "+"))
        if value is None:
            raise ValidationError({"since": "زمان نامعتبر است."})
        return value

    def _markers(self, conversation):
        """(user_id, last_read) for everyone but the developer accounts."""
        return list(
            ConversationRead.objects.filter(conversation=conversation)
            .exclude(user__is_superuser=True)
            .values_list("user_id", "last_read_message_id")
        )

    @action(detail=True, methods=["get"], url_path=r"messages/(?P<message_id>\d+)/viewers")
    def viewers(self, request, pk=None, message_id=None):
        """Who has seen a message, with roughly when — for its sender or the teacher."""
        conversation = self._conversation(pk)
        message = get_object_or_404(conversation.messages, pk=message_id)
        if message.sender_id != request.user.id and not services.is_teacher(request.user):
            raise PermissionDenied()
        reads = (
            ConversationRead.objects.filter(conversation=conversation, last_read_message_id__gte=message.id)
            .exclude(user=message.sender)
            .exclude(user__is_superuser=True)
            .select_related("user")
            .order_by("-read_at")
        )
        return Response([{**MemberSerializer(r.user).data, "read_at": r.read_at} for r in reads])

    @action(detail=True, methods=["delete"], url_path=r"messages/(?P<message_id>\d+)")
    def delete_message(self, request, pk=None, message_id=None):
        """Delete for everyone: the sender can delete their own message; a
        group's manager any message in it. Soft delete — the teacher's chat
        report keeps the original."""
        conversation = self._conversation(pk)
        message = get_object_or_404(conversation.messages, pk=message_id, deleted_at__isnull=True)
        if message.sender_id != request.user.id and not services.can_manage(request.user, conversation):
            raise PermissionDenied("فقط فرستنده یا استاد می‌تواند این پیام را حذف کند.")
        message.deleted_at = timezone.now()
        message.deleted_by = request.user
        message.save(update_fields=["deleted_at", "deleted_by", "updated_at"])
        if conversation.pinned_message_id == message.id:
            Conversation.objects.filter(pk=conversation.pk).update(pinned_message=None)
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=True, methods=["post"], url_path=r"messages/(?P<message_id>\d+)/react")
    def react(self, request, pk=None, message_id=None):
        """{emoji}: add a reaction, change it, or remove it by sending the same one again."""
        conversation = self._conversation(pk)
        message = get_object_or_404(conversation.messages, pk=message_id, deleted_at__isnull=True)
        emoji = request.data.get("emoji")
        if emoji not in REACTION_EMOJIS:
            raise ValidationError({"emoji": "این واکنش پشتیبانی نمی‌شود."})
        existing = MessageReaction.objects.filter(message=message, user=request.user).first()
        if existing and existing.emoji == emoji:
            existing.delete()
        elif existing:
            existing.emoji = emoji
            existing.save(update_fields=["emoji"])
        else:
            MessageReaction.objects.create(message=message, user=request.user, emoji=emoji)
        message.save(update_fields=["updated_at"])  # so other clients' polls pick it up
        message = conversation.messages.prefetch_related("reactions").select_related("sender").get(pk=message.pk)
        return Response(MessageSerializer(message, context={"request": request}).data)

    # ---------- the teacher's chat report ----------
    @action(detail=False, methods=["get"], url_path="report")
    def report(self, request):
        """Every conversation on the site, private ones included, for the teacher."""
        if not services.is_teacher(request.user):
            raise PermissionDenied()
        from django.db.models import Count, Q

        rows = (
            Conversation.objects.filter(last_message_at__isnull=False)
            .select_related("student", "course")
            .annotate(total=Count("messages"), deleted=Count("messages", filter=Q(messages__deleted_at__isnull=False)))
            .order_by("-last_message_at")
        )
        data = []
        for c in rows:
            people = services.members(c)
            if c.kind == Conversation.Kind.COURSE:
                title = c.title or c.course.title
            elif c.kind == Conversation.Kind.CUSTOM:
                title = c.title or "گروه"
            else:
                title = " و ".join(MemberSerializer(p).data["name"] for p in people[-2:])
            data.append({
                "id": c.id, "kind": c.kind, "private": c.private or c.kind == Conversation.Kind.PEER,
                "title": title, "members": len(people), "messages": c.total, "deleted": c.deleted,
                "last_message_at": c.last_message_at,
            })
        return Response(data)

    @action(detail=False, methods=["get"], url_path=r"report/(?P<conversation_id>\d+)")
    def report_messages(self, request, conversation_id=None):
        if not services.is_teacher(request.user):
            raise PermissionDenied()
        conversation = get_object_or_404(Conversation, pk=conversation_id)
        messages = conversation.messages.select_related("sender", "reply_to__sender", "deleted_by").prefetch_related("reactions")
        before = request.query_params.get("before")
        if before:
            messages = messages.filter(id__lt=int(before))
        page = list(messages.order_by("-id")[:100])[::-1]
        context = {"request": request, "audit": True}
        return Response({
            "messages": AuditMessageSerializer(page, many=True, context=context).data,
            "has_more": bool(page) and conversation.messages.filter(id__lt=page[0].id).exists(),
        })

    def _send(self, request, conversation):
        if not services.can_send(request.user, conversation):
            raise PermissionDenied("در این گروه فقط استاد می‌تواند پیام بفرستد.")
        payload = SendMessageSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        data = payload.validated_data
        upload = data.get("file")
        reply_to = (
            conversation.messages.filter(pk=data.get("reply_to"), deleted_at__isnull=True).first()
            if data.get("reply_to") else None
        )
        message = Message.objects.create(
            reply_to=reply_to,
            conversation=conversation,
            sender=request.user,
            text=data.get("text", ""),
            attachment=upload,
            attachment_kind=data.get("kind", ""),
            attachment_name=upload.name[:255] if upload else "",
            attachment_size=upload.size if upload else 0,
            duration_seconds=data.get("duration_seconds") if data.get("kind") == Message.AttachmentKind.VOICE else None,
        )
        Conversation.objects.filter(pk=conversation.pk).update(last_message_at=timezone.now())
        services.mark_read(conversation, request.user, message.id)
        return Response(
            MessageSerializer(message, context={"request": request, "read_markers": self._markers(conversation)}).data,
            status=status.HTTP_201_CREATED,
        )

    @action(detail=True, methods=["post"])
    def read(self, request, pk=None):
        conversation = self._conversation(pk)
        message_id = request.data.get("message_id")
        try:
            message_id = int(message_id) if message_id is not None else None
        except (TypeError, ValueError) as e:
            raise ValidationError({"message_id": "Invalid id."}) from e
        return Response({"last_read_message_id": services.mark_read(conversation, request.user, message_id)})

