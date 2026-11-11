#!/usr/bin/env bash
# The server half of a release (deploy/release.sh runs it over SSH). From the repository root:
#
#   bash deploy/server-release.sh deploy <commit-sha>   # switch to that commit's images
#   bash deploy/server-release.sh rollback              # back to the images that ran before
#
# deploy:
#   1. remember the running IMAGE_TAG (deploy/.release-history) and pull the new images;
#   2. back up the database (amozeshyar-backup --db-only), and stop if that fails;
#   3. run the migrations with the NEW image while the OLD app keeps serving (migrations here are
#      additive, so the old code keeps working on the new schema for those seconds);
#   4. switch the containers;
#   5. wait for backend and frontend to report healthy; if they don't, switch back to the
#      previous images automatically and exit 1.
# rollback: switches to the previous images. The database stays as it is; if a migration has
#   to be undone too, restore the pre-release dump: bash deploy/restore.sh --db <that dump>.
set -euo pipefail

COMPOSE=${COMPOSE:-docker compose -f deploy/docker-compose.prod.yml --env-file deploy/.env}
ENV_FILE=${ENV_FILE:-deploy/.env}
HISTORY=${HISTORY:-deploy/.release-history}
BACKUP_CMD=${BACKUP_CMD:-/usr/local/bin/amozeshyar-backup}
HEALTH_WAIT=${HEALTH_WAIT:-180}   # seconds to wait for healthy containers
PROJECT=${PROJECT:-amozeshyar}
PULL=${PULL:-1}                   # 0: use images already on this machine (testing)

log() { echo "== $*"; }

current_tag() { grep -m1 '^IMAGE_TAG=' "$ENV_FILE" | cut -d= -f2 || true; }

set_tag() {
    if grep -q '^IMAGE_TAG=' "$ENV_FILE"; then
        sed -i "s|^IMAGE_TAG=.*|IMAGE_TAG=$1|" "$ENV_FILE"
    else
        echo "IMAGE_TAG=$1" >> "$ENV_FILE"
    fi
}

container_health() {
    docker inspect --format '{{if .State.Health}}{{.State.Health.Status}}{{else}}{{.State.Status}}{{end}}' "$PROJECT-$1-1" 2>/dev/null || echo missing
}

restarts() { docker inspect --format '{{.RestartCount}}' "$PROJECT-$1-1" 2>/dev/null || echo 0; }

# Healthy within HEALTH_WAIT, or fail as soon as a container crashes: an app that can't boot
# exits and is restarted at once, and waiting out the whole timeout would only keep the site
# down longer before the rollback.
wait_healthy() {
    local deadline=$(( $(date +%s) + HEALTH_WAIT ))
    while [ "$(date +%s)" -lt "$deadline" ]; do
        local b f svc
        b=$(container_health backend) f=$(container_health frontend)
        if [ "$b" = healthy ] && [ "$f" = healthy ]; then
            return 0
        fi
        for svc in backend frontend worker worker-video; do
            if [ "$(restarts "$svc")" -gt 0 ] || [ "$(container_health "$svc")" = exited ] || [ "$(container_health "$svc")" = unhealthy ]; then
                echo "$svc crashed or is unhealthy (restarts: $(restarts "$svc"))."
                return 1
            fi
        done
        sleep 3
    done
    echo "backend: $(container_health backend), frontend: $(container_health frontend)"
    return 1
}

switch_to() {
    set_tag "$1"
    $COMPOSE up -d --no-build --remove-orphans
}

deploy() {
    local new=$1 prev
    prev=$(current_tag)
    log "release ${new:0:7} (running: ${prev:0:7})"
    [ "$PULL" = 1 ] && IMAGE_TAG=$new $COMPOSE pull --quiet backend frontend

    log "backup before migrating"
    if [ -n "$BACKUP_CMD" ]; then
        $BACKUP_CMD --db-only --label "pre-${new:0:7}" || { echo "Stop: backup failed, nothing was changed."; exit 1; }
    fi

    log "migrations (new code, old app still serving)"
    $COMPOSE up -d --no-build postgres redis minio minio-init
    IMAGE_TAG=$new $COMPOSE run --rm --no-deps backend python manage.py migrate --noinput

    log "switching containers"
    echo "$(date '+%F %T') ${new} previous=${prev}" >> "$HISTORY"
    switch_to "$new"

    log "waiting for the new containers to be healthy"
    if ! wait_healthy; then
        echo "The new release is not healthy: rolling back to ${prev:0:7}."
        $COMPOSE logs --tail 40 backend frontend || true
        if [ -n "$prev" ]; then
            switch_to "$prev"
            echo "$(date '+%F %T') ${prev} previous=${new} (automatic rollback)" >> "$HISTORY"
            wait_healthy && echo "Rolled back; the site runs ${prev:0:7} again." || echo "Rollback also unhealthy: check now."
        fi
        exit 1
    fi
    $COMPOSE ps --format '{{.Service}}: {{.Status}}'
    log "released ${new:0:7}"
}

rollback() {
    local cur prev
    cur=$(current_tag)
    # The release that brought the current images in (not a rollback line), and what ran before it.
    prev=$(grep -v "rollback)" "$HISTORY" 2>/dev/null | grep " ${cur} previous=" | tail -1 | sed -E 's/.*previous=([^ ]*).*/\1/' || true)
    [ -n "$prev" ] || { echo "No earlier release recorded in $HISTORY."; exit 1; }
    log "rolling back ${cur:0:7} -> ${prev:0:7} (database unchanged)"
    switch_to "$prev"
    echo "$(date '+%F %T') ${prev} previous=${cur} (manual rollback)" >> "$HISTORY"
    wait_healthy || { echo "Not healthy after rollback: check now."; exit 1; }
    log "running ${prev:0:7}"
}

case "${1:-}" in
    deploy) deploy "${2:?commit sha}" ;;
    rollback) rollback ;;
    *) echo "usage: $0 deploy <sha> | rollback" >&2; exit 2 ;;
esac
