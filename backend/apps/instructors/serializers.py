from rest_framework import serializers

from .models import InstructorProfile


class PublicInstructorSerializer(serializers.ModelSerializer):
    """Read-only shape exposed on public marketing pages — no PII beyond what the instructor chose to publish."""

    display_name = serializers.SerializerMethodField()
    phone_number = serializers.CharField(source="user.phone_number", read_only=True)

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
            "phone_number",
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
            "intro_video",
            "status",
            "rejection_reason",
            "rating_avg",
            "total_students",
        )
        read_only_fields = ("id", "slug", "status", "rejection_reason", "rating_avg", "total_students")


class InstructorModerationSerializer(serializers.ModelSerializer):
    """Admin-only serializer for reviewing (resume + intro video), scoring,
    and approving/rejecting an instructor profile."""

    display_name = serializers.SerializerMethodField()

    class Meta:
        model = InstructorProfile
        fields = (
            "id", "display_name", "headline", "bio", "resume", "intro_video",
            "status", "rejection_reason", "admin_quality_score",
        )
        read_only_fields = ("display_name", "headline", "bio", "resume", "intro_video")

    def get_display_name(self, obj) -> str:
        return obj.user.get_full_name() or obj.user.email.split("@")[0]

    def validate(self, attrs):
        status = attrs.get("status")
        if status == InstructorProfile.Status.REJECTED and not attrs.get("rejection_reason"):
            raise serializers.ValidationError({"rejection_reason": "Required when rejecting a profile."})
        if status == InstructorProfile.Status.APPROVED and not (attrs.get("admin_quality_score") or self.instance and self.instance.admin_quality_score):
            raise serializers.ValidationError({"admin_quality_score": "Required when approving a profile."})
        return attrs
