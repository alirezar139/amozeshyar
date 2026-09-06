from rest_framework import serializers

from apps.courses.serializers import PublicCourseListSerializer

from .models import Enrollment, LessonProgress, WishlistItem


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


class LessonProgressUpdateSerializer(serializers.Serializer):
    lesson_id = serializers.IntegerField()
    position_seconds = serializers.IntegerField(min_value=0)


class LessonProgressResponseSerializer(serializers.ModelSerializer):
    lesson_id = serializers.IntegerField(read_only=True)

    class Meta:
        model = LessonProgress
        fields = ("lesson_id", "position_seconds", "completed")


class ContinueLearningSerializer(serializers.Serializer):
    course_slug = serializers.CharField()
    course_title = serializers.CharField()
    lesson_id = serializers.IntegerField()
    lesson_title = serializers.CharField()
    position_seconds = serializers.IntegerField()
