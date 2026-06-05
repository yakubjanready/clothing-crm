#!/usr/bin/env bash
# Netdata monitoring o'rnatish (lightweight, 1 server uchun).
# Default port 19999 — nginx orqali /netdata location (basic auth).

set -euo pipefail
cd "$(dirname "$0")/../.."

SERVER_IP="${1:-$(cat infra/secrets/server_ip.txt 2>/dev/null || echo '')}"
SSH_KEY="$PWD/infra/secrets/id_ed25519_crm"
SSH_OPTS="-i $SSH_KEY -o StrictHostKeyChecking=accept-new -o UserKnownHostsFile=infra/secrets/known_hosts"

[[ -z "$SERVER_IP" ]] && { echo "ERROR: SERVER_IP berilmagan"; exit 1; }

step() { echo; echo "═══ $* ═══"; }

step "1) Netdata kickstart (rasmiy skript)"
ssh $SSH_OPTS deploy@"$SERVER_IP" "
    if ! command -v netdata >/dev/null 2>&1; then
        wget -O /tmp/kickstart.sh https://my-netdata.io/kickstart.sh
        sudo bash /tmp/kickstart.sh --dont-wait --disable-telemetry --stable-channel --no-updates
    else
        echo Netdata mavjud
    fi
"

step "2) Netdata'ni faqat localhost'da tinglashga sozlash"
ssh $SSH_OPTS deploy@"$SERVER_IP" "
    sudo sed -i 's|^[[:space:]]*# bind socket to IP =.*|        bind socket to IP = 127.0.0.1|' /etc/netdata/netdata.conf || true
    sudo systemctl restart netdata
    curl -sS http://127.0.0.1:19999/api/v1/info | head -c 200 && echo
"

echo
echo "═══ Monitoring tayyor ✓ ═══"
echo "  Netdata: tashqaridan ko'rish uchun nginx /netdata location qo'shish kerak."
echo "  Hozircha SSH tunnel orqali ko'rish mumkin:"
echo "    ssh -L 19999:127.0.0.1:19999 deploy@$SERVER_IP"
echo "    → keyin http://localhost:19999"
