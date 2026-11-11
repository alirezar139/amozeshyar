#!/usr/bin/env bash
# Read-only snapshot of the server's resources, to size the memory limits in
# deploy/docker-compose.prod.yml. Changes nothing and prints no secrets. On the server:
#   bash /srv/amozeshyar/deploy/server-report.sh
set -uo pipefail
PROJECT=${PROJECT:-amozeshyar}

echo "== host"; echo "cpus: $(nproc)"; free -m; swapon --show 2>/dev/null || true
echo; echo "== disk"; df -h / /var/lib/docker /var/backups 2>/dev/null | sort -u
echo; echo "== containers (memory used / limit)"
docker stats --no-stream --format 'table {{.Name}}\t{{.MemUsage}}\t{{.MemPerc}}\t{{.CPUPerc}}'
echo; echo "== restarts / health"
for c in $(docker ps -a --format '{{.Names}}' | grep "^$PROJECT-"); do
    docker inspect --format "$c {{.State.Status}} {{if .State.Health}}{{.State.Health.Status}}{{end}} restarts={{.RestartCount}} oom={{.State.OOMKilled}}" "$c"
done
echo; echo "== other containers on this host (they share the RAM)"
docker ps --format '{{.Names}}' | grep -v "^$PROJECT-" || echo "(none)"
echo; echo "== data size"
for v in postgres-data minio-data redis-data; do
    mp=$(docker volume inspect "${PROJECT}_$v" --format '{{.Mountpoint}}' 2>/dev/null) && echo "$v: $(du -sh "$mp" 2>/dev/null | cut -f1)"
done
du -sh /var/backups/amozeshyar/db /var/backups/amozeshyar/media 2>/dev/null
echo; echo "== last backups"; tail -6 /var/log/amozeshyar-backup.log 2>/dev/null || echo "(no backup log)"
echo; echo "== kernel OOM kills (last 7 days)"
journalctl -k --since "7 days ago" 2>/dev/null | grep -ci "killed process" || dmesg 2>/dev/null | grep -ci "killed process" || true
