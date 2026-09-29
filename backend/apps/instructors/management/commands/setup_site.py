import os

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from apps.accounts.models import User
from apps.courses.models import Course
from apps.instructors.models import InstructorProfile


class Command(BaseCommand):
    """Turn a fresh install into one instructor's site. Safe to re-run.

    Creates (or updates) two accounts:
      - the instructor: an admin who owns the site's public profile and courses;
      - the developer: a superuser taken from DEVELOPER_EMAIL/DEVELOPER_PASSWORD,
        hidden from the instructor's user list so they can't lock it out.

    Passwords of accounts that already exist are left alone.
    """

    help = "Create the site owner (instructor) and the developer account for this install."

    def add_arguments(self, parser):
        parser.add_argument("--email", required=True, help="Instructor's login email")
        parser.add_argument("--password", help="Instructor's password (required when the account is new)")
        parser.add_argument("--first-name", default="")
        parser.add_argument("--last-name", default="")
        parser.add_argument("--headline", default="", help="e.g. «مدرس برنامه‌نویسی پایتون»")
        parser.add_argument(
            "--adopt-courses",
            action="store_true",
            help="Reassign every existing course to this instructor (when converting an old multi-instructor DB)",
        )

    @transaction.atomic
    def handle(self, *args, **opts):
        owner_user = self._upsert_user(
            opts["email"], opts["password"], first_name=opts["first_name"], last_name=opts["last_name"],
        )

        InstructorProfile.objects.filter(is_site_owner=True).exclude(user=owner_user).update(is_site_owner=False)
        profile, _ = InstructorProfile.objects.get_or_create(user=owner_user)
        profile.is_site_owner = True
        profile.status = InstructorProfile.Status.APPROVED
        if opts["headline"]:
            profile.headline = opts["headline"]
        profile.save()
        self.stdout.write(self.style.SUCCESS(f"Site owner: {owner_user.email}"))

        if opts["adopt_courses"]:
            moved = Course.objects.exclude(instructor=profile).update(instructor=profile)
            self.stdout.write(f"Reassigned {moved} course(s) to the site owner.")

        dev_email = os.environ.get("DEVELOPER_EMAIL")
        if dev_email:
            dev = self._upsert_user(dev_email, os.environ.get("DEVELOPER_PASSWORD"), superuser=True)
            self.stdout.write(self.style.SUCCESS(f"Developer: {dev.email}"))
        else:
            self.stdout.write(self.style.WARNING("DEVELOPER_EMAIL not set — no developer account created."))

    def _upsert_user(self, email, password, superuser=False, **names):
        user = User.objects.filter(email__iexact=email).first()
        if user is None:
            if not password:
                raise CommandError(f"{email} doesn't exist yet — a password is required to create it.")
            user = User.objects.create_user(email=email, password=password)
        user.role = User.Role.ADMIN
        user.is_active = True
        if superuser:
            user.is_staff = user.is_superuser = True
        for field, value in names.items():
            if value:
                setattr(user, field, value)
        user.save()
        return user
