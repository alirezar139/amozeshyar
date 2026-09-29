from django.conf import settings
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

    class Meta:
        model = Message
        fields = (
            "id", "conversation", "sender", "is_mine", "text",
            "attachment_kind", "attachment_name", "attachment_size", "attachment_url", "duration_seconds",
            "created_at",
        )

    def get_is_mine(self, obj) -> bool:
        return obj.sender_id == self.context["request"].user.id

    def get_attachment_url(self, obj) -> str | None:
        # Private storage: a short-lived signed link, only ever handed to
        # someone the view already checked is in this conversation.
        return obj.attachment.url if obj.attachment else None


class SendMessageSerializer(serializers.Serializer):
    text = serializers.CharField(required=False, allow_blank=True, max_length=MAX_TEXT_LENGTH, trim_whitespace=True)
    file = serializers.FileField(required=False)
    voice = serializers.BooleanField(required=False, default=False)
    duration_seconds = serializers.IntegerField(required=False, min_value=0, max_value=60 * 30)

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

    class Meta:
        model = Conversation
        fields = (
            "id", "kind", "title", "subtitle", "avatar", "members",
            "unread", "others_last_read", "last_message", "last_message_at",
        )

    def _viewer(self):
        return self.context["request"].user

    def _owner(self):
        # Same for every row; look it up once per response, not per conversation.
        if "site_owner" not in self.context:
            from apps.instructors.site import get_site_owner

            self.context["site_owner"] = get_site_owner()
        return self.context["site_owner"]

    def get_title(self, obj) -> str:
        if obj.kind == Conversation.Kind.COURSE:
            return obj.course.title
        if services.is_teacher(self._viewer()):
            return display_name(obj.student)
        owner = self._owner()
        return display_name(owner.user) if owner else "استاد"

    def get_subtitle(self, obj) -> str:
        if obj.kind == Conversation.Kind.COURSE:
            return "گروه دوره"
        return obj.student.email if services.is_teacher(self._viewer()) else "گفتگوی خصوصی با استاد"

    def get_avatar(self, obj) -> str | None:
        if obj.kind == Conversation.Kind.COURSE:
            return obj.course.cover_image.url if obj.course.cover_image else None
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
