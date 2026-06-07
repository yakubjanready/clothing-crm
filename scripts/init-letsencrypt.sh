#!/usr/bin/env bash
# Hetzner serverda BIR MARTA ishga tushiriladi — Let's Encrypt sertifikatini ilk bor
# olib, nginx'ga ulaydi. Idempotent: cert mavjud bo'lsa, hech narsa qilmaydi.
#
# Foydalanish:
#   ssh deploy@138.199.218.108
#   cd /opt/crm
#   sudo ./scripts/init-letsencrypt.sh
#
# Talab: DNS A: negative.uz va www.negative.uz -> server IP'iga yo'naltirilgan;
# server'da 80 va 443 portlari ochiq (Hetzner firewall'da allaqachon ochiq).

set -euo pipefail

DOMAINS=("negative.uz" "www.negative.uz")
EMAIL="${CERTBOT_EMAIL:-admin@negative.uz}"
RSA_KEY_SIZE=4096
STAGING="${CERTBOT_STAGING:-0}"  # 1 -> Let's Encrypt staging (test rejimi, rate limit kengroq)

DATA_PATH_HOST="$(docker volume inspect crm_certbot_certs --format '{{.Mountpoint}}' 2>/dev/null || true)"
WEBROOT_HOST="$(docker volume inspect crm_certbot_webroot --format '{{.Mountpoint}}' 2>/dev/null || true)"
COMPOSE="docker compose -f docker-compose.prod.yml --env-file .env.prod"

step() { echo; echo "═══ $* ═══"; }

step "1) Volume tekshiruvi"
if [[ -z "$DATA_PATH_HOST" || -z "$WEBROOT_HOST" ]]; then
    echo "  Volumelar hali yo'q — birinchi marta compose ko'tarib turamiz (nginx fail qilishi mumkin, normal)"
    $COMPOSE up -d --no-build postgres redis backend frontend || true
    $COMPOSE up --no-start nginx certbot
    DATA_PATH_HOST="$(docker volume inspect crm_certbot_certs --format '{{.Mountpoint}}')"
    WEBROOT_HOST="$(docker volume inspect crm_certbot_webroot --format '{{.Mountpoint}}')"
fi

step "2) options-ssl-nginx.conf + ssl-dhparams.pem (recommended)"
if [[ ! -f "$DATA_PATH_HOST/options-ssl-nginx.conf" ]] || [[ ! -f "$DATA_PATH_HOST/ssl-dhparams.pem" ]]; then
    sudo curl -s https://raw.githubusercontent.com/certbot/certbot/master/certbot-nginx/certbot_nginx/_internal/tls_configs/options-ssl-nginx.conf \
        -o "$DATA_PATH_HOST/options-ssl-nginx.conf"
    sudo openssl dhparam -out "$DATA_PATH_HOST/ssl-dhparams.pem" 2048
else
    echo "  ✓ Allaqachon mavjud"
fi

step "3) Dummy sertifikat (nginx'ni ko'tarish uchun)"
CERT_DIR="$DATA_PATH_HOST/live/${DOMAINS[0]}"
if [[ ! -f "$CERT_DIR/fullchain.pem" ]]; then
    sudo mkdir -p "$CERT_DIR"
    sudo openssl req -x509 -nodes -newkey rsa:$RSA_KEY_SIZE -days 1 \
        -keyout "$CERT_DIR/privkey.pem" \
        -out    "$CERT_DIR/fullchain.pem" \
        -subj   "/CN=${DOMAINS[0]}"
    echo "  ✓ Dummy sertifikat yaratildi"
else
    echo "  ✓ Sertifikat allaqachon mavjud (real bo'lishi mumkin)"
fi

step "4) nginx'ni ko'tarish (dummy cert bilan ham bo'lsin)"
$COMPOSE up -d --no-build nginx
sleep 3

step "5) Dummy cert'ni o'chirish (faqat birinchi marta)"
REAL_CERT_CHECK=$(sudo openssl x509 -in "$CERT_DIR/fullchain.pem" -noout -issuer 2>/dev/null | grep -c "Let's Encrypt" || true)
if [[ "$REAL_CERT_CHECK" == "0" ]]; then
    echo "  Dummy aniqlandi — o'chiramiz"
    sudo rm -rf "$DATA_PATH_HOST/live/${DOMAINS[0]}" \
               "$DATA_PATH_HOST/archive/${DOMAINS[0]}" \
               "$DATA_PATH_HOST/renewal/${DOMAINS[0]}.conf"
else
    echo "  ✓ Real Let's Encrypt cert mavjud — o'tkazib yuboramiz"
    exit 0
fi

step "6) Real sertifikat — certbot certonly --webroot"
DOMAIN_ARGS=()
for d in "${DOMAINS[@]}"; do DOMAIN_ARGS+=("-d" "$d"); done

STAGING_FLAG=()
[[ "$STAGING" == "1" ]] && STAGING_FLAG+=("--staging")

$COMPOSE run --rm --entrypoint "certbot certonly --webroot -w /var/www/certbot \
    --email $EMAIL \
    --rsa-key-size $RSA_KEY_SIZE \
    --agree-tos --no-eff-email \
    --force-renewal \
    ${STAGING_FLAG[*]} \
    ${DOMAIN_ARGS[*]}" certbot

step "7) nginx'ni qayta ulash (yangi sertifikat bilan)"
$COMPOSE exec nginx nginx -s reload
echo
echo "Tayyor! https://negative.uz ochiladi."
