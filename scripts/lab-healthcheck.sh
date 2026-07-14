#!/bin/bash
# lab-healthcheck.sh — Verification rapide du labo
# Execute SUR LE MANAGER, verifie la Target via SSH
# ============================================================

GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m'
PASS=0
FAIL=0
WARN=0

check() {
  local desc=$1
  if [ $2 -eq 0 ]; then
    echo -e "  ${GREEN}[OK]${NC} $desc"
    PASS=$((PASS+1))
  else
    echo -e "  ${RED}[FAIL]${NC} $desc — $3"
    FAIL=$((FAIL+1))
  fi
}

warn() {
  echo -e "  ${YELLOW}[WARN]${NC} $1 — $2"
  WARN=$((WARN+1))
}

echo "========================================="
echo "   LAB HEALTHCHECK — $(date '+%Y-%m-%d %H:%M')"
echo "   Host : $(hostname) ($(hostname -I | awk '{print $1}'))"
echo "========================================="
echo ""

# ================ Gateway OpenClaw ================
echo "[Gateway OpenClaw]"

GW_SVC=$(systemctl --user is-active openclaw-gateway 2>/dev/null)
[ "$GW_SVC" = "active" ]
check "Service Gateway" $? "$GW_SVC"

GW_PORT=$(ss -tlnp | grep 18789 | head -1)
[ -n "$GW_PORT" ]
check "Port 18789" $? "Pas d'ecoute"

# ================ Target (SSH) ================
echo "[Target — via SSH]"

HOSTNAME_TGT=$(ssh -o ConnectTimeout=3 target "hostname" 2>/dev/null)
check "SSH joignable" $? "ssh: connexion echouee"

[ -n "$HOSTNAME_TGT" ]
check "Hostname = $HOSTNAME_TGT" $?

SURICATA=$(ssh target "sudo systemctl is-active suricata" 2>/dev/null)
[ "$SURICATA" = "active" ]
check "Suricata" $? "$SURICATA"

DOCKER=$(ssh target "sudo docker info --format '{{.ServerVersion}}'" 2>/dev/null)
[ -n "$DOCKER" ]
check "Docker v$DOCKER" $? "Docker inaccessible"

WAZUH_AGENT=$(ssh target "sudo systemctl is-active wazuh-agent" 2>/dev/null)
[ "$WAZUH_AGENT" = "active" ]
check "Wazuh Agent" $? "$WAZUH_AGENT"

# ================ ML Pipeline ================
echo "[ML Pipeline]"

INF_SVC=$(systemctl is-active wazuh-inference 2>/dev/null)
[ "$INF_SVC" = "active" ]
check "Inference Service" $? "$INF_SVC"

API_SVC=$(systemctl is-active wazuh-api 2>/dev/null)
[ "$API_SVC" = "active" ]
check "API Service" $? "$API_SVC"

API_HEALTH=$(curl -s -o /dev/null -w "%{http_code}" http://127.0.0.1:9090/health 2>/dev/null)
[ "$API_HEALTH" = "200" ]
check "API ML repond (HTTP $API_HEALTH)" $? "Status: $API_HEALTH"

# Check model via inference service logs (API n'a pas d'endpoint /model/status)
MODEL_LOADED=$(sudo journalctl -u wazuh-inference --since "5 min ago" --no-pager 2>/dev/null | grep -q "Model loaded" && echo "true" || echo "unknown")
[ "$MODEL_LOADED" = "true" ]
check "Modele charge" $? "$MODEL_LOADED"

# ================ Securite ================
echo "[Securite]"

UFW_ACTIVE=$(sudo ufw status 2>/dev/null | head -1)
echo "$UFW_ACTIVE" | grep -qi "active"
check "UFW actif" $? "$UFW_ACTIVE"

UFW_18789=$(sudo ufw status 2>/dev/null | grep "18789" | grep "192.168.30.1")
[ -n "$UFW_18789" ]
check "UI reservee a 192.168.30.1" $? "Regle manquante"

# ================ Wazuh ================
echo "[Wazuh]"

WAZUH_MGR=$(systemctl is-active wazuh-manager 2>/dev/null)
[ "$WAZUH_MGR" = "active" ]
check "Wazuh Manager" $? "$WAZUH_MGR"

# ================ Bilan ================
echo ""
echo "========================================="
echo "   BILAN : $PASS OK / $FAIL FAIL / $WARN WARN"
echo "========================================="

exit $FAIL
