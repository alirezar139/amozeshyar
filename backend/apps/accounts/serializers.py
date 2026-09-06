from django.contrib.auth.password_validation import validate_password
from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer

from .models import User


class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, validators=[validate_password])

    class Meta:
        model = User
        fields = ("id", "email", "password", "first_name", "last_name", "role", "phone_number", "interests")
        read_only_fields = ("id",)

    def validate_role(self, value):
        # Public registration may only self-select student/instructor;
        # admin accounts are provisioned separately (createsuperuser / admin panel).
        if value == User.Role.ADMIN:
            raise serializers.ValidationError("Cannot self-register as admin.")
        return value

    def create(self, validated_data):
        return User.objects.create_user(**validated_data)


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = (
            "id", "email", "first_name", "last_name", "role", "phone_number",
            "avatar", "is_email_verified", "interests",
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
