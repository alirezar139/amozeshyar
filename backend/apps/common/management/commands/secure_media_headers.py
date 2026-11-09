"""Re-type the files already in the media bucket with the server-chosen headers.

Files uploaded before `file_types.storage_headers` existed carry whatever
Content-Type the uploader's browser sent, possibly text/html. This sniffs
the first bytes of every object and, where its stored ContentType or
ContentDisposition differs from what the server would choose today, rewrites
only those headers (an in-place S3 copy with MetadataDirective=REPLACE: the
bytes and the key stay as they are, nothing is deleted).

    python manage.py secure_media_headers            # report only
    python manage.py secure_media_headers --apply    # rewrite the headers
"""
from io import BytesIO

from django.conf import settings
from django.core.files.storage import default_storage
from django.core.management.base import BaseCommand, CommandError

from apps.common.file_types import SNIFF_BYTES, storage_headers


class Command(BaseCommand):
    help = "Fix ContentType/ContentDisposition of stored media to the server-chosen values (dry run unless --apply)."

    def add_arguments(self, parser):
        parser.add_argument("--apply", action="store_true", help="Rewrite the headers (default: only report).")
        parser.add_argument("--prefix", default="", help="Only objects whose key starts with this.")

    def handle(self, *args, apply: bool, prefix: str, **options):
        if not hasattr(default_storage, "bucket"):
            raise CommandError("The default storage isn't S3/MinIO; nothing to fix.")
        client = default_storage.bucket.meta.client
        bucket = settings.AWS_STORAGE_BUCKET_NAME

        checked = changed = 0
        for page in client.get_paginator("list_objects_v2").paginate(Bucket=bucket, Prefix=prefix):
            for item in page.get("Contents", []):
                key = item["Key"]
                checked += 1
                head = client.head_object(Bucket=bucket, Key=key)
                sample = b""
                if item.get("Size"):
                    body = client.get_object(Bucket=bucket, Key=key, Range=f"bytes=0-{SNIFF_BYTES - 1}")["Body"]
                    sample = body.read()
                wanted = storage_headers(key, BytesIO(sample))
                current = {"ContentType": head.get("ContentType", ""), "ContentDisposition": head.get("ContentDisposition", "")}
                target = {"ContentType": wanted["ContentType"], "ContentDisposition": wanted.get("ContentDisposition", "")}
                if current == target and not head.get("ContentEncoding"):
                    continue
                changed += 1
                self.stdout.write(
                    f"{key}: {current['ContentType'] or '-'} [{current['ContentDisposition'] or 'inline'}]"
                    f" -> {target['ContentType']} [{target['ContentDisposition'] or 'inline'}]"
                )
                if apply:
                    client.copy_object(
                        Bucket=bucket,
                        Key=key,
                        CopySource={"Bucket": bucket, "Key": key},
                        MetadataDirective="REPLACE",
                        Metadata=head.get("Metadata", {}),
                        **wanted,
                    )

        verb = "fixed" if apply else "would fix (run again with --apply)"
        self.stdout.write(self.style.SUCCESS(f"{checked} objects checked, {changed} {verb}."))
