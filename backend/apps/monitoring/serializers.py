from rest_framework import serializers

from .models import ErrorEvent, SupportReport

MAX_BROWSER_EVENTS = 30


class ErrorEventSerializer(serializers.ModelSerializer):
    class Meta:
        model = ErrorEvent
        fields = (
            "id", "created_at", "source", "level", "method", "path", "status",
            "user_label", "message", "detail", "page_url",
        )


class ClientErrorSerializer(serializers.Serializer):
    """What the browser reports (see frontend/plugins/live-log.client.ts)."""

    level = serializers.ChoiceField(choices=("error", "warning"), default="error")
    kind = serializers.CharField(max_length=40, default="error")
    message = serializers.CharField(max_length=2000, allow_blank=True, default="")
    detail = serializers.CharField(max_length=8000, allow_blank=True, required=False, allow_null=True)
    url = serializers.CharField(max_length=300, allow_blank=True, default="")


class SupportReportSerializer(serializers.ModelSerializer):
    events = ErrorEventSerializer(many=True, read_only=True)

    class Meta:
        model = SupportReport
        fields = (
            "id", "created_at", "user_label", "message", "page_url", "user_agent",
            "browser_events", "events", "resolved", "resolved_at",
        )
        read_only_fields = ("id", "created_at", "user_label", "user_agent", "events", "resolved_at")

    def validate_message(self, value):
        value = value.strip()
        if not value:
            raise serializers.ValidationError("توضیح مشکل را بنویسید.")
        if len(value) > 4000:
            raise serializers.ValidationError("توضیح حداکثر ۴۰۰۰ کاراکتر است.")
        return value

    def validate_browser_events(self, value):
        if not isinstance(value, list):
            raise serializers.ValidationError("فرمت نامعتبر.")
        cleaned = []
        for item in value[:MAX_BROWSER_EVENTS]:
            if isinstance(item, dict):
                cleaned.append({k: str(item.get(k, ""))[:2000] for k in ("at", "level", "kind", "message", "detail")})
        return cleaned


class ResolveReportSerializer(serializers.ModelSerializer):
    class Meta:
        model = SupportReport
        fields = ("id", "resolved", "resolved_at")
        read_only_fields = ("id", "resolved_at")
