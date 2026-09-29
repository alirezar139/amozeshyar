from rest_framework import serializers

from apps.common.validators import ALLOWED_COURSE_FILE_EXTENSIONS

from . import services
from .models import Conversation, Message

IMAGE_EXTENSIONS = {"jpg", "jpeg", "png", "webp", "gif"}
VOICE_EXTENSIONS = {"webm", "ogg", "oga", "m4a", "mp4", "mp3", "wav", "aac"}
MAX_IMAGE_BYTES = 10 * 1024 * 1024
MAX_VOICE_BYTES = 20 * 1024 * 1024
MAX_FILE_BYTES = 50 * 1024 * 1024
MAX_TEXT_LENGTH = 4000


def _extension(name: str) -> str:
    return name.rsplit(".", 1)[-1].lower() if "." in name else ""


def display_name(user) -> str:
    return user.get_full_name() or user.email.split("@")[0]


class SenderSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    name = serializers.SerializerMethodField()
    is_teacher = serializers.SerializerMethodField()
    avatar = serializers.SerializerMethodField()

    def get_name(self, user) -> str:
        return display_name(user)

    def get_is_teacher(self, user) -> bool:
        return services.is_teacher(user)

    def get_avatar(self, user) -> str | None:
        return user.avatar.url if user.avatar else None


class MessageSerializer(serializers.ModelSerializer):
    sender = SenderSerializer(read_only=True)
    is_mine = serializers.SerializerMethodField()
    attachment_url = serializers.SerializerMethodField()
    reply_to = serializers.SerializerMethodField()
    seen_count = serializers.SerializerMethodField()
    is_deleted = serializers.SerializerMethodField()
    reactions = serializers.SerializerMethodField()

    class Meta:
        model = Message
        fields = (
            "id", "conversation", "sender", "is_mine", "text",
            "attachment_kind", "attachment_name", "attachment_size", "attachment_url", "duration_seconds",
            "reply_to", "seen_count", "is_deleted", "reactions", "created_at",
        )

    def to_representation(self, obj):
        data = super().to_representation(obj)
        if obj.deleted_at and not self.context.get("audit"):
            # Gone for everyone in the conversation; only the report keeps it.
            data.update(text="", attachment_kind="", attachment_name="", attachment_size=0,
                        attachment_url=None, duration_seconds=None, reply_to=None, reactions=[])
        return data

    def get_is_deleted(self, obj) -> bool:
        return obj.deleted_at is not None

    def get_reactions(self, obj) -> list[dict]:
        """[{emoji, count, mine}], most used first (uses prefetched reactions)."""
        me = self.context["request"].user.id
        summary: dict[str, dict] = {}
        for r in obj.reactions.all():
            row = summary.setdefault(r.emoji, {"emoji": r.emoji, "count": 0, "mine": False})
            row["count"] += 1
            row["mine"] = row["mine"] or r.user_id == me
        return sorted(summary.values(), key=lambda row: -row["count"])

    def get_is_mine(self, obj) -> bool:
        return obj.sender_id == self.context["request"].user.id

    def get_reply_to(self, obj) -> dict | None:
        quoted = obj.reply_to
        if not quoted:
            return None
        if quoted.deleted_at and not self.context.get("audit"):
            return {"id": quoted.id, "sender_name": display_name(quoted.sender), "text": "", "attachment_kind": "", "deleted": True}
        return {
            "id": quoted.id,
            "sender_name": display_name(quoted.sender),
            "text": quoted.text[:200],
            "attachment_kind": quoted.attachment_kind,
        }

    def get_seen_count(self, obj) -> int | None:
        """How many others have seen one of *my* messages (markers passed in
        by the view, so this is one query per page, not per message)."""
        markers = self.context.get("read_markers")
        if markers is None or obj.sender_id != self.context["request"].user.id:
            return None
        return sum(1 for user_id, last in markers if user_id != obj.sender_id and last >= obj.id)

    def get_attachment_url(self, obj) -> str | None:
        # Private storage: a short-lived signed link, only ever handed to
        # someone the view already checked is in this conversation.
        return obj.attachment.url if obj.attachment else None


class SendMessageSerializer(serializers.Serializer):
    text = serializers.CharField(required=False, allow_blank=True, max_length=MAX_TEXT_LENGTH, trim_whitespace=True)
    file = serializers.FileField(required=False)
    voice = serializers.BooleanField(required=False, default=False)
    duration_seconds = serializers.IntegerField(required=False, min_value=0, max_value=60 * 30)
    reply_to = serializers.IntegerField(required=False, allow_null=True)

    def validate(self, attrs):
        text = attrs.get("text", "")
        upload = attrs.get("file")
        if not text and not upload:
            raise serializers.ValidationError("پیام خالی است.")
        if upload:
            ext = _extension(upload.name)
            if attrs.get("voice"):
                if ext not in VOICE_EXTENSIONS:
                    raise serializers.ValidationError({"file": "فرمت پیام صوتی پشتیبانی نمی‌شود."})
                if upload.size > MAX_VOICE_BYTES:
                    raise serializers.ValidationError({"file": "پیام صوتی بیش از حد طولانی است."})
                attrs["kind"] = Message.AttachmentKind.VOICE
            elif ext in IMAGE_EXTENSIONS:
                if upload.size > MAX_IMAGE_BYTES:
                    raise serializers.ValidationError({"file": "حجم عکس بیشتر از ۱۰ مگابایت است."})
                attrs["kind"] = Message.AttachmentKind.IMAGE
            else:
                if ext not in ALLOWED_COURSE_FILE_EXTENSIONS:
                    raise serializers.ValidationError({"file": f"این نوع فایل پشتیبانی نمی‌شود: .{ext or '?'}"})
                if upload.size > MAX_FILE_BYTES:
                    raise serializers.ValidationError({"file": "حجم فایل بیشتر از ۵۰ مگابایت است."})
                attrs["kind"] = Message.AttachmentKind.FILE
        return attrs


