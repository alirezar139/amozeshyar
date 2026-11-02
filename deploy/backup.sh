#!/usr/bin/env bash
# Nightly backup for one instructor site. Install on the host:
#   install -m 700 deploy/backup.sh /usr/local/bin/amozeshyar-backup
#   echo '30 3 * * * root /usr/local/bin/amozeshyar-backup >> /var/log/amozeshyar-backup.log 2>&1' \
#       > /etc/cron.d/amozeshyar-backup
# Database: compressed pg_dump, last 14 kept. Media: rsync mirror of the MinIO volume without
# --delete, so a file removed by mistake in the app is still in the backup.
# Off-site: when OFFSITE_REMOTE is set (in /etc/amozeshyar-backup.conf), both are copied to that
# rclone remote — ideally a `crypt` remote, so the copy leaving the server is encrypted.
# See deploy/README.md for setting it up and for restoring.
set -euo pipefail
umask 077

CONF=${CONF:-/etc/amozeshyar-backup.conf}
if [ -f "$CONF" ]; then
    # shellcheck source=/dev/null
    . "$CONF"
fi

BACKUP_DIR=${BACKUP_DIR:-/var/backups/amozeshyar}
KEEP_DAYS=${KEEP_DAYS:-14}
MINIO_VOLUME=${MINIO_VOLUME:-amozeshyar_minio-data}
OFFSITE_REMOTE=${OFFSITE_REMOTE:-}      # e.g. "offsite-crypt:" — empty skips the off-site copy
OFFSITE_BWLIMIT=${OFFSITE_BWLIMIT:-0}   # e.g. "2M" so the upload doesn't starve the site; 0 = no limit

mkdir -p "$BACKUP_DIR/db" "$BACKUP_DIR/media"
chmod 700 "$BACKUP_DIR"

stamp=$(date +%Y-%m-%d_%H%M)
# Written to a temp name first: a dump cut short (disk full, container down) must never sit
# next to the good ones looking complete, nor be shipped off-site.
dump="$BACKUP_DIR/db/amozeshyar_$stamp.dump"
trap 'rm -f "$dump.partial"' EXIT
docker exec amozeshyar-postgres-1 pg_dump -U amozeshyar -d amozeshyar --format=custom > "$dump.partial"
mv "$dump.partial" "$dump"
find "$BACKUP_DIR/db" -name 'amozeshyar_*.dump' -mtime +"$KEEP_DAYS" -delete

media_src=$(docker volume inspect "$MINIO_VOLUME" --format '{{ .Mountpoint }}')
rsync -a "$media_src/" "$BACKUP_DIR/media/"

echo "$(date '+%F %T') local backup ok: $stamp"

if [ -n "$OFFSITE_REMOTE" ]; then
    case "$OFFSITE_REMOTE" in *: | */) ;; *) OFFSITE_REMOTE="$OFFSITE_REMOTE/" ;; esac
    # db: sync, so the remote keeps the same 14 days as here instead of growing forever.
    # media: copy (never deletes), same reasoning as the local rsync above. Only new or
    # changed files travel, so after the first run this is just the day's uploads.
    rclone sync "$BACKUP_DIR/db" "${OFFSITE_REMOTE}db" --bwlimit "$OFFSITE_BWLIMIT" --exclude '*.partial'
    rclone copy "$BACKUP_DIR/media" "${OFFSITE_REMOTE}media" --bwlimit "$OFFSITE_BWLIMIT"
    echo "$(date '+%F %T') off-site copy ok: $OFFSITE_REMOTE"
fi
