#!/usr/bin/env bash
# Hetzner serverda BIR MARTA ishga tushiriladi — Let's Encrypt sertifikatini ilk bor
# olib, certbot_certs volume'iga saqlaydi. Idempotent: cert mavjud bo'lsa, exit 0.
#
# Standalone rejimi — 80 portni vaqtincha o'zi egallaydi (nginx to'xtatiladi).
# Bu yondashuv sudo / volume mountpath xack'lar talab qilmaydi.
#
# Foydalanish:
#   ssh deploy@138.199.218.108
#   cd /opt/crm
#   ./scripts/init-letsencrypt.sh
#
# Talab: DNS A: negative.uz va www.negative.uz -> server IP'iga yo'naltirilgan;
# server'da 80 va 443 portlari ochiq (Hetzner firewall'da allaqachon ochiq).

set -euo pipefail

DOMAINS=("negative.uz" "www.negative.uz")
EMAIL="${CERTBOT_EMAIL:-admin@negative.uz}"
RSA_KEY_SIZE=4096
STAGING="${CERTBOT_STAGING:-0}"  # 1 -> Let's Encrypt staging (rate limit kengroq)

COMPOSE="docker compose -f docker-compose.prod.yml --env-file .env.prod"
CERTS_VOL="crm_certbot_certs"
WEBROOT_VOL="crm_certbot_webroot"

step() { echo; echo "═══ $* ═══"; }

step "1) Mavjud sertifikat tekshiruvi"
EXISTING=$(docker run --rm -v "$CERTS_VOL:/etc/letsencrypt" --entrypoint sh \
    certbot/certbot:latest -c \
    "if [ -f /etc/letsencrypt/live/${DOMAINS[0]}/fullchain.pem ]; then \
        openssl x509 -in /etc/letsencrypt/live/${DOMAINS[0]}/fullchain.pem -noout -issuer 2>/dev/null || true; \
    fi" 2>/dev/null || true)

if echo "$EXISTING" | grep -q "Let's Encrypt"; then
    echo "  ✓ Real Let's Encrypt cert allaqachon mavjud — sertifikat olish kerak emas."
    echo "  Faqat nginx'ni qayta ko'taramiz."
    $COMPOSE up -d --no-build nginx
    exit 0
fi

step "2) Nginx'ni to'xtatish (80 portni bo'shatish)"
$COMPOSE stop nginx 2>/dev/null || true

step "3) Certbot standalone — sertifikatni olish"
DOMAIN_ARGS=()
for d in "${DOMAINS[@]}"; do DOMAIN_ARGS+=("-d" "$d"); done

STAGING_FLAG=""
[[ "$STAGING" == "1" ]] && STAGING_FLAG="--staging"

# Volumelar mavjud bo'lmasa, docker run avtomatik yaratadi (named volume).
docker run --rm \
    -p 80:80 \
    -v "$CERTS_VOL:/etc/letsencrypt" \
    -v "$WEBROOT_VOL:/var/www/certbot" \
    certbot/certbot:latest \
    certonly --standalone --non-interactive --agree-tos --no-eff-email \
    -m "$EMAIL" \
    --rsa-key-size $RSA_KEY_SIZE \
    $STAGING_FLAG \
    "${DOMAIN_ARGS[@]}"

step "4) Nginx'ni yangi sertifikat bilan ko'tarish"
$COMPOSE up -d --no-build nginx
sleep 3

step "5) Tekshiruv"
docker ps --filter name=crm-nginx --format '{{.Names}}: {{.Status}}'
echo
echo "Tayyor! Endi tekshiring:"
echo "  curl -sSI https://${DOMAINS[0]}/healthz"
echo "  https://${DOMAINS[0]}/  brauzerda"