class ConversationSerializer(serializers.ModelSerializer):
    """List/detail row. Expects the queryset annotated by services.annotate_for."""

    title = serializers.SerializerMethodField()
    subtitle = serializers.SerializerMethodField()
    avatar = serializers.SerializerMethodField()
    unread = serializers.IntegerField(read_only=True)
    others_last_read = serializers.IntegerField(read_only=True)
    members = serializers.SerializerMethodField()
    last_message = serializers.SerializerMethodField()
    pinned = serializers.SerializerMethodField()
    can_send = serializers.SerializerMethodField()
    can_manage = serializers.SerializerMethodField()

    class Meta:
        model = Conversation
        fields = (
            "id", "kind", "title", "subtitle", "avatar", "members",
            "unread", "others_last_read", "last_message", "last_message_at",
            "announcement_only", "pinned", "can_send", "can_manage",
        )

    def _viewer(self):
        return self.context["request"].user

    def _owner(self):
        # Same for every row; look it up once per response, not per conversation.
        if "site_owner" not in self.context:
            from apps.instructors.site import get_site_owner

            self.context["site_owner"] = get_site_owner()
        return self.context["site_owner"]

    def _peer(self, obj):
        other = obj.members.exclude(user=self._viewer()).select_related("user").first()
        return other.user if other else None

    def get_title(self, obj) -> str:
        if obj.kind == Conversation.Kind.COURSE:
            return obj.title or obj.course.title
        if obj.kind == Conversation.Kind.CUSTOM:
            return obj.title or "گروه"
        if obj.kind == Conversation.Kind.PEER:
            peer = self._peer(obj)
            return display_name(peer) if peer else "هم‌کلاسی"
        if services.is_teacher(self._viewer()):
            return display_name(obj.student)
        owner = self._owner()
        return display_name(owner.user) if owner else "استاد"

    def get_subtitle(self, obj) -> str:
        if obj.kind == Conversation.Kind.COURSE:
            return "گروه دوره"
        if obj.kind == Conversation.Kind.CUSTOM:
            return "گروه هم‌کلاسی‌ها" if obj.private else "گروه"
        if obj.kind == Conversation.Kind.PEER:
            return "گفت‌وگوی خصوصی با هم‌کلاسی"
        return obj.student.email if services.is_teacher(self._viewer()) else "گفت‌وگوی خصوصی با استاد"

    def get_avatar(self, obj) -> str | None:
        if obj.avatar:
            return obj.avatar.url
        if obj.kind == Conversation.Kind.COURSE:
            return obj.course.cover_image.url if obj.course.cover_image else None
        if obj.kind == Conversation.Kind.CUSTOM:
            return None
        if obj.kind == Conversation.Kind.PEER:
            peer = self._peer(obj)
            return peer.avatar.url if peer and peer.avatar else None
        if services.is_teacher(self._viewer()):
            return obj.student.avatar.url if obj.student.avatar else None
        owner = self._owner()
        return owner.cover_image.url if owner and owner.cover_image else None

    def get_members(self, obj) -> int:
        return services.member_count(obj)

    def get_last_message(self, obj) -> dict | None:
        message = services.last_message(obj)
        if not message:
            return None
        return {
            "id": message.id,
            "text": message.text,
            "attachment_kind": message.attachment_kind,
            "sender_name": display_name(message.sender),
            "is_mine": message.sender_id == self._viewer().id,
            "created_at": message.created_at,
        }

    def get_pinned(self, obj) -> dict | None:
        message = obj.pinned_message
        if not message:
            return None
        return {
            "id": message.id,
            "text": message.text,
            "attachment_kind": message.attachment_kind,
            "sender_name": display_name(message.sender),
        }

    def get_can_send(self, obj) -> bool:
        return services.can_send(self._viewer(), obj)

    def get_can_manage(self, obj) -> bool:
        return services.can_manage(self._viewer(), obj)


class MemberSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    name = serializers.SerializerMethodField()
    email = serializers.EmailField()
    avatar = serializers.SerializerMethodField()
    is_teacher = serializers.SerializerMethodField()

    def get_name(self, user) -> str:
        return display_name(user)

    def get_avatar(self, user) -> str | None:
        return user.avatar.url if user.avatar else None

    def get_is_teacher(self, user) -> bool:
        return services.is_teacher(user)


class GroupSettingsSerializer(serializers.ModelSerializer):
    """What the teacher can change on a group. `title`/`avatar` apply to
    custom groups; course groups keep their course's name and cover."""

    member_ids = serializers.ListField(child=serializers.IntegerField(), required=False, write_only=True)

    class Meta:
        model = Conversation
        fields = ("title", "avatar", "announcement_only", "member_ids")


class AuditMessageSerializer(MessageSerializer):
    """The teacher's chat report: everything, including deleted content."""

    deleted_at = serializers.DateTimeField(read_only=True)
    deleted_by_name = serializers.SerializerMethodField()

    class Meta(MessageSerializer.Meta):
        fields = MessageSerializer.Meta.fields + ("deleted_at", "deleted_by_name")

    def get_deleted_by_name(self, obj) -> str:
        return display_name(obj.deleted_by) if obj.deleted_by else ""
