#!/usr/bin/env bash
# CRM Postgres restore — backup faylidan tiklash.
# Ishlatish:
#   ./scripts/restore-db.sh /var/backups/crm/crm-crm-20260605-020000.sql.gz
#
# OGOH: bu joriy DBni qayta yozadi (--clean --if-exists). Avval `docker compose down`
# orqali backendni to'xtatish tavsiya etiladi (ulanishlar uzilishi uchun).

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

if [[ -f "$REPO_ROOT/.env.prod" ]]; then
    # shellcheck disable=SC1090,SC1091
    set -a; source "$REPO_ROOT/.env.prod"; set +a
fi

: "${POSTGRES_USER:?POSTGRES_USER kerak}"
: "${POSTGRES_DB:?POSTGRES_DB kerak}"

if [[ $# -lt 1 ]]; then
    echo "Foydalanish: $0 <backup-file.sql.gz>" >&2
    exit 1
fi

BACKUP_FILE="$1"
if [[ ! -f "$BACKUP_FILE" ]]; then
    echo "Backup fayli topilmadi: $BACKUP_FILE" >&2
    exit 1
fi

COMPOSE_FILE="$REPO_ROOT/docker-compose.prod.yml"

echo "[$(date -u +%FT%TZ)] Restore boshlandi: $BACKUP_FILE → DB '$POSTGRES_DB'"
echo "Davom etish uchun 'YES' deb yozing:"
read -r confirm
[[ "$confirm" == "YES" ]] || { echo "Bekor qilindi"; exit 1; }

gunzip -c "$BACKUP_FILE" | docker compose -f "$COMPOSE_FILE" exec -T postgres \
    psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -v ON_ERROR_STOP=1

echo "[$(date -u +%FT%TZ)] Restore tugadi."
