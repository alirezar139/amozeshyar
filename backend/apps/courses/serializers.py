from datetime import timedelta

from django.utils import timezone
from rest_framework import serializers

from .models import Category, ClassSession, Course, Lesson


class CategorySerializer(serializers.ModelSerializer):
    course_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = Category
        fields = ("id", "name", "slug", "parent", "image", "course_count")


class LessonSerializer(serializers.ModelSerializer):
    has_video = serializers.SerializerMethodField()
    video_id = serializers.SerializerMethodField()
    video_status = serializers.SerializerMethodField()
    progress_seconds = serializers.SerializerMethodField()
    completed = serializers.SerializerMethodField()

    class Meta:
        model = Lesson
        fields = (
            "id", "course", "title", "order", "is_free_preview", "attachment",
            "has_video", "video_id", "video_status", "progress_seconds", "completed",
        )
        read_only_fields = ("id",)

    def get_has_video(self, obj) -> bool:
        return hasattr(obj, "video_asset")

    def get_video_id(self, obj) -> int | None:
        return obj.video_asset.id if hasattr(obj, "video_asset") else None

    def get_video_status(self, obj) -> str | None:
        return obj.video_asset.status if hasattr(obj, "video_asset") else None

    def _progress(self, obj):
        request = self.context.get("request")
        user = getattr(request, "user", None)
        if not user or not user.is_authenticated:
            return None
        from apps.enrollments.models import LessonProgress

        return LessonProgress.objects.filter(student=user, lesson=obj).first()

    def get_progress_seconds(self, obj) -> int:
        progress = self._progress(obj)
        return progress.position_seconds if progress else 0

    def get_completed(self, obj) -> bool:
        progress = self._progress(obj)
        return bool(progress and progress.completed)


class PublicCourseListSerializer(serializers.ModelSerializer):
    category_name = serializers.CharField(source="category.name", read_only=True)
    is_enrolled = serializers.SerializerMethodField()

    class Meta:
        model = Course
        fields = (
            "id", "slug", "title", "subtitle", "category_name", "level", "price",
            "discount_price", "effective_price", "cover_image", "rating_avg",
            "total_duration_seconds", "is_enrolled",
        )

    def get_is_enrolled(self, obj) -> bool:
        request = self.context.get("request")
        user = getattr(request, "user", None)
        if not user or not user.is_authenticated:
            return False
        from apps.enrollments.models import Enrollment

        return Enrollment.objects.filter(student=user, course=obj, is_active=True).exists()


class PublicCourseDetailSerializer(PublicCourseListSerializer):
    lessons = LessonSerializer(many=True, read_only=True)

    class Meta(PublicCourseListSerializer.Meta):
        fields = PublicCourseListSerializer.Meta.fields + ("description", "lessons")


class CourseManageSerializer(serializers.ModelSerializer):
    """Admin (the site's instructor): create/edit any course. New courses
    belong to the site owner and go live immediately unless created as a
    draft; flipping `status` to published stamps `published_at`."""

    class Meta:
        model = Course
        fields = (
            "id", "slug", "category", "title", "subtitle", "description", "level",
            "price", "discount_price", "cover_image", "preview_seconds_override", "status",
        )
        read_only_fields = ("id", "slug")

    def validate_status(self, value):
        if value not in (Course.Status.DRAFT, Course.Status.PUBLISHED):
            raise serializers.ValidationError("Status must be draft or published.")
        return value

    def create(self, validated_data):
        from apps.instructors.site import get_site_owner

        owner = get_site_owner()
        if owner is None:
            raise serializers.ValidationError("Site owner not set up yet — run `manage.py setup_site`.")
        validated_data["instructor"] = owner
        validated_data.setdefault("status", Course.Status.PUBLISHED)
        if validated_data["status"] == Course.Status.PUBLISHED:
            validated_data["published_at"] = timezone.now()
        return super().create(validated_data)

    def update(self, instance, validated_data):
        if validated_data.get("status") == Course.Status.PUBLISHED and instance.status != Course.Status.PUBLISHED:
            validated_data["published_at"] = timezone.now()
        return super().update(instance, validated_data)


class ClassSessionSerializer(serializers.ModelSerializer):
    """Admin-facing CRUD for a course's scheduled sessions.

    `course` stays a writable id (needed to create/move a session), while
    `course_title` is a read-only convenience so a calendar view spanning
    every course doesn't need a second lookup per session just to label it.
    """

    course_title = serializers.CharField(source="course.title", read_only=True)

    class Meta:
        model = ClassSession
        fields = (
            "id", "course", "course_title",
            "title", "starts_at", "ends_at", "is_online", "location_note",
        )
        read_only_fields = ("id",)

    def validate_starts_at(self, value):
        # Nothing in the model itself constrains the year, so a stray
        # Jalali year typed into a Gregorian-only datetime picker (seen in
        # practice: a session dated 621 years in the past) sails through
        # as a "valid" datetime — Django and Postgres are both happy to
        # store it. The real damage shows up later, client-side: a date
        # that old predates Iran's standard time zone, so Python computes
        # its historical Local Mean Time offset (down to the second),
        # which isn't a well-formed ISO offset and breaks the browser's
        # own Date parser entirely. A generous but finite window closes
        # this off at the source instead of relying on every consumer to
        # defend against garbage dates forever.
        now = timezone.now()
        if not (now - timedelta(days=365) <= value <= now + timedelta(days=365 * 5)):
            raise serializers.ValidationError("زمان کلاس باید بین یک سال گذشته تا پنج سال آینده باشد.")
        return value


class StudentScheduleSerializer(serializers.ModelSerializer):
    """Read-only shape for a student's own calendar — bundles just enough
    course context to render the session without a second lookup."""

    course_title = serializers.CharField(source="course.title", read_only=True)
    course_slug = serializers.CharField(source="course.slug", read_only=True)

    class Meta:
        model = ClassSession
        fields = (
            "id", "title", "starts_at", "ends_at", "is_online", "location_note",
            "course_title", "course_slug",
        )
