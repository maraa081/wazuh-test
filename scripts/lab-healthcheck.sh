#!/bin/bash
# lab-healthcheck.sh — Verification rapide de l'etat du labo
# ============================================================
# Verifie que les deux noeuds OpenClaw sont accessibles
# et que les services critiques tournent.

NODE_MANAGER="manager-wazuh"
NODE_TARGET="target-suricata"
PASS=0
FAIL=0

green() { echo -e "\e[32m$1\e[0m"; }
red()   { echo -e "\e[31m$1\e[0m"; }

check() {
  local desc=$1
  local result=$2
  if [ "$result" = "OK" ]; then
    green "  [OK] $desc"
    PASS=$((PASS+1))
  else
    red "  [FAIL] $desc — $result"
    FAIL=$((FAIL+1))
  fi
}

echo "========================================="
echo "   LAB HEALTHCHECK — $(date +%Y-%m-%d\ %H:%M)"
echo "========================================="
echo ""

# --- Noeuds OpenClaw ---
echo "[Noeuds OpenClaw]"

NODES_LIST=$(openclaw nodes list --connected 2>&1)
echo "$NODES_LIST" | grep -q "manager-wazuh"
check "Manager connecte" "$([ $? -eq 0 ] && echo OK || echo INTROUVABLE)"

echo "$NODES_LIST" | grep -q "target-suricata"
check "Target connectee" "$([ $? -eq 0 ] && echo OK || echo INTROUVABLE)"

# --- Manager : services systemd ---
echo "[Manager — Services]"

SVC_INF=$(openclaw nodes invoke --node "$NODE_MANAGER" --command "system.run" \
  --params '{"command":"systemctl is-active wazuh-inference"}' 2>&1)
echo "$SVC_INF" | grep -q "active"
check "ML Inference" "$([ $? -eq 0 ] && echo OK || echo "$SVC_INF")"

SVC_API=$(openclaw nodes invoke --node "$NODE_MANAGER" --command "system.run" \
  --params '{"command":"systemctl is-active wazuh-api"}' 2>&1)
echo "$SVC_API" | grep -q "active"
check "ML API" "$([ $? -eq 0 ] && echo OK || echo "$SVC_API")"

SVC_WAZUH=$(openclaw nodes invoke --node "$NODE_MANAGER" --command "system.run" \
  --params '{"command":"systemctl is-active wazuh-manager"}' 2>&1)
echo "$SVC_WAZUH" | grep -q "active"
check "Wazuh Manager" "$([ $? -eq 0 ] && echo OK || echo "$SVC_WAZUH")"

# --- Manager : API ML ---
echo "[Manager — API ML]"

API_HEALTH=$(openclaw nodes invoke --node "$NODE_MANAGER" --command "system.run" \
  --params '{"command":"curl -s -o /dev/null -w \\"%{http_code}\\" http://127.0.0.1:9090/health"}' 2>&1)
echo "$API_HEALTH" | grep -q "200"
check "Endpoint /health" "$([ $? -eq 0 ] && echo OK || echo "HTTP $API_HEALTH")"

API_MODEL=$(openclaw nodes invoke --node "$NODE_MANAGER" --command "system.run" \
  --params '{"command":"curl -s http://127.0.0.1:9090/model/status | python3 -c \\\"import sys,json; d=json.load(sys.stdin); print(d.get('model_loaded','unknown'))\\\""}' 2>&1)
echo "$API_MODEL" | grep -q "true"
check "Modele charge" "$([ $? -eq 0 ] && echo OK || echo "$API_MODEL")"

# --- Target : services ---
echo "[Target — Services]"

SVC_SURICATA=$(openclaw nodes invoke --node "$NODE_TARGET" --command "system.run" \
  --params '{"command":"systemctl is-active suricata"}' 2>&1)
echo "$SVC_SURICATA" | grep -q "active"
check "Suricata" "$([ $? -eq 0 ] && echo OK || echo "$SVC_SURICATA")"

SVC_AGENT=$(openclaw nodes invoke --node "$NODE_TARGET" --command "system.run" \
  --params '{"command":"systemctl is-active wazuh-agent"}' 2>&1)
echo "$SVC_AGENT" | grep -q "active"
check "Wazuh Agent" "$([ $? -eq 0 ] && echo OK || echo "$SVC_AGENT")"

DOCKER_OK=$(openclaw nodes invoke --node "$NODE_TARGET" --command "system.run" \
  --params '{"command":"sudo docker info --format \\"{{.ServerVersion}}\\" 2>/dev/null || echo NO_DOCKER"}' 2>&1)
echo "$DOCKER_OK" | grep -qv "NO_DOCKER"
check "Docker" "$([ $? -eq 0 ] && echo OK || echo "$DOCKER_OK")"

# --- Securite ---
echo "[Securite — UFW]"

UFW_MGR=$(openclaw nodes invoke --node "$NODE_MANAGER" --command "system.run" \
  --params '{"command":"sudo ufw status | head -3"}' 2>&1)
echo "$UFW_MGR" | grep -q "active"
check "UFW actif sur Manager" "$([ $? -eq 0 ] && echo OK || echo "$UFW_MGR")"

UFW_TGT=$(openclaw nodes invoke --node "$NODE_TARGET" --command "system.run" \
  --params '{"command":"sudo ufw status | head -3"}' 2>&1)
echo "$UFW_TGT" | grep -q "active"
check "UFW actif sur Target" "$([ $? -eq 0 ] && echo OK || echo "$UFW_TGT")"

# --- Tests de communication ---
echo "[Communication inter-VMs]"

PING_MT=$(openclaw nodes invoke --node "$NODE_MANAGER" --command "system.run" \
  --params '{"command":"ping -c 1 -W 2 192.168.30.10 >/dev/null 2>&1 && echo OK || echo FAIL"}' 2>&1)
echo "$PING_MT" | grep -q "OK"
check "Manager -> Target" "$([ $? -eq 0 ] && echo OK || echo "$PING_MT")"

PING_TM=$(openclaw nodes invoke --node "$NODE_TARGET" --command "system.run" \
  --params '{"command":"ping -c 1 -W 2 192.168.30.3 >/dev/null 2>&1 && echo OK || echo FAIL"}' 2>&1)
echo "$PING_TM" | grep -q "OK"
check "Target -> Manager" "$([ $? -eq 0 ] && echo OK || echo "$PING_TM")"

# --- Bilan ---
echo ""
echo "========================================="
echo "   BILAN : $PASS OK / $FAIL FAIL"
echo "========================================="

exit $FAIL
