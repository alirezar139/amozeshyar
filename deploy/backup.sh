#!/usr/bin/env bash
# Backup for one instructor site. Install on the host:
#   install -m 700 deploy/backup.sh /usr/local/bin/amozeshyar-backup
#   echo '30 3 * * * root /usr/local/bin/amozeshyar-backup >> /var/log/amozeshyar-backup.log 2>&1' \
#       > /etc/cron.d/amozeshyar-backup
# (deploy/release.sh installs both.)
#
#   amozeshyar-backup                       # nightly: database + media, then off-site
#   amozeshyar-backup --db-only --label X   # just the database, named ..._X (release does this
#                                           # before every migration)
#
# Database: pg_dump (custom format), checked by listing it back with pg_restore before it counts
# as a backup, with a .sha256 next to it; kept KEEP_DAYS days. Media: rsync mirror of the MinIO
# volume without --delete, so a file removed by mistake in the app is still in the backup.
# Off-site: when OFFSITE_REMOTE is set (in /etc/amozeshyar-backup.conf), both are copied to that
# rclone remote — ideally a `crypt` remote, so the copy leaving the server is encrypted.
# Every run appends sizes and durations to the log and rewrites $BACKUP_DIR/last-backup.env,
# which deploy/monitor.sh reads. See deploy/README.md for setting it up and for restoring.
set -euo pipefail
umask 077

CONF=${CONF:-/etc/amozeshyar-backup.conf}
if [ -f "$CONF" ]; then
    # shellcheck source=/dev/null
    . "$CONF"
fi

BACKUP_DIR=${BACKUP_DIR:-/var/backups/amozeshyar}
KEEP_DAYS=${KEEP_DAYS:-14}
POSTGRES_CONTAINER=${POSTGRES_CONTAINER:-amozeshyar-postgres-1}
MINIO_VOLUME=${MINIO_VOLUME:-amozeshyar_minio-data}
OFFSITE_REMOTE=${OFFSITE_REMOTE:-}      # e.g. "offsite-crypt:" — empty skips the off-site copy
OFFSITE_BWLIMIT=${OFFSITE_BWLIMIT:-0}   # e.g. "2M" so the upload doesn't starve the site; 0 = no limit

DB_ONLY=0
LABEL=""
while [ $# -gt 0 ]; do
    case "$1" in
        --db-only) DB_ONLY=1 ;;
        --label) LABEL="_${2//[^A-Za-z0-9._-]/}"; shift ;;
        *) echo "unknown option: $1" >&2; exit 2 ;;
    esac
    shift
done

log() { echo "$(date '+%F %T') $*"; }
human() { numfmt --to=iec --suffix=B "$1" 2>/dev/null || echo "${1}B"; }

mkdir -p "$BACKUP_DIR/db" "$BACKUP_DIR/media"
chmod 700 "$BACKUP_DIR"

stamp=$(date +%Y-%m-%d_%H%M%S)
# Written to a temp name first: a dump cut short (disk full, container down) must never sit
# next to the good ones looking complete, nor be shipped off-site.
dump="$BACKUP_DIR/db/amozeshyar_${stamp}${LABEL}.dump"
trap 'rm -f "$dump.partial"' EXIT

t0=$(date +%s)
docker exec "$POSTGRES_CONTAINER" pg_dump -U amozeshyar -d amozeshyar --format=custom > "$dump.partial"
# A dump pg_restore can't read is not a backup.
entries=$(docker exec -i "$POSTGRES_CONTAINER" pg_restore --list < "$dump.partial" | grep -cE '^[0-9]+;' || true)
if [ "${entries:-0}" -lt 10 ]; then
    log "ERROR: the database dump looks broken (only ${entries:-0} entries); keeping the previous backups"
    exit 1
fi
mv "$dump.partial" "$dump"
(cd "$BACKUP_DIR/db" && sha256sum "$(basename "$dump")" > "$(basename "$dump").sha256")
db_bytes=$(stat -c %s "$dump")
db_seconds=$(( $(date +%s) - t0 ))
find "$BACKUP_DIR/db" -name 'amozeshyar_*.dump*' -mtime +"$KEEP_DAYS" -delete
log "database ok: $(basename "$dump"), $(human "$db_bytes"), $entries entries, ${db_seconds}s"

media_bytes=""
media_seconds=""
if [ "$DB_ONLY" = 0 ]; then
    t0=$(date +%s)
    media_src=$(docker volume inspect "$MINIO_VOLUME" --format '{{ .Mountpoint }}')
    rsync -a "$media_src/" "$BACKUP_DIR/media/"
    media_seconds=$(( $(date +%s) - t0 ))
    media_bytes=$(du -sb "$BACKUP_DIR/media" | cut -f1)
    log "media ok: $(human "$media_bytes") mirrored in ${media_seconds}s"
fi

offsite="skipped"
if [ "$DB_ONLY" = 0 ] && [ -n "$OFFSITE_REMOTE" ]; then
    case "$OFFSITE_REMOTE" in *: | */) ;; *) OFFSITE_REMOTE="$OFFSITE_REMOTE/" ;; esac
    t0=$(date +%s)
    # db: sync, so the remote keeps the same KEEP_DAYS as here instead of growing forever.
    # media: copy (never deletes), same reasoning as the local rsync above. Only new or
    # changed files travel, so after the first run this is just the day's uploads.
    rclone sync "$BACKUP_DIR/db" "${OFFSITE_REMOTE}db" --bwlimit "$OFFSITE_BWLIMIT" --exclude '*.partial'
    rclone copy "$BACKUP_DIR/media" "${OFFSITE_REMOTE}media" --bwlimit "$OFFSITE_BWLIMIT"
    offsite="ok in $(( $(date +%s) - t0 ))s"
    log "off-site copy $offsite: $OFFSITE_REMOTE"
fi

# For deploy/monitor.sh: when the last good backup happened.
cat > "$BACKUP_DIR/last-backup.env.tmp" <<EOF
LAST_DB_BACKUP_AT=$(date +%s)
LAST_DB_BACKUP_FILE=$(basename "$dump")
LAST_DB_BACKUP_BYTES=$db_bytes
LAST_DB_BACKUP_SECONDS=$db_seconds
EOF
if [ "$DB_ONLY" = 0 ]; then
    cat >> "$BACKUP_DIR/last-backup.env.tmp" <<EOF
LAST_FULL_BACKUP_AT=$(date +%s)
LAST_MEDIA_BYTES=$media_bytes
LAST_MEDIA_SECONDS=$media_seconds
LAST_OFFSITE="$offsite"
EOF
elif [ -f "$BACKUP_DIR/last-backup.env" ]; then
    grep -E '^(LAST_FULL_BACKUP_AT|LAST_MEDIA_|LAST_OFFSITE)' "$BACKUP_DIR/last-backup.env" >> "$BACKUP_DIR/last-backup.env.tmp" || true
fi
mv "$BACKUP_DIR/last-backup.env.tmp" "$BACKUP_DIR/last-backup.env"
log "backup ok: $stamp${LABEL}"
