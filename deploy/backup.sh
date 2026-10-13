#!/usr/bin/env bash
# Nightly backup for one instructor site. Install on the host:
#   install -m 700 deploy/backup.sh /usr/local/bin/amozeshyar-backup
#   echo '30 3 * * * root /usr/local/bin/amozeshyar-backup' > /etc/cron.d/amozeshyar-backup
# Database: compressed pg_dump, last 14 kept. Media: rsync mirror of the MinIO volume without
# --delete, so a file removed by mistake in the app is still in the backup.
# Both live on the same disk; copy BACKUP_DIR off the box regularly for real disaster recovery.
set -euo pipefail
umask 077

BACKUP_DIR=${BACKUP_DIR:-/var/backups/amozeshyar}
KEEP_DAYS=${KEEP_DAYS:-14}
MINIO_VOLUME=${MINIO_VOLUME:-amozeshyar_minio-data}

mkdir -p "$BACKUP_DIR/db" "$BACKUP_DIR/media"
chmod 700 "$BACKUP_DIR"

stamp=$(date +%Y-%m-%d_%H%M)
docker exec amozeshyar-postgres-1 pg_dump -U amozeshyar -d amozeshyar --format=custom \
    > "$BACKUP_DIR/db/amozeshyar_$stamp.dump"
find "$BACKUP_DIR/db" -name 'amozeshyar_*.dump' -mtime +"$KEEP_DAYS" -delete

media_src=$(docker volume inspect "$MINIO_VOLUME" --format '{{ .Mountpoint }}')
rsync -a "$media_src/" "$BACKUP_DIR/media/"

echo "backup ok: $stamp"
