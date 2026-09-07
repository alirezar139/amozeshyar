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
    instructor_name = serializers.CharField(source="instructor.user.get_full_name", read_only=True)
    instructor_slug = serializers.CharField(source="instructor.slug", read_only=True)
    category_name = serializers.CharField(source="category.name", read_only=True)
    is_enrolled = serializers.SerializerMethodField()

    class Meta:
        model = Course
        fields = (
            "id", "slug", "title", "subtitle", "category_name", "level", "price",
            "discount_price", "effective_price", "cover_image", "rating_avg",
            "total_duration_seconds", "instructor_name", "instructor_slug", "is_enrolled",
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


class AdminCourseWriteSerializer(serializers.ModelSerializer):
    """Admin-only: create a course directly, on behalf of any instructor.

    Unlike CourseWriteSerializer, the admin picks the instructor explicitly
    and the course is published immediately — the admin creating it *is*
    the review, so there's no point routing it back through the moderation
    queue the admin would just approve themselves.
    """

    class Meta:
        model = Course
        fields = (
            "id", "instructor", "category", "title", "subtitle", "description", "level",
            "price", "discount_price", "cover_image", "preview_seconds_override", "status",
        )
        read_only_fields = ("id", "status")

    def create(self, validated_data):
        from django.utils import timezone

        validated_data["status"] = Course.Status.PUBLISHED
        validated_data["published_at"] = timezone.now()
        return super().create(validated_data)


class CourseModerationSerializer(serializers.ModelSerializer):
    instructor_name = serializers.CharField(source="instructor.user.get_full_name", read_only=True)
    instructor_resume = serializers.FileField(source="instructor.resume", read_only=True)

    class Meta:
        model = Course
        fields = (
            "id", "title", "subtitle", "price", "instructor_name", "instructor_resume",
            "status", "rejection_reason",
        )
        read_only_fields = ("title", "subtitle", "price", "instructor_name", "instructor_resume")

    def validate(self, attrs):
        if attrs.get("status") == Course.Status.REJECTED and not attrs.get("rejection_reason"):
            raise serializers.ValidationError({"rejection_reason": "Required when rejecting a course."})
        return attrs

    def save(self, **kwargs):
        from django.utils import timezone

        if self.validated_data.get("status") == Course.Status.PUBLISHED:
            kwargs["published_at"] = timezone.now()
        return super().save(**kwargs)


class ClassSessionSerializer(serializers.ModelSerializer):
    """Instructor/admin-facing CRUD for a course's scheduled sessions.

    `course` stays a writable id (needed to create/move a session), while
    `course_title`/`instructor_name` are read-only conveniences so a
    calendar view (e.g. the admin's, spanning every course) doesn't need a
    second lookup per session just to label it.
    """

    course_title = serializers.CharField(source="course.title", read_only=True)
    instructor_name = serializers.CharField(source="course.instructor.user.get_full_name", read_only=True)

    class Meta:
        model = ClassSession
        fields = (
            "id", "course", "course_title", "instructor_name",
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
    instructor_name = serializers.CharField(source="course.instructor.user.get_full_name", read_only=True)

    class Meta:
        model = ClassSession
        fields = (
            "id", "title", "starts_at", "ends_at", "is_online", "location_note",
            "course_title", "course_slug", "instructor_name",
        )
