from django.contrib.auth.models import AbstractUser
from django.core.validators import RegexValidator
from django.db import models

from .managers import UserManager

iranian_mobile_validator = RegexValidator(
    regex=r"^09\d{9}$",
    message="Enter a valid Iranian mobile number (e.g. 09123456789).",
)


class User(AbstractUser):
    """Custom user, keyed by email, carrying the platform-wide role."""

    class Role(models.TextChoices):
        STUDENT = "student", "Student"
        INSTRUCTOR = "instructor", "Instructor"
        ADMIN = "admin", "Admin"

    username = None
    email = models.EmailField(unique=True)
    role = models.CharField(max_length=20, choices=Role.choices, default=Role.STUDENT)
    phone_number = models.CharField(
        max_length=11, blank=True, validators=[iranian_mobile_validator]
    )
    is_email_verified = models.BooleanField(default=False)
    avatar = models.ImageField(upload_to="avatars/", blank=True, null=True)
    # Self-reported at signup for non-instructor roles (instructors provide
    # a resume instead — see InstructorProfile.resume). Free text rather
    # than a fixed taxonomy since there's no course-tagging system to match
    # it against yet; kept simple until that exists.
    interests = models.TextField(blank=True)

    class ColorTheme(models.TextChoices):
        TEAL = "teal", "Teal & Amber"
        BLUE = "blue", "Blue & Rose"
        PURPLE = "purple", "Purple & Gold"
        MONO = "mono", "Monochrome & Amber"

    # Per-account accent palette (frontend maps this to a `data-palette`
    # attribute driving CSS custom properties — see useTheme.ts). Persisted
    # server-side, not just localStorage, so it follows the user across
    # devices once logged in.
    color_theme = models.CharField(max_length=20, choices=ColorTheme.choices, default=ColorTheme.TEAL)

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = []

    objects = UserManager()

    def __str__(self):
        return self.email

    @property
    def is_instructor(self) -> bool:
        return self.role == self.Role.INSTRUCTOR

    @property
    def is_student(self) -> bool:
        return self.role == self.Role.STUDENT
