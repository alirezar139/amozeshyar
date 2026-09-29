from django.shortcuts import get_object_or_404
from django.utils import timezone
from drf_spectacular.utils import extend_schema
from rest_framework import permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import NotFound, ValidationError
from rest_framework.response import Response

from apps.accounts.authentication import UploadJWTAuthentication
from apps.accounts.models import User

from . import services
from .models import Conversation, Message
from .serializers import ConversationSerializer, MessageSerializer, SendMessageSerializer

PAGE = 40


class ConversationViewSet(viewsets.ReadOnlyModelViewSet):
    """Chat between students and the teacher: private conversations and
    one group per course. Clients poll `messages/?after=` for new messages."""

    serializer_class = ConversationSerializer
    permission_classes = (permissions.IsAuthenticated,)
    pagination_class = None

    def get_authenticators(self):
        # Sending a voice note or file is an upload; see UploadJWTAuthentication.
        if self.request and self.request.method == "POST" and self.request.path.endswith("/messages/"):
            return [UploadJWTAuthentication()]
        return super().get_authenticators()

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):
            return Conversation.objects.none()
        user = self.request.user
        conversations = services.visible_conversations(user).select_related("student", "course")
        return services.annotate_for(conversations, user)

    def _conversation(self, pk) -> Conversation:
        conversation = get_object_or_404(Conversation.objects.select_related("student", "course"), pk=pk)
        if not services.can_access(self.request.user, conversation):
            raise NotFound()
        return conversation

    @action(detail=False, methods=["get"])
    def unread(self, request):
        return Response({"total": services.unread_total(request.user)})

    @action(detail=False, methods=["post"])
    def start(self, request):
        """Open (or create) a private conversation: a student with the
        teacher, or the teacher with `student_id`."""
        if services.is_teacher(request.user):
            student = get_object_or_404(User, pk=request.data.get("student_id"), role=User.Role.STUDENT)
        else:
            student = request.user
        conversation = services.get_or_create_direct(student)
        row = services.annotate_for(Conversation.objects.filter(pk=conversation.pk).select_related("student", "course"), request.user).get()
        return Response(self.get_serializer(row).data)

    @extend_schema(request=SendMessageSerializer, responses=MessageSerializer)
    @action(detail=True, methods=["get", "post"])
    def messages(self, request, pk=None):
        conversation = self._conversation(pk)
        if request.method == "POST":
            return self._send(request, conversation)

        messages = conversation.messages.select_related("sender")
        after, before = request.query_params.get("after"), request.query_params.get("before")
        if after:
            page = list(messages.filter(id__gt=int(after)).order_by("id")[:200])
        else:
            if before:
                messages = messages.filter(id__lt=int(before))
            page = list(messages.order_by("-id")[:PAGE])[::-1]
        others_last_read = (
            services.annotate_for(Conversation.objects.filter(pk=conversation.pk), request.user)
            .values_list("others_last_read", flat=True)
            .get()
        )
        return Response({
            "messages": MessageSerializer(page, many=True, context={"request": request}).data,
            "has_more": bool(page) and not after and conversation.messages.filter(id__lt=page[0].id).exists(),
            "others_last_read": others_last_read,
        })

    def _send(self, request, conversation):
        payload = SendMessageSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        data = payload.validated_data
        upload = data.get("file")
        message = Message.objects.create(
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
        return Response(MessageSerializer(message, context={"request": request}).data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=["post"])
    def read(self, request, pk=None):
        conversation = self._conversation(pk)
        message_id = request.data.get("message_id")
        try:
            message_id = int(message_id) if message_id is not None else None
        except (TypeError, ValueError) as e:
            raise ValidationError({"message_id": "Invalid id."}) from e
        return Response({"last_read_message_id": services.mark_read(conversation, request.user, message_id)})
