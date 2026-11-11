#!/usr/bin/env bash
# Restore one instructor site from a backup made by deploy/backup.sh. Run on the server, from the
# repository root (/srv/amozeshyar), after `docker compose ... up -d` has created the containers:
#
#   bash deploy/restore.sh                       # latest dump + the media mirror
#   bash deploy/restore.sh --db FILE.dump        # a specific dump (e.g. a pre-release one)
#   bash deploy/restore.sh --db-only             # leave the media files as they are
#   bash deploy/restore.sh --yes                 # don't ask (scripts)
#
# It stops the app (backend, workers, frontend), checks the dump's checksum, restores the
# database (pg_restore --clean: the tables are replaced by the dump's), copies the media mirror
# into the MinIO volume (adding and overwriting files, never deleting any), starts everything
# again and prints row counts for a quick check. To restore from the off-site copy on a new
# server, first `rclone copy offsite-crypt:db` / `:media` into BACKUP_DIR (deploy/README.md).
set -euo pipefail

BACKUP_DIR=${BACKUP_DIR:-/var/backups/amozeshyar}
COMPOSE=${COMPOSE:-docker compose -f deploy/docker-compose.prod.yml --env-file deploy/.env}
POSTGRES_CONTAINER=${POSTGRES_CONTAINER:-amozeshyar-postgres-1}
MINIO_VOLUME=${MINIO_VOLUME:-amozeshyar_minio-data}

DUMP=""
MEDIA=1
YES=0
while [ $# -gt 0 ]; do
    case "$1" in
        --db) DUMP="$2"; shift ;;
        --db-only) MEDIA=0 ;;
        --yes) YES=1 ;;
        *) echo "unknown option: $1" >&2; exit 2 ;;
    esac
    shift
done

log() { echo "$(date '+%F %T') $*"; }

if [ -z "$DUMP" ]; then
    DUMP=$(ls -1t "$BACKUP_DIR"/db/amozeshyar_*.dump 2>/dev/null | head -1 || true)
fi
[ -f "$DUMP" ] || { echo "No dump found (looked in $BACKUP_DIR/db)."; exit 1; }
if [ -f "$DUMP.sha256" ]; then
    (cd "$(dirname "$DUMP")" && sha256sum -c --quiet "$(basename "$DUMP").sha256") || { echo "Checksum mismatch: $DUMP is damaged."; exit 1; }
fi

echo "Restore database from: $DUMP ($(du -h "$DUMP" | cut -f1))"
[ "$MEDIA" = 1 ] && echo "Restore media from:    $BACKUP_DIR/media ($(du -sh "$BACKUP_DIR/media" | cut -f1))"
echo "The site is offline while this runs; the current database is replaced."
if [ "$YES" != 1 ]; then
    read -r -p "Type RESTORE to continue: " answer
    [ "$answer" = "RESTORE" ] || { echo "Cancelled."; exit 1; }
fi

t0=$(date +%s)
log "stopping the app"
$COMPOSE stop backend worker worker-video frontend >/dev/null 2>&1 || true
$COMPOSE up -d postgres minio >/dev/null

log "restoring the database"
docker exec -i "$POSTGRES_CONTAINER" pg_restore -U amozeshyar -d amozeshyar --clean --if-exists --no-owner --exit-on-error < "$DUMP"

if [ "$MEDIA" = 1 ]; then
    log "restoring media files"
    $COMPOSE stop minio >/dev/null
    target=$(docker volume inspect "$MINIO_VOLUME" --format '{{ .Mountpoint }}')
    rsync -a "$BACKUP_DIR/media/" "$target/"
    $COMPOSE up -d minio >/dev/null
fi

log "starting the app"
$COMPOSE up -d --no-build >/dev/null
log "restore finished in $(( $(date +%s) - t0 ))s; row counts:"
docker exec "$POSTGRES_CONTAINER" psql -U amozeshyar -d amozeshyar -At -F ' ' -c "
    SELECT 'users', count(*) FROM accounts_user UNION ALL
    SELECT 'courses', count(*) FROM courses_course UNION ALL
    SELECT 'enrollments', count(*) FROM enrollments_enrollment UNION ALL
    SELECT 'paid orders', count(*) FROM payments_order WHERE status = 'paid' UNION ALL
    SELECT 'videos', count(*) FROM videos_videoasset"
