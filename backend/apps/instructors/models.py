from django.conf import settings
from django.db import models
from django.utils.text import slugify

from apps.common.models import TimeStampedModel


class InstructorProfile(TimeStampedModel):
    """Public marketing profile for an instructor.

    A profile starts life as `pending_review` (product decision: courses and
    instructor pages only go public after an admin approves them, to keep
    quality/trust high on the marketplace) and only becomes visible on public
    pages / the sitemap once `status == APPROVED`.
    """

    class Status(models.TextChoices):
        PENDING_REVIEW = "pending_review", "Pending review"
        APPROVED = "approved", "Approved"
        REJECTED = "rejected", "Rejected"

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="instructor_profile"
    )
    slug = models.SlugField(unique=True, blank=True)
    headline = models.CharField(max_length=255, blank=True)
    bio = models.TextField(blank=True)
    credentials = models.JSONField(default=list, blank=True)  # [{"title": ..., "issuer": ..., "year": ...}]
    cover_image = models.ImageField(upload_to="instructor_covers/", blank=True, null=True)
    social_links = models.JSONField(default=dict, blank=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING_REVIEW)
    rejection_reason = models.TextField(blank=True)
    rating_avg = models.DecimalField(max_digits=3, decimal_places=2, default=0)
    total_students = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ("-created_at",)

    def __str__(self):
        return self.user.get_full_name() or self.user.email

    def save(self, *args, **kwargs):
        if not self.slug:
            base_slug = slugify(self.user.get_full_name() or self.user.email.split("@")[0], allow_unicode=True)
            slug = base_slug
            counter = 1
            while InstructorProfile.objects.filter(slug=slug).exclude(pk=self.pk).exists():
                counter += 1
                slug = f"{base_slug}-{counter}"
            self.slug = slug
        super().save(*args, **kwargs)

    @property
    def is_public(self) -> bool:
        return self.status == self.Status.APPROVED
