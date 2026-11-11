"""Find (and with --apply, delete) video files no lesson uses any more (VID-01).

Before this cleanup existed, replacing or deleting a lesson's video left its original (up to
2 GB), HLS segments and preview in storage. New deletions clean up after themselves (signals.py);
this command is for what piled up before, and as a periodic safety net.

    python manage.py cleanup_video_files                 # report only
    python manage.py cleanup_video_files --apply         # delete what the report lists

Only keys under lessons/ are considered; a key inside any remaining video's folder is never
listed; and nothing younger than --min-age-hours (default 24) is listed, since an upload in
progress is stored before its VideoAsset row exists.
"""
from datetime import timedelta

from django.core.files.storage import default_storage
from django.core.management.base import BaseCommand, CommandError

from apps.videos.services.cleanup import delete_keys, find_orphans


class Command(BaseCommand):
    help = "List video files no lesson uses (dry run unless --apply)."

    def add_arguments(self, parser):
        parser.add_argument("--apply", action="store_true", help="Delete the listed files.")
        parser.add_argument("--min-age-hours", type=int, default=24)

    def handle(self, *args, apply: bool, min_age_hours: int, **options):
        if not hasattr(default_storage, "bucket"):
            raise CommandError("The default storage isn't S3/MinIO.")
        if min_age_hours < 1:
            raise CommandError("--min-age-hours must be at least 1.")
        orphans = find_orphans(timedelta(hours=min_age_hours))
        total = sum(o["size"] for o in orphans)
        for o in orphans[:50]:
            self.stdout.write(f"{o['key']}  {o['size'] / 1e6:.1f} MB  {o['modified']:%Y-%m-%d}")
        if len(orphans) > 50:
            self.stdout.write(f"... and {len(orphans) - 50} more")
        if apply:
            delete_keys([o["key"] for o in orphans])
        verb = "deleted" if apply else "would be deleted (run again with --apply)"
        self.stdout.write(self.style.SUCCESS(f"{len(orphans)} files, {total / 1e9:.2f} GB {verb}."))
