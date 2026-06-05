#!/usr/bin/env bash
# Serverga SSH orqali ulanib CRM'ni o'rnatish.
# Talab: 01_create_all.sh ishlatilgan va cloud-init tugagan (~4-5 daqiqa).
#
# Ishlatish:
#   ./infra/hetzner/02_provision.sh [SERVER_IP]
# Agar IP berilmasa infra/secrets/server_ip.txt'dan o'qiladi.

set -euo pipefail
cd "$(dirname "$0")/../.."

SERVER_IP="${1:-$(cat infra/secrets/server_ip.txt 2>/dev/null || echo '')}"
SSH_KEY="$PWD/infra/secrets/id_ed25519_crm"
SSH_OPTS="-i $SSH_KEY -o StrictHostKeyChecking=accept-new -o UserKnownHostsFile=infra/secrets/known_hosts"
REPO_URL="${REPO_URL:-https://gitlab.com/Elyorbek00/ulgurji-kiyim-kechak-kompaniyasi-crm.git}"

if [[ -z "$SERVER_IP" ]]; then echo "ERROR: SERVER_IP berilmagan"; exit 1; fi
step() { echo; echo "═══ $* ═══"; }

step "1) SSH ulanish (deploy@$SERVER_IP)"
ssh $SSH_OPTS deploy@"$SERVER_IP" "hostname && id && docker --version && docker compose version"

step "2) Repo'ni klon qilish"
ssh $SSH_OPTS deploy@"$SERVER_IP" "cd /opt/crm && \
    if [[ ! -d .git ]]; then git clone $REPO_URL . ; else git pull --rebase ; fi && \
    git log --oneline -1"

step "3) .env.prod ni xavfsiz yaratish (random sirlar)"
if [[ ! -f infra/secrets/.env.prod ]]; then
    SECRET_KEY="$(openssl rand -hex 32)"
    DB_PASS="$(openssl rand -base64 24 | tr -d '/+=')"
    ADMIN_PASS="$(openssl rand -base64 18 | tr -d '/+=')"
    MINIO_PASS="$(openssl rand -base64 18 | tr -d '/+=')"
    cat > infra/secrets/.env.prod <<EOF
APP_NAME=clothing-crm
APP_ENV=production
DEBUG=false
API_V1_PREFIX=/api/v1
BACKEND_CORS_ORIGINS=["http://$SERVER_IP","https://$SERVER_IP"]
POSTGRES_HOST=postgres
POSTGRES_PORT=5432
POSTGRES_USER=crm
POSTGRES_PASSWORD=$DB_PASS
POSTGRES_DB=crm
REDIS_URL=redis://redis:6379/0
CELERY_BROKER_URL=redis://redis:6379/1
CELERY_RESULT_BACKEND=redis://redis:6379/2
SECRET_KEY=$SECRET_KEY
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=15
REFRESH_TOKEN_EXPIRE_DAYS=7
INITIAL_ADMIN_EMAIL=admin@crm.local
INITIAL_ADMIN_PASSWORD=$ADMIN_PASS
MEDIA_ROOT=/app/media
MEDIA_URL_PREFIX=/media
WEB_CONCURRENCY=2
LOG_LEVEL=info
SENTRY_DSN=
VITE_SENTRY_DSN=
MINIO_ROOT_USER=minio
MINIO_ROOT_PASSWORD=$MINIO_PASS
MINIO_API_PORT=9000
MINIO_CONSOLE_PORT=9001
NGINX_HTTP_PORT=80
BACKUP_DIR=/var/backups/crm
RETENTION_DAYS=14
EOF
    chmod 600 infra/secrets/.env.prod
    echo "  ✓ .env.prod yaratildi (sirlar infra/secrets/.env.prod ichida, gitignore'd)"
fi
scp $SSH_OPTS infra/secrets/.env.prod deploy@"$SERVER_IP":/opt/crm/.env.prod
ssh $SSH_OPTS deploy@"$SERVER_IP" "chmod 600 /opt/crm/.env.prod"

step "4) Docker compose up -d --build (birinchi marta ~10-15 daq)"
ssh $SSH_OPTS deploy@"$SERVER_IP" "cd /opt/crm && docker compose -f docker-compose.prod.yml --env-file .env.prod up -d --build"

step "5) Servislarni kutish (healthcheck)"
ssh $SSH_OPTS deploy@"$SERVER_IP" "cd /opt/crm && \
    for i in {1..30}; do \
        if docker compose -f docker-compose.prod.yml ps backend | grep -q healthy; then \
            echo backend healthy; break; \
        fi; \
        echo waiting backend... \$i; sleep 5; \
    done"

step "6) Alembic upgrade head"
ssh $SSH_OPTS deploy@"$SERVER_IP" "cd /opt/crm && docker compose -f docker-compose.prod.yml exec -T backend alembic upgrade head"

step "7) RBAC seed (admin user)"
ssh $SSH_OPTS deploy@"$SERVER_IP" "cd /opt/crm && docker compose -f docker-compose.prod.yml exec -T backend python -m app.scripts.seed_rbac || echo '(seed allaqachon bajarilgan bo\\'lishi mumkin)'"

step "8) Smoke test"
ssh $SSH_OPTS deploy@"$SERVER_IP" "curl -fsS http://localhost/healthz && echo && curl -fsS http://localhost/api/v1/auth/login -X POST -H 'Content-Type: application/json' -d '{\"email\":\"x\",\"password\":\"x\"}' | head -c 200"

echo
echo "═══ Tugadi ✓ ═══"
echo "  Public URL : http://$SERVER_IP"
echo "  API docs   : http://$SERVER_IP/api/docs"
echo "  Admin email: admin@crm.local (parol .env.prod ichida)"
