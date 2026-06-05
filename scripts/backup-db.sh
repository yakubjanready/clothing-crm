#!/usr/bin/env bash
# CRM Postgres backup — Hetzner serverda cron orqali kuniga 1 marta ishlatiladi.
#
# Cron misoli (`crontab -e` yoki `/etc/cron.d/crm-backup`):
#   0 2 * * * cd /opt/crm && ./scripts/backup-db.sh >> /var/log/crm-backup.log 2>&1
#
# Konfiguratsiya `.env.prod` orqali keladi (BACKUP_DIR, BACKUP_RETENTION_DAYS,
# POSTGRES_USER, POSTGRES_DB).

set -euo pipefail

# Skript turgan repo ildizini topish
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

# .env.prod ni yuklash (bor bo'lsa)
if [[ -f "$REPO_ROOT/.env.prod" ]]; then
    # shellcheck disable=SC1090,SC1091
    set -a; source "$REPO_ROOT/.env.prod"; set +a
fi

: "${POSTGRES_USER:?POSTGRES_USER kerak}"
: "${POSTGRES_DB:?POSTGRES_DB kerak}"

OUT_DIR="${BACKUP_DIR:-$REPO_ROOT/backups}"
RETENTION="${BACKUP_RETENTION_DAYS:-14}"
COMPOSE_FILE="$REPO_ROOT/docker-compose.prod.yml"

mkdir -p "$OUT_DIR"

TS="$(date -u +%Y%m%d-%H%M%S)"
OUT_FILE="$OUT_DIR/crm-${POSTGRES_DB}-${TS}.sql.gz"

echo "[$(date -u +%FT%TZ)] Backup boshlandi: $OUT_FILE"

# postgres konteyneri orqali pg_dump
docker compose -f "$COMPOSE_FILE" exec -T postgres \
    pg_dump -U "$POSTGRES_USER" -d "$POSTGRES_DB" \
            --no-owner --clean --if-exists --format=plain \
    | gzip -9 > "$OUT_FILE"

SIZE_KB=$(( $(stat -c%s "$OUT_FILE" 2>/dev/null || stat -f%z "$OUT_FILE") / 1024 ))
echo "[$(date -u +%FT%TZ)] Backup tugadi (${SIZE_KB} KB)"

# Eski backuplarni tozalash
deleted=$(find "$OUT_DIR" -name "crm-${POSTGRES_DB}-*.sql.gz" -type f -mtime "+${RETENTION}" -print -delete | wc -l)
if [[ "$deleted" -gt 0 ]]; then
    echo "[$(date -u +%FT%TZ)] Eski backup'lar o'chirildi: ${deleted} ta (>${RETENTION} kun)"
fi

# Mavjud backuplarni ko'rsatish (toza chiqish uchun yakuniy holat)
ls -lh "$OUT_DIR" | tail -n +2
