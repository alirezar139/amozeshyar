import re

from rest_framework import serializers

from .models import InstructorProfile


class PublicInstructorSerializer(serializers.ModelSerializer):
    """Read-only shape exposed on public marketing pages — no PII beyond what the instructor chose to publish."""

    display_name = serializers.SerializerMethodField()
    phone_number = serializers.CharField(source="user.phone_number", read_only=True)
    # The owner's profile photo; the homepage shows it when no separate cover_image is set.
    avatar = serializers.ImageField(source="user.avatar", read_only=True)

    class Meta:
        model = InstructorProfile
        fields = (
            "slug",
            "display_name",
            "site_name",
            "logo",
            "background_style",
            "background_colors",
            "background_image",
            "background_motion",
            "background_speed",
            "allow_peer_chat",
            "headline",
            "bio",
            "credentials",
            "cover_image",
            "avatar",
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
        fields = (
            "site_name", "logo", "headline", "bio", "credentials", "cover_image", "social_links",
            "background_style", "background_colors", "background_image", "background_motion", "background_speed",
            "allow_peer_chat",
        )

    def validate_background_colors(self, value):
        if not isinstance(value, list) or len(value) > 3 or not all(
            isinstance(c, str) and re.fullmatch(r"#[0-9a-fA-F]{6}", c) for c in value
        ):
            raise serializers.ValidationError("حداکثر سه رنگ، به شکل کد هگز مثل #157e6c.")
        return value
