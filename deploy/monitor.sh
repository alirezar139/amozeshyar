#!/usr/bin/env bash
# Health and resource checks for one instructor site, every 5 minutes from cron (release.sh installs it):
#   install -m 700 deploy/monitor.sh /usr/local/bin/amozeshyar-monitor
#   echo '*/5 * * * * root /usr/local/bin/amozeshyar-monitor >> /var/log/amozeshyar-monitor.log 2>&1' \
#       > /etc/cron.d/amozeshyar-monitor
#
# Checks: the site's health endpoint; every container running and healthy; disk and memory on the
# host; each container's memory against its limit; Celery queues not piling up; last backup fresh;
# payments nobody could settle. A problem is alerted once when it starts, reminded every
# REMIND_HOURS while it lasts, and "resolved" when it's gone; never once per run.
#
# Alerts go to a chat bot. /etc/amozeshyar-monitor.conf (mode 600):
#   ALERT_BOT_TOKEN=...            # from @botfather in Bale (or Telegram)
#   ALERT_CHAT_ID=...              # the chat the bot writes to
#   ALERT_BOT_API=https://tapi.bale.ai     # Bale (reachable from Iran); https://api.telegram.org for Telegram
# Without a token, alerts are only written to the log.
set -uo pipefail

CONF=${CONF:-/etc/amozeshyar-monitor.conf}
[ -f "$CONF" ] && . "$CONF"

