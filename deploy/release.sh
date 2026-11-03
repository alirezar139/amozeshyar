#!/usr/bin/env bash
# Release origin/main to the production server, from the laptop:
#   bash deploy/release.sh                 # code + build + migrate + checks
#   APK=path/to/app-release.apk bash deploy/release.sh   # ...and publish the Android app
# Every step is safe to repeat. Same steps as docs/architecture.md «انتشار نسخه‌ی جدید».
set -euo pipefail
SERVER=${SERVER:-root@modaresyar-org.site}
SITE=${SITE:-https://modaresyar-org.site}
REMOTE_DIR=/srv/amozeshyar
COMPOSE="docker compose -f deploy/docker-compose.prod.yml --env-file deploy/.env"

cd "$(git rev-parse --show-toplevel)"
git fetch -q origin
if [ "$(git rev-parse HEAD)" != "$(git rev-parse origin/main)" ]; then
    echo "Stop: check out main at origin/main first (git checkout main && git pull)."; exit 1
fi
if [ -n "$(git status --porcelain --untracked-files=no)" ]; then
    echo "Stop: uncommitted changes; git archive would ship HEAD without them."; exit 1
fi

echo "== 1/4 uploading $(git rev-parse --short HEAD)"
git archive --format=tar HEAD | ssh "$SERVER" "tar -x -C $REMOTE_DIR"

echo "== 2/4 settings, backup job, build, migrate"
# ssh joins its arguments into one remote command line, so quote the values for that shell.
ssh "$SERVER" "$(printf 'SITE=%q COMPOSE=%q REMOTE_DIR=%q bash -s' "$SITE" "$COMPOSE" "$REMOTE_DIR")" <<'REMOTE'
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
$COMPOSE build
$COMPOSE up -d
$COMPOSE exec -T backend python manage.py migrate --noinput
$COMPOSE ps --format '{{.Service}}: {{.Status}}'
REMOTE

echo "== 3/4 Android app"
if [ -n "${APK:-}" ]; then
    ssh "$SERVER" "cd $REMOTE_DIR && $COMPOSE exec -T backend python manage.py publish_android_app -" < "$APK"
else
    echo "(skipped; set APK=path/to/app-release.apk to publish one)"
fi

echo "== 4/4 checking the live site"
sleep 10
curl -fsS "$SITE/api/v1/health/" && echo
for path in / /manifest.webmanifest "/checkout/callback?status=paid"; do
    curl -fsS -o /dev/null -w "%{http_code} $path\n" "$SITE$path"
done
curl -sS -o /dev/null -w "%{http_code} /api/v1/site/android.apk (302 = published, 404 = none yet)\n" "$SITE/api/v1/site/android.apk"
echo "== done"
