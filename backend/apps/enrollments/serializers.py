from rest_framework import serializers

from apps.courses.serializers import PublicCourseListSerializer

from .models import Enrollment, WishlistItem


class EnrollmentSerializer(serializers.ModelSerializer):
    course = PublicCourseListSerializer(read_only=True)

    class Meta:
        model = Enrollment
        fields = ("id", "course", "access_granted_at", "is_active")


class WishlistItemSerializer(serializers.ModelSerializer):
    course = PublicCourseListSerializer(read_only=True)
    course_id = serializers.IntegerField(write_only=True)

    class Meta:
        model = WishlistItem
        fields = ("id", "course", "course_id", "created_at")

    def create(self, validated_data):
        validated_data["student"] = self.context["request"].user
        validated_data["course_id"] = validated_data.pop("course_id")
        return super().create(validated_data)
