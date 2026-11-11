#!/usr/bin/env bash
# Live classes on the site's own server: the official docker-jitsi-meet next to the site, with
# entry by the site's JWT only. From the repository root (/srv/amozeshyar), as root:
#
#   bash deploy/jitsi/install.sh meet.SITE_HOST PUBLIC_IP
#
# Safe to run again (upgrade, settings changed): keeps Jitsi's own passwords and the shared
# secret, rewrites only the settings below. What it does:
#   1. downloads the pinned docker-jitsi-meet release into $JITSI_DIR (default /srv/jitsi);
#   2. configures it for this site: JWT auth, no guests, moderator only from the token,
#      web on 127.0.0.1 only (the host nginx in front, deploy/nginx-jitsi.conf), memory capped
#      so it fits next to the site (deploy/JITSI_SETUP.md, «منابع»);
#   3. writes JITSI_DOMAIN / JITSI_APP_ID / JITSI_APP_SECRET into deploy/.env (secret generated
#      once, never printed);
#   4. starts it and waits until it answers.
# Afterwards: nginx server block + certificate for the subdomain, and a release so the site
# reads the new settings (both printed at the end).
set -euo pipefail

DOMAIN=${1:?usage: $0 meet.SITE_HOST PUBLIC_IP}
PUBLIC_IP=${2:?usage: $0 meet.SITE_HOST PUBLIC_IP}
VERSION=${JITSI_VERSION:-stable-11248-3}
JITSI_DIR=${JITSI_DIR:-/srv/jitsi}
SITE_ENV=${SITE_ENV:-deploy/.env}
WEB_PORT=${JITSI_WEB_PORT:-8200}                 # 127.0.0.1 only; the site uses 8100/3300/9200
JVB_MEMORY=${JITSI_VIDEOBRIDGE_MEMORY:-1024m}    # Jitsi's default is 3 GB each
JICOFO_MEMORY=${JITSI_JICOFO_MEMORY:-512m}
APP_ID=amozeshyar

REPO=$(pwd)
log() { echo "== $*"; }
[ -f "$SITE_ENV" ] || { echo "Run from the site's repository root ($SITE_ENV not found)."; exit 1; }

set_env() {  # set_env FILE KEY VALUE: replace or append, the value never echoed
    local file=$1 key=$2 value=$3
    if grep -q "^#\?${key}=" "$file"; then
        sed -i "s|^#\?${key}=.*|${key}=${value}|" "$file"
    else
        echo "${key}=${value}" >> "$file"
    fi
}

log "docker-jitsi-meet $VERSION in $JITSI_DIR"
mkdir -p "$JITSI_DIR"
if [ ! -f "$JITSI_DIR/.version" ] || [ "$(cat "$JITSI_DIR/.version")" != "$VERSION" ]; then
    tmp=$(mktemp -d)
    curl -fsSL --retry 3 -o "$tmp/djm.tgz" "https://github.com/jitsi/docker-jitsi-meet/archive/refs/tags/$VERSION.tar.gz"
    tar xzf "$tmp/djm.tgz" -C "$tmp"
    # Release files only; the existing .env (passwords) stays.
    cp -r "$tmp/docker-jitsi-meet-$VERSION/." "$JITSI_DIR/"
    rm -rf "$tmp"
    echo "$VERSION" > "$JITSI_DIR/.version"
fi
cd "$JITSI_DIR"
if [ ! -f .env ]; then
    cp env.example .env
    ./gen-passwords.sh >/dev/null
fi

# The secret both sides share: reuse the site's, or make one.
SECRET=$(grep -m1 '^JITSI_APP_SECRET=' "$REPO/$SITE_ENV" | cut -d= -f2- || true)
[ -n "$SECRET" ] || SECRET=$(openssl rand -hex 32)

