from rest_framework import serializers

from .models import InstructorProfile


class PublicInstructorSerializer(serializers.ModelSerializer):
    """Read-only shape exposed on public marketing pages — no PII beyond what the instructor chose to publish."""

    display_name = serializers.SerializerMethodField()

    class Meta:
        model = InstructorProfile
        fields = (
            "slug",
            "display_name",
            "headline",
            "bio",
            "credentials",
            "cover_image",
            "social_links",
            "rating_avg",
            "total_students",
        )

    def get_display_name(self, obj) -> str:
        return obj.user.get_full_name() or obj.user.email.split("@")[0]


class InstructorProfileSerializer(serializers.ModelSerializer):
    """Owner-facing serializer used by the instructor panel to edit their own profile."""

    class Meta:
        model = InstructorProfile
        fields = (
            "id",
            "slug",
            "headline",
            "bio",
            "credentials",
            "cover_image",
            "social_links",
            "resume",
            "status",
            "rejection_reason",
            "rating_avg",
            "total_students",
        )
        read_only_fields = ("id", "slug", "status", "rejection_reason", "rating_avg", "total_students")


class InstructorModerationSerializer(serializers.ModelSerializer):
    """Admin-only serializer for approving/rejecting an instructor profile."""

    display_name = serializers.SerializerMethodField()

    class Meta:
        model = InstructorProfile
        fields = ("id", "display_name", "headline", "bio", "resume", "status", "rejection_reason")
        read_only_fields = ("display_name", "headline", "bio", "resume")

    def get_display_name(self, obj) -> str:
        return obj.user.get_full_name() or obj.user.email.split("@")[0]

    def validate(self, attrs):
        if attrs.get("status") == InstructorProfile.Status.REJECTED and not attrs.get("rejection_reason"):
            raise serializers.ValidationError({"rejection_reason": "Required when rejecting a profile."})
        return attrs
