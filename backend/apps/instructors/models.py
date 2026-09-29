from django.conf import settings
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.utils.text import slugify

from apps.common.models import TimeStampedModel


class InstructorProfile(TimeStampedModel):
    """Public profile of the instructor who owns this install.

    Each instructor gets their own install of the software, so exactly one
    profile is the site owner (`is_site_owner`): its name, headline, bio and
    cover are what the homepage presents, and every course belongs to it.
    `status`/`resume`/`intro_video`/`admin_quality_score` are leftovers from
    the old multi-instructor marketplace's review flow, kept only so existing
    rows migrate cleanly.
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
    # Required at instructor signup (enforced in the frontend form + the
    # owner-facing serializer) so admin has something concrete to review
    # before approving the profile/their courses — never exposed on the
    # public profile serializer, only to the instructor themself and admin.
    resume = models.FileField(upload_to="instructor_resumes/", blank=True, null=True)
    # A short self-introduction/teaching-sample video — same reasoning as
    # the resume: required so admin has something to actually judge
    # teaching quality from, not just credentials on paper.
    intro_video = models.FileField(upload_to="instructor_intro_videos/", blank=True, null=True)
    social_links = models.JSONField(default=dict, blank=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING_REVIEW)
    rejection_reason = models.TextField(blank=True)
    # Admin's own 1-5 judgment of the intro video/resume at review time —
    # distinct from `rating_avg`, which is students' post-course rating and
    # only exists once they've actually taken a course from this instructor.
    admin_quality_score = models.PositiveSmallIntegerField(
        null=True, blank=True, validators=[MinValueValidator(1), MaxValueValidator(5)]
    )
    rating_avg = models.DecimalField(max_digits=3, decimal_places=2, default=0)
    total_students = models.PositiveIntegerField(default=0)
    is_site_owner = models.BooleanField(default=False)

    class Meta:
        ordering = ("-created_at",)
        constraints = [
            models.UniqueConstraint(
                fields=("is_site_owner",),
                condition=models.Q(is_site_owner=True),
                name="single_site_owner",
            ),
        ]

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