CONFIG_DIR=${JITSI_CONFIG:-$JITSI_DIR/config}
for kv in \
    "CONFIG=$CONFIG_DIR" "PUBLIC_URL=https://$DOMAIN" "JVB_ADVERTISE_IPS=$PUBLIC_IP" "TZ=Asia/Tehran" \
    "HTTP_PORT=127.0.0.1:$WEB_PORT" "HTTPS_PORT=127.0.0.1:$((WEB_PORT + 43))" "DISABLE_HTTPS=1" \
    "ENABLE_HTTP_REDIRECT=0" "ENABLE_LETSENCRYPT=0" \
    "ENABLE_AUTH=1" "AUTH_TYPE=jwt" "ENABLE_GUESTS=0" "JWT_ALLOW_EMPTY=0" \
    "JWT_APP_ID=$APP_ID" "JWT_ACCEPTED_ISSUERS=$APP_ID" "JWT_ACCEPTED_AUDIENCES=jitsi" \
    "XMPP_MUC_MODULES=token_affiliation" "ENABLE_AUTO_OWNER=0" \
    "VIDEOBRIDGE_MAX_MEMORY=$JVB_MEMORY" "JICOFO_MAX_MEMORY=$JICOFO_MEMORY"; do
    set_env .env "${kv%%=*}" "${kv#*=}"
done
set_env .env JWT_APP_SECRET "$SECRET"
chmod 600 .env
# Every directory the release's compose file mounts. Docker would create missing ones as root,
# but the containers run as uid 1000 and refuse to start on a storage dir they can't write.
mkdir -p "$CONFIG_DIR"/{web,web/custom-ca,prosody/config,prosody/custom-ca,prosody/prosody-plugins-custom}          "$CONFIG_DIR"/{jicofo,jicofo/custom-ca,jvb,jvb/custom-ca}          "$CONFIG_DIR"/storage/{web,prosody,transcripts} "$CONFIG_DIR"/tmp/web-load-test
chown -R 1000:1000 "$CONFIG_DIR"/storage 2>/dev/null || chmod -R 777 "$CONFIG_DIR"/storage

cd "$REPO"
set_env "$SITE_ENV" JITSI_DOMAIN "$DOMAIN"
set_env "$SITE_ENV" JITSI_APP_ID "$APP_ID"
set_env "$SITE_ENV" JITSI_APP_SECRET "$SECRET"
chmod 600 "$SITE_ENV"

log "starting Jitsi"
(cd "$JITSI_DIR" && docker compose -p jitsi up -d --remove-orphans)
for _ in $(seq 1 60); do
    curl -fsS -o /dev/null "http://127.0.0.1:$WEB_PORT/external_api.js" && break
    sleep 3
done
curl -fsS -o /dev/null "http://127.0.0.1:$WEB_PORT/external_api.js" || { echo "Jitsi web did not answer on 127.0.0.1:$WEB_PORT: docker compose -p jitsi logs web"; exit 1; }
(cd "$JITSI_DIR" && docker compose -p jitsi ps --format '{{.Service}}: {{.Status}}')

log "Jitsi is up on 127.0.0.1:$WEB_PORT. Still to do:"
cat <<EOF
  1. DNS: an A record for $DOMAIN -> $PUBLIC_IP; firewall: ufw allow 10000/udp
  2. nginx: sed 's/JITSI_HOST/$DOMAIN/g' deploy/nginx-jitsi.conf > /etc/nginx/sites-available/jitsi
            ln -sf /etc/nginx/sites-available/jitsi /etc/nginx/sites-enabled/jitsi
            certbot --nginx -d $DOMAIN && nginx -t && systemctl reload nginx
     and in the site's nginx file JITSI_HOST -> $DOMAIN (CSP, camera permission), reload.
  3. bash deploy/release.sh   (the site reads JITSI_* from deploy/.env)
  4. A class in a real browser, also on mobile data (deploy/JITSI_SETUP.md, «آزمایش نهایی»).
EOF