SITE_HEALTH_URL=${SITE_HEALTH_URL:-}            # default: read PUBLIC_URL from deploy/.env
REPO_DIR=${REPO_DIR:-/srv/amozeshyar}
PROJECT=${PROJECT:-amozeshyar}
BACKUP_DIR=${BACKUP_DIR:-/var/backups/amozeshyar}
STATE_DIR=${STATE_DIR:-/var/lib/amozeshyar-monitor}
DISK_MAX_PCT=${DISK_MAX_PCT:-85}
MEM_MIN_AVAILABLE_PCT=${MEM_MIN_AVAILABLE_PCT:-10}
CONTAINER_MEM_MAX_PCT=${CONTAINER_MEM_MAX_PCT:-90}
QUEUE_MAX_DEFAULT=${QUEUE_MAX_DEFAULT:-50}
QUEUE_MAX_VIDEO=${QUEUE_MAX_VIDEO:-10}
BACKUP_MAX_AGE_HOURS=${BACKUP_MAX_AGE_HOURS:-26}
REMIND_HOURS=${REMIND_HOURS:-6}
SERVICES=${SERVICES:-"postgres redis minio backend worker worker-video frontend"}
# Live classes on this server (deploy/jitsi/install.sh): watched too when installed.
JITSI_DIR=${JITSI_DIR:-/srv/jitsi}
ALERT_BOT_API=${ALERT_BOT_API:-https://tapi.bale.ai}

mkdir -p "$STATE_DIR"
host=$(hostname)
problems=()

problem() { problems+=("$1|$2"); }   # id|message

# --- the site answers ---
if [ -z "$SITE_HEALTH_URL" ] && [ -f "$REPO_DIR/deploy/.env" ]; then
    SITE_HEALTH_URL="$(grep -m1 '^PUBLIC_URL=' "$REPO_DIR/deploy/.env" | cut -d= -f2)/api/v1/health/"
fi
if [ -n "$SITE_HEALTH_URL" ]; then
    body=$(curl -fsS --max-time 15 "$SITE_HEALTH_URL" 2>&1) || problem site "سایت جواب نمی‌دهد: $SITE_HEALTH_URL ($(echo "$body" | tail -c 120))"
fi

# --- containers ---
for svc in $SERVICES; do
    state=$(docker inspect --format '{{.State.Status}} {{if .State.Health}}{{.State.Health.Status}}{{end}} {{.RestartCount}}' "$PROJECT-$svc-1" 2>/dev/null) \
        || { problem "container-$svc" "کانتینر $svc وجود ندارد"; continue; }
    read -r status health restarts <<<"$state"
    [ "$status" = running ] || problem "container-$svc" "کانتینر $svc در وضعیت $status است"
    [ "${health:-}" = unhealthy ] && problem "health-$svc" "کانتینر $svc ناسالم (unhealthy) است"
    prev_restarts=$(cat "$STATE_DIR/restarts-$svc" 2>/dev/null || echo "$restarts")
    [ "${restarts:-0}" -gt "${prev_restarts:-0}" ] && problem "restart-$svc" "کانتینر $svc دوباره راه‌اندازی شد (احتمالاً کمبود حافظه)؛ $restarts بار تا الان"
    echo "${restarts:-0}" > "$STATE_DIR/restarts-$svc"
done

# --- live-class containers (only when Jitsi is installed here) ---
if [ -f "$JITSI_DIR/.version" ]; then
    for svc in web prosody jicofo jvb; do
        status=$(docker inspect --format '{{.State.Status}}' "jitsi-$svc-1" 2>/dev/null || echo missing)
        [ "$status" = running ] || problem "jitsi-$svc" "کلاس زنده: کانتینر jitsi-$svc در وضعیت $status است (کلاس‌ها برگزار نمی‌شوند)"
    done
fi

# --- host disk and memory ---
disk=$(df -P / | awk 'NR==2 {gsub("%",""); print $5}')
[ "$disk" -ge "$DISK_MAX_PCT" ] && problem disk "دیسک ${disk}٪ پر است"
for path in "$BACKUP_DIR" /var/lib/docker; do
    [ -d "$path" ] || continue
    pct=$(df -P "$path" | awk 'NR==2 {gsub("%",""); print $5}')
    [ "$pct" -ge "$DISK_MAX_PCT" ] && problem "disk-$path" "پارتیشن $path ${pct}٪ پر است"
done
avail_pct=$(awk '/MemTotal/ {t=$2} /MemAvailable/ {a=$2} END {printf "%d", a*100/t}' /proc/meminfo)
[ "$avail_pct" -lt "$MEM_MIN_AVAILABLE_PCT" ] && problem memory "حافظه‌ی آزاد سرور فقط ${avail_pct}٪ است"

# --- containers near their memory limit (an OOM kill restarts them) ---
while read -r name pct; do
    [ -n "$name" ] || continue
    pct=${pct%%.*}; pct=${pct%\%}
    [ "${pct:-0}" -ge "$CONTAINER_MEM_MAX_PCT" ] && problem "mem-$name" "$name ${pct}٪ از سقف حافظه‌اش را مصرف می‌کند"
done < <(docker stats --no-stream --format '{{.Name}} {{.MemPerc}}' 2>/dev/null | grep "^$PROJECT-")

# --- Celery queues piling up (a worker stopped, or stuck) ---
for q in default celery video; do
    len=$(docker exec "$PROJECT-redis-1" redis-cli LLEN "$q" 2>/dev/null || echo 0)
    max=$([ "$q" = video ] && echo "$QUEUE_MAX_VIDEO" || echo "$QUEUE_MAX_DEFAULT")
    [ "${len:-0}" -gt "$max" ] && problem "queue-$q" "صف $q با $len کار در انتظار پر شده (worker کار نمی‌کند؟)"
done

# --- backups ---
if [ -f "$BACKUP_DIR/last-backup.env" ]; then
    . "$BACKUP_DIR/last-backup.env"
    age_h=$(( ( $(date +%s) - ${LAST_FULL_BACKUP_AT:-0} ) / 3600 ))
    [ "$age_h" -gt "$BACKUP_MAX_AGE_HOURS" ] && problem backup "آخرین بکاپ کامل $age_h ساعت پیش بوده؛ لاگ: /var/log/amozeshyar-backup.log"
else
    problem backup "هیچ بکاپی ثبت نشده ($BACKUP_DIR/last-backup.env نیست)"
fi

# --- payments nobody could settle (money may be taken without access) ---
stuck=$(docker exec "$PROJECT-postgres-1" psql -U amozeshyar -d amozeshyar -At -c \
    "SELECT count(*) FROM payments_payment WHERE status = 'initiated' AND created_at < now() - interval '3 hours'" 2>/dev/null || echo 0)
[ "${stuck:-0}" -gt 0 ] && problem payments "$stuck پرداخت بیش از ۳ ساعت روشن نشده؛ manage.py audit_payments را ببینید"

# --- send what changed ---
send() {
    echo "$(date '+%F %T') ALERT $1"
    [ -n "${ALERT_BOT_TOKEN:-}" ] && [ -n "${ALERT_CHAT_ID:-}" ] || return 0
    curl -fsS --max-time 15 "$ALERT_BOT_API/bot$ALERT_BOT_TOKEN/sendMessage" \
        --data-urlencode "chat_id=$ALERT_CHAT_ID" --data-urlencode "text=[$host] $1" >/dev/null \
        || echo "$(date '+%F %T') could not reach the alert bot"
}

now=$(date +%s)
active=()
for p in "${problems[@]}"; do
    id=${p%%|*}; msg=${p#*|}
    active+=("$id")
    file="$STATE_DIR/alert-$(echo "$id" | tr '/ ' '__')"
    last=$(cat "$file" 2>/dev/null || echo 0)
    if [ "$last" = 0 ] || [ $(( now - last )) -ge $(( REMIND_HOURS * 3600 )) ]; then
        send "⚠️ $msg"
        echo "$now" > "$file"
    fi
done
for file in "$STATE_DIR"/alert-*; do
    [ -e "$file" ] || continue
    id=${file#"$STATE_DIR/alert-"}
    still=0
    for a in "${active[@]}"; do [ "$(echo "$a" | tr '/ ' '__')" = "$id" ] && still=1; done
    if [ "$still" = 0 ]; then
        send "✅ برطرف شد: $id"
        rm -f "$file"
    fi
done
[ ${#problems[@]} -eq 0 ] && echo "$(date '+%F %T') ok"
exit 0
