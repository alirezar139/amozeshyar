import sys
from io import BytesIO

from django.core.management.base import BaseCommand, CommandError

from apps.instructors import android_app


class Command(BaseCommand):
    """Put a signed APK where the site's footer link downloads it from.

    Run on the server after a release build, e.g. from the laptop:
        cat app-release.apk | ssh SERVER 'cd /srv/amozeshyar && docker compose ... exec -T backend \
            python manage.py publish_android_app -'
    """

    help = "Publish the Android app (APK) for download from the site. Pass a path, or - for stdin."

    def add_arguments(self, parser):
        parser.add_argument("apk", help="Path to the .apk, or - to read it from stdin")

    def handle(self, *args, apk, **options):
        if apk == "-":
            data = sys.stdin.buffer.read()
        else:
            try:
                with open(apk, "rb") as fh:
                    data = fh.read()
            except OSError as exc:
                raise CommandError(f"Can't read {apk}: {exc}") from exc
        if not data.startswith(b"PK"):  # an APK is a zip archive
            raise CommandError("That isn't an APK file.")

        android_app.publish(BytesIO(data))
        self.stdout.write(self.style.SUCCESS(f"Published the Android app ({len(data) // 1024} KB)."))
