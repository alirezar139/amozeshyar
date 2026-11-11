#!/usr/bin/env bash
# Release origin/main to the production server, from the laptop:
#   bash deploy/release.sh                 # code + backup + migrate + switch + health check
#   bash deploy/release.sh --rollback      # back to the images that ran before (database unchanged)
#   APK=path/to/app-release.apk bash deploy/release.sh   # ...and publish the Android app
# The work on the server is deploy/server-release.sh (backup before migrating, migrations before
# switching containers, automatic rollback if the new containers don't become healthy).
# Every step is safe to repeat. Same steps as docs/architecture.md «انتشار نسخه‌ی جدید».
set -euo pipefail
SERVER=${SERVER:-root@modaresyar-org.site}
SITE=${SITE:-https://modaresyar-org.site}
REMOTE_DIR=/srv/amozeshyar
COMPOSE="docker compose -f deploy/docker-compose.prod.yml --env-file deploy/.env"

cd "$(git rev-parse --show-toplevel)"

if [ "${1:-}" = "--rollback" ]; then
    ssh "$SERVER" "cd $REMOTE_DIR && bash deploy/server-release.sh rollback"
    curl -fsS "$SITE/api/v1/health/" && echo
    exit 0
fi

git fetch -q origin
if [ "$(git rev-parse HEAD)" != "$(git rev-parse origin/main)" ]; then
    echo "Stop: check out main at origin/main first (git checkout main && git pull)."; exit 1
fi
if [ -n "$(git status --porcelain --untracked-files=no)" ]; then
    echo "Stop: uncommitted changes; git archive would ship HEAD without them."; exit 1
fi

SHA=$(git rev-parse HEAD)
echo "== 0/4 waiting for GitHub Actions to build the images of ${SHA:0:7}"
# The server can't build reliably (PyPI/npm time out there); .github/workflows/images.yml does.
RUN_ID=""
for _ in $(seq 30); do
    RUN_ID=$(gh run list --workflow images.yml --commit "$SHA" --limit 1 --json databaseId -q '.[0].databaseId')
    [ -n "$RUN_ID" ] && break
    sleep 10
done
[ -n "$RUN_ID" ] || { echo "Stop: no Images run for $SHA"; exit 1; }
gh run watch "$RUN_ID" --exit-status --interval 20 > /dev/null || { echo "Stop: image build failed, see gh run view $RUN_ID"; exit 1; }

echo "== 1/4 uploading ${SHA:0:7}"
git archive --format=tar HEAD | ssh "$SERVER" "tar -x -C $REMOTE_DIR"

echo "== 2/4 settings, scheduled jobs, then backup, migrate, switch and health check"
# ssh joins its arguments into one remote command line, so quote the values for that shell.
ssh "$SERVER" "$(printf 'SITE=%q REMOTE_DIR=%q SHA=%q bash -s' "$SITE" "$REMOTE_DIR" "$SHA")" <<'REMOTE'
set -euo pipefail
cd "$REMOTE_DIR"
E=deploy/.env
# ZarinPal returns the buyer to the API, which then redirects to this page.
URL="$SITE/checkout/callback"
if ! grep -qx "ZARINPAL_CALLBACK_URL=$URL" "$E"; then
    cp "$E" "$E.bak-$(date +%F-%H%M)"
    if grep -q '^ZARINPAL_CALLBACK_URL=' "$E"; then
        sed -i "s|^ZARINPAL_CALLBACK_URL=.*|ZARINPAL_CALLBACK_URL=$URL|" "$E"
    else
        echo "ZARINPAL_CALLBACK_URL=$URL" >> "$E"
    fi
    echo "set ZARINPAL_CALLBACK_URL"
fi
install -m 700 deploy/backup.sh /usr/local/bin/amozeshyar-backup
echo '30 3 * * * root /usr/local/bin/amozeshyar-backup >> /var/log/amozeshyar-backup.log 2>&1' > /etc/cron.d/amozeshyar-backup
install -m 700 deploy/monitor.sh /usr/local/bin/amozeshyar-monitor
echo '*/5 * * * * root /usr/local/bin/amozeshyar-monitor >> /var/log/amozeshyar-monitor.log 2>&1' > /etc/cron.d/amozeshyar-monitor
bash deploy/server-release.sh deploy "$SHA"
REMOTE

echo "== 3/4 Android app"
if [ -n "${APK:-}" ]; then
    ssh "$SERVER" "cd $REMOTE_DIR && $COMPOSE exec -T backend python manage.py publish_android_app -" < "$APK"
else
    echo "(skipped; set APK=path/to/app-release.apk to publish one)"
fi

echo "== 4/4 checking the live site"
curl -fsS "$SITE/api/v1/health/" && echo
for path in / /manifest.webmanifest "/checkout/callback?status=paid"; do
    curl -fsS -o /dev/null -w "%{http_code} $path\n" "$SITE$path"
done
curl -sS -o /dev/null -w "%{http_code} /api/v1/site/android.apk (302 = published, 404 = none yet)\n" "$SITE/api/v1/site/android.apk"
echo "== done (undo with: bash deploy/release.sh --rollback)"
