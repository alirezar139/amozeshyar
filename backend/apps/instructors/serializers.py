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


class SiteSettingsSerializer(serializers.ModelSerializer):
    """What the site owner can edit about their public profile. Their name
    lives on the User row and is edited from the regular profile page."""

    class Meta:
        model = InstructorProfile
        fields = ("headline", "bio", "credentials", "cover_image", "social_links")
