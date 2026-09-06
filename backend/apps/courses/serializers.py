from rest_framework import serializers

from .models import Category, Course, Lesson


class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ("id", "name", "slug", "parent")


class LessonSerializer(serializers.ModelSerializer):
    has_video = serializers.SerializerMethodField()

    class Meta:
        model = Lesson
        fields = ("id", "course", "title", "order", "is_free_preview", "attachment", "has_video")
        read_only_fields = ("id",)

    def get_has_video(self, obj) -> bool:
        return hasattr(obj, "video_asset")


class PublicCourseListSerializer(serializers.ModelSerializer):
    instructor_name = serializers.CharField(source="instructor.user.get_full_name", read_only=True)
    instructor_slug = serializers.CharField(source="instructor.slug", read_only=True)
    category_name = serializers.CharField(source="category.name", read_only=True)

    class Meta:
        model = Course
        fields = (
            "id", "slug", "title", "subtitle", "category_name", "level", "price",
            "discount_price", "effective_price", "cover_image", "rating_avg",
            "total_duration_seconds", "instructor_name", "instructor_slug",
        )


class PublicCourseDetailSerializer(PublicCourseListSerializer):
    lessons = LessonSerializer(many=True, read_only=True)

    class Meta(PublicCourseListSerializer.Meta):
        fields = PublicCourseListSerializer.Meta.fields + ("description", "lessons")


class CourseWriteSerializer(serializers.ModelSerializer):
    """Used by the instructor panel to create/edit a course.

    Any create/edit forces the course back to `pending_review` — this is
    intentional: the admin-approval gate applies to every published change,
    not just the first submission, so an instructor can't sneak edits past
    moderation once approved.
    """

    class Meta:
        model = Course
        fields = (
            "id", "category", "title", "subtitle", "description", "level",
            "price", "discount_price", "cover_image", "preview_seconds_override", "status",
        )
        read_only_fields = ("id", "status")

    def create(self, validated_data):
        validated_data["instructor"] = self.context["request"].user.instructor_profile
        validated_data["status"] = Course.Status.PENDING_REVIEW
        return super().create(validated_data)

    def update(self, instance, validated_data):
        validated_data["status"] = Course.Status.PENDING_REVIEW
        return super().update(instance, validated_data)


class CourseModerationSerializer(serializers.ModelSerializer):
    instructor_name = serializers.CharField(source="instructor.user.get_full_name", read_only=True)

    class Meta:
        model = Course
        fields = (
            "id", "title", "subtitle", "price", "instructor_name",
            "status", "rejection_reason",
        )
        read_only_fields = ("title", "subtitle", "price", "instructor_name")

    def validate(self, attrs):
        if attrs.get("status") == Course.Status.REJECTED and not attrs.get("rejection_reason"):
            raise serializers.ValidationError({"rejection_reason": "Required when rejecting a course."})
        return attrs

    def save(self, **kwargs):
        from django.utils import timezone

        if self.validated_data.get("status") == Course.Status.PUBLISHED:
            kwargs["published_at"] = timezone.now()
        return super().save(**kwargs)
