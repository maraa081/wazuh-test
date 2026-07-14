#!/bin/bash
# lab-campaign.sh — Orchestration campagne via Gateway Manager + SSH Target
# Usage : ./lab-campaign.sh <duree_secondes>
# ============================================================
# Ce script est execute SUR LE MANAGER.
# Il pilote la Target via SSH et le pipeline ML localement.

DURATION=${1:-300}
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
TARGET_SCRIPT="/home/vboxuser/wazuh-test/traffic-generator/main.py"

echo "[$(date +%H:%M:%S)] === CAMPAGNE $TIMESTAMP (${DURATION}s) ==="

# Phase 1 : Verifier que la Target est joignable
echo "[1/4] Verification de la Target..."
ssh -o ConnectTimeout=3 target "hostname" > /dev/null 2>&1
if [ $? -ne 0 ]; then
  echo "[FAIL] Target injoignable — verifier SSH et UFW"
  exit 1
fi
echo "[OK] Target connectee ($(ssh target 'hostname'))"

# Phase 2 : Lancer la campagne
echo "[2/4] Lancement de la campagne (${DURATION}s)..."
ssh target "cd /home/vboxuser/wazuh-test/traffic-generator && sudo python3 main.py --duration $DURATION"
if [ $? -ne 0 ]; then
  echo "[FAIL] La campagne a echoue"
  exit 1
fi
echo "[OK] Campagne terminee"

# Phase 3 : Collecter les alertes depuis Wazuh
echo "[3/4] Collecte des alertes..."
mkdir -p /tmp/campaign_$TIMESTAMP
cp /var/ossec/logs/alerts/alerts.json /tmp/campaign_$TIMESTAMP/alerts_snapshot.json
ALERTS=$(wc -l < /tmp/campaign_$TIMESTAMP/alerts_snapshot.json)
echo "[OK] $ALERTS alertes collectees dans /tmp/campaign_$TIMESTAMP/"

# Phase 4 : Verifier le pipeline ML
echo "[4/4] Verification du pipeline ML..."
HEALTH=$(curl -s -o /dev/null -w "%{http_code}" http://127.0.0.1:9090/health 2>/dev/null)
if [ "$HEALTH" = "200" ]; then
  echo "[OK] API ML fonctionnelle (HTTP $HEALTH)"
else
  echo "[WARN] API ML ne repond pas (HTTP $HEALTH)"
fi

# Bilan
MODEL_STATUS=$(curl -s http://127.0.0.1:9090/model/status 2>/dev/null | python3 -c "import sys,json; d=json.load(sys.stdin); print('Charge' if d.get('model_loaded') else 'Non charge')" 2>/dev/null)
echo ""
echo "========================================="
echo "   CAMPAGNE TERMINEE"
echo "   Duree : ${DURATION}s"
echo "   Alertes : $ALERTS"
echo "   Modele : $MODEL_STATUS"
echo "   Dossier : /tmp/campaign_$TIMESTAMP"
echo "========================================="
