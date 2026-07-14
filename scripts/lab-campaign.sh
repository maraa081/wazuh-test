#!/bin/bash
# lab-campaign.sh — Orchestration complete d'une campagne d'attaque
# Usage : ./lab-campaign.sh <duree_secondes>
# ============================================================
# Ce script pilote les deux noeuds OpenClaw (Manager + Target)
# pour executer une sequence : Campagne -> Collecte -> Inference

DURATION=${1:-300}
NODE_MANAGER="manager-wazuh"
NODE_TARGET="target-suricata"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)

echo "[$(date +%H:%M:%S)] === CAMPAGNE $TIMESTAMP (${DURATION}s) ==="

# Phase 1 : Verifier les noeuds
echo "[1/5] Verification des noeuds..."
openclaw nodes invoke --node "$NODE_MANAGER" --command "system.run" \
  --params '{"command":"echo MANAGER_OK"}' > /dev/null 2>&1
if [ $? -ne 0 ]; then echo "[FAIL] Manager injoignable"; exit 1; fi
echo "[OK] Manager connecte"

openclaw nodes invoke --node "$NODE_TARGET" --command "system.run" \
  --params '{"command":"echo TARGET_OK"}' > /dev/null 2>&1
if [ $? -ne 0 ]; then echo "[FAIL] Target injoignable"; exit 1; fi
echo "[OK] Target connectee"

# Phase 2 : Preparer la collecte
echo "[2/5] Preparation de la collecte..."
openclaw nodes invoke --node "$NODE_MANAGER" --command "system.run" \
  --params "{\"command\":\"mkdir -p /tmp/campaign_$TIMESTAMP && echo DONE\"}"
echo "[OK] Dossier de collecte pret"

# Phase 3 : Lancer la campagne
echo "[3/5] Lancement de la campagne (${DURATION}s)..."
openclaw nodes invoke --node "$NODE_TARGET" --command "system.run" \
  --params "{\"command\":\"cd /home/vboxuser/wazuh-test/traffic-generator && sudo python3 main.py --duration $DURATION\"}"
echo "[OK] Campagne terminee"

# Phase 4 : Collecter les alertes
echo "[4/5] Collecte des alertes depuis le Manager..."
ALERTS_RAW=$(openclaw nodes invoke --node "$NODE_MANAGER" --command "system.run" \
  --params "{\"command\":\"cp /var/ossec/logs/alerts/alerts.json /tmp/campaign_$TIMESTAMP/alerts_snapshot.json && wc -l /tmp/campaign_$TIMESTAMP/alerts_snapshot.json\"}" 2>&1)
echo "[OK] Alertes collectees : $ALERTS_RAW"

# Phase 5 : Verifier l'inference
echo "[5/5] Verification du pipeline ML..."
INFER_STATUS=$(openclaw nodes invoke --node "$NODE_MANAGER" --command "system.run" \
  --params '{"command":"curl -s http://127.0.0.1:9090/health"}' 2>&1)
echo "[OK] Inference ML : $INFER_STATUS"

echo ""
echo "[$(date +%H:%M:%S)] === CAMPAGNE TERMINEE ==="
echo "Prochaine etape : entrainer le modele avec les nouvelles donnees"
echo "  -> exec host=node node=$NODE_MANAGER command=\\\"cd /home/vboxuser/wazuh-test && python3 pipeline/02_label_dataset.py && python3 pipeline/04_train_model.py\\\""
