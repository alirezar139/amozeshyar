from rest_framework import serializers

from apps.courses.serializers import PublicCourseListSerializer

from .models import Enrollment, LessonProgress, WishlistItem


class EnrollmentSerializer(serializers.ModelSerializer):
    course = PublicCourseListSerializer(read_only=True)
    progress = serializers.SerializerMethodField()

    class Meta:
        model = Enrollment
        fields = ("id", "course", "access_granted_at", "is_active", "progress")

    def get_progress(self, obj) -> dict:
        total = obj.course.lessons.count()
        done = LessonProgress.objects.filter(student=obj.student, lesson__course=obj.course, completed=True).count()
        return {"total_lessons": total, "completed_lessons": done, "percent": round(done * 100 / total) if total else 0}


class UpcomingSessionSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    title = serializers.CharField()
    course_title = serializers.CharField()
    starts_at = serializers.DateTimeField()
    is_online = serializers.BooleanField()


class RecentFileSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    title = serializers.CharField()
    extension = serializers.CharField()
    size_bytes = serializers.IntegerField()
    lesson_title = serializers.CharField()
    course_title = serializers.CharField()
    course_slug = serializers.CharField()
    created_at = serializers.DateTimeField()


class DashboardSummarySerializer(serializers.Serializer):
    courses = serializers.IntegerField()
    completed_lessons = serializers.IntegerField()
    total_lessons = serializers.IntegerField()
    watched_minutes = serializers.IntegerField()
    next_session = UpcomingSessionSerializer(allow_null=True)
    recent_files = RecentFileSerializer(many=True)


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
    position_seconds = serializers.IntegerField(min_value=0, required=False, default=0)
    # Explicit "I finished this" — for lessons without a video, or to un-mark one.
    completed = serializers.BooleanField(required=False, allow_null=True, default=None)


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
