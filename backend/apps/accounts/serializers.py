from django.contrib.auth.password_validation import validate_password
from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer

from .models import User


class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, validators=[validate_password])

    class Meta:
        model = User
        fields = ("id", "email", "password", "first_name", "last_name", "role", "phone_number", "interests")
        read_only_fields = ("id", "role")

    def create(self, validated_data):
        # Public sign-up is always a student of this site's instructor; the
        # instructor (admin) and developer accounts come from `setup_site`.
        return User.objects.create_user(**validated_data, role=User.Role.STUDENT)


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = (
            "id", "email", "first_name", "last_name", "role", "phone_number",
            "avatar", "is_email_verified", "interests",
            "primary_color", "accent_color", "header_color", "nav_color",
        )
        read_only_fields = ("id", "email", "role", "is_email_verified")


class AdminUserSerializer(serializers.ModelSerializer):
    """Admin's user directory row: only `role` and `is_active` are editable here.

    Everything else (email, name...) is read-only from this screen — role
    management is scoped to exactly what it says, not a general user editor.
    """

    class Meta:
        model = User
        fields = ("id", "email", "first_name", "last_name", "role", "is_active", "date_joined", "phone_number")
        read_only_fields = ("id", "email", "first_name", "last_name", "date_joined", "phone_number")

    def validate_role(self, value):
        if value == User.Role.INSTRUCTOR:
            raise serializers.ValidationError("This site has a single instructor; pick student or admin.")
        return value


class CaptchaChallengeSerializer(serializers.Serializer):
    token = serializers.CharField()
    background = serializers.CharField(help_text="data: URL, JPEG")
    piece = serializers.CharField(help_text="data: URL, PNG with alpha")
    piece_y = serializers.IntegerField()
    width = serializers.IntegerField()
    height = serializers.IntegerField()
    piece_size = serializers.IntegerField()


class CaptchaVerifyRequestSerializer(serializers.Serializer):
    token = serializers.CharField()
    x = serializers.FloatField()


class CaptchaNumberChallengeSerializer(serializers.Serializer):
    token = serializers.CharField()
    image = serializers.CharField(help_text="data: URL, JPEG")
    length = serializers.IntegerField()


class CaptchaVerifyNumberRequestSerializer(serializers.Serializer):
    token = serializers.CharField()
    code = serializers.CharField()


class CaptchaPassSerializer(serializers.Serializer):
    pass_token = serializers.CharField()


class RefreshResponseSerializer(serializers.Serializer):
    access = serializers.CharField()


class EmailTokenObtainPairSerializer(TokenObtainPairSerializer):
    """JWT login serializer keyed by email, embedding the role in the token payload."""

    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)
        token["role"] = user.role
        token["email"] = user.email
        return token
