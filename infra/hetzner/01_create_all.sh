#!/usr/bin/env bash
# CRM Hetzner infra'ni boshidan oxirigacha yaratish (idempotent — mavjud bo'lsa o'tkazib yuboradi).
# Talab: hcloud CLI sozlangan (`hcloud context create crm-prod`) va admin IP qo'lda kiritilgan.

set -euo pipefail
cd "$(dirname "$0")/../.."

ADMIN_IP="${ADMIN_IP:-195.158.9.110}/32"
SERVER_NAME="${SERVER_NAME:-crm-app-01}"
SERVER_TYPE="${SERVER_TYPE:-cpx22}"   # CPX22 x86 ($9.49/oy) — ARM CAX11/21 ko'pincha yo'q
LOCATION="${LOCATION:-nbg1}"
NETWORK_NAME="${NETWORK_NAME:-crm-vpc}"
FIREWALL_NAME="${FIREWALL_NAME:-crm-fw}"
SSH_KEY_NAME="${SSH_KEY_NAME:-crm-deploy}"
SSH_KEY_PATH="${SSH_KEY_PATH:-infra/secrets/id_ed25519_crm}"

step() { echo; echo "═══ $* ═══"; }

step "1) SSH kalit"
if [[ ! -f "$SSH_KEY_PATH" ]]; then
    mkdir -p "$(dirname "$SSH_KEY_PATH")"
    ssh-keygen -t ed25519 -N "" -C "crm-deploy@hetzner" -f "$SSH_KEY_PATH"
else
    echo "  ✓ Mavjud: $SSH_KEY_PATH"
fi

step "2) Hetzner'da SSH kalit"
if ! hcloud ssh-key describe "$SSH_KEY_NAME" >/dev/null 2>&1; then
    hcloud ssh-key create --name "$SSH_KEY_NAME" --public-key "$(cat "${SSH_KEY_PATH}.pub")"
else
    echo "  ✓ Mavjud: $SSH_KEY_NAME"
fi

step "3) Private Network ($NETWORK_NAME, 10.0.0.0/16)"
if ! hcloud network describe "$NETWORK_NAME" >/dev/null 2>&1; then
    hcloud network create --name "$NETWORK_NAME" --ip-range 10.0.0.0/16
    hcloud network add-subnet "$NETWORK_NAME" --type cloud --network-zone eu-central --ip-range 10.0.1.0/24
else
    echo "  ✓ Mavjud: $NETWORK_NAME"
fi

step "4) Firewall ($FIREWALL_NAME)"
if ! hcloud firewall describe "$FIREWALL_NAME" >/dev/null 2>&1; then
    # Admin IP'ni JSON faylga inject qilamiz
    sed "s|195.158.9.110/32|$ADMIN_IP|" infra/hetzner/firewall-rules.json > /tmp/fw.json
    hcloud firewall create --name "$FIREWALL_NAME" --rules-file /tmp/fw.json
    rm /tmp/fw.json
else
    echo "  ✓ Mavjud: $FIREWALL_NAME"
fi

step "5) Server ($SERVER_NAME, $SERVER_TYPE @ $LOCATION)"
if ! hcloud server describe "$SERVER_NAME" >/dev/null 2>&1; then
    hcloud server create \
        --name "$SERVER_NAME" \
        --type "$SERVER_TYPE" \
        --image ubuntu-24.04 \
        --location "$LOCATION" \
        --ssh-key "$SSH_KEY_NAME" \
        --network "$NETWORK_NAME" \
        --firewall "$FIREWALL_NAME" \
        --user-data-from-file infra/cloud-init/app.yaml
else
    echo "  ✓ Mavjud: $SERVER_NAME"
fi

step "6) IP manzili"
SERVER_IP="$(hcloud server ip "$SERVER_NAME")"
echo "  Public IPv4 : $SERVER_IP"
echo "  Keyingi qadam: ./02_provision.sh $SERVER_IP"
echo "$SERVER_IP" > infra/secrets/server_ip.txt
