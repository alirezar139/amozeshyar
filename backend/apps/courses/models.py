from django.db import models
from django.utils.text import slugify

from apps.common.models import TimeStampedModel
from apps.instructors.models import InstructorProfile


class Category(TimeStampedModel):
    name = models.CharField(max_length=100)
    slug = models.SlugField(unique=True, blank=True)
    parent = models.ForeignKey("self", null=True, blank=True, on_delete=models.SET_NULL, related_name="children")

    class Meta:
        verbose_name_plural = "categories"
        ordering = ("name",)

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name, allow_unicode=True)
        super().save(*args, **kwargs)


class Course(TimeStampedModel):
    """A sellable course, owned by one instructor.

    Publishing requires admin approval (`status=pending_review` ->
    `published`), matching the product decision to keep marketplace quality
    high rather than letting instructors self-publish instantly.
    """

    class Level(models.TextChoices):
        BEGINNER = "beginner", "Beginner"
        INTERMEDIATE = "intermediate", "Intermediate"
        ADVANCED = "advanced", "Advanced"

    class Status(models.TextChoices):
        DRAFT = "draft", "Draft"
        PENDING_REVIEW = "pending_review", "Pending review"
        PUBLISHED = "published", "Published"
        REJECTED = "rejected", "Rejected"

    instructor = models.ForeignKey(InstructorProfile, on_delete=models.CASCADE, related_name="courses")
    category = models.ForeignKey(Category, on_delete=models.PROTECT, related_name="courses")
    title = models.CharField(max_length=255)
    slug = models.SlugField(unique=True, blank=True)
    subtitle = models.CharField(max_length=255, blank=True)
    description = models.TextField(blank=True)
    level = models.CharField(max_length=20, choices=Level.choices, default=Level.BEGINNER)
    price = models.DecimalField(max_digits=12, decimal_places=0, default=0)  # Toman
    discount_price = models.DecimalField(max_digits=12, decimal_places=0, null=True, blank=True)
    cover_image = models.ImageField(upload_to="course_covers/", blank=True, null=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.DRAFT)
    rejection_reason = models.TextField(blank=True)
    published_at = models.DateTimeField(null=True, blank=True)
    # null => fall back to the global PreviewPolicy.default_preview_seconds
    preview_seconds_override = models.PositiveIntegerField(null=True, blank=True)
    total_duration_seconds = models.PositiveIntegerField(default=0)
    rating_avg = models.DecimalField(max_digits=3, decimal_places=2, default=0)

    class Meta:
        ordering = ("-created_at",)

    def __str__(self):
        return self.title

    def save(self, *args, **kwargs):
        if not self.slug:
            base_slug = slugify(self.title, allow_unicode=True)
            slug = base_slug
            counter = 1
            while Course.objects.filter(slug=slug).exclude(pk=self.pk).exists():
                counter += 1
                slug = f"{base_slug}-{counter}"
            self.slug = slug
        super().save(*args, **kwargs)

    @property
    def is_public(self) -> bool:
        return self.status == self.Status.PUBLISHED

    @property
    def effective_price(self) -> int:
        return self.discount_price if self.discount_price is not None else self.price


class Lesson(TimeStampedModel):
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name="lessons")
    title = models.CharField(max_length=255)
    order = models.PositiveIntegerField(default=0)
    # A lesson explicitly marked free skips the paywall entirely (a marketing
    # sampler chapter), independent of the video-level preview-clip mechanism.
    is_free_preview = models.BooleanField(default=False)
    attachment = models.FileField(upload_to="lesson_attachments/", blank=True, null=True)

    class Meta:
        ordering = ("course", "order")
        unique_together = ("course", "order")

    def __str__(self):
        return f"{self.course.title} - {self.title}"
