#!/bin/bash
# deploy-sidecar.sh — Déploiement du Wazuh ML Sidecar sur le Manager
# Usage: sudo bash deploy-sidecar.sh
set -euo pipefail

INSTALL_DIR="/opt/wazuh-ml-sidecar"
REPO="https://raw.githubusercontent.com/maraa081/wazuh-test/main"

echo "================================================================"
echo " WAZUH ML SIDECAR DEPLOYMENT"
echo "================================================================"
echo "  Target: $INSTALL_DIR"
echo "  Repo:   $REPO"
echo ""

if [ "$(id -u)" -ne 0 ]; then echo "ERROR: run as root"; exit 1; fi

# --- 1. Create directories ---
echo "--- 1/5: Directories ---"
mkdir -p "$INSTALL_DIR/scripts"
mkdir -p "$INSTALL_DIR/data"
mkdir -p "$INSTALL_DIR/models"

# --- 2. Download files ---
echo "--- 2/5: Downloading files ---"
for file in \
    scripts/wazuh-ml-sidecar/inference_service.py \
    scripts/wazuh-ml-sidecar/api_service.py \
    scripts/wazuh-ml-sidecar/requirements.txt \
    scripts/wazuh-ml-sidecar/wazuh-inference.service \
    scripts/wazuh-ml-sidecar/wazuh-api.service; do
    curl -sL -o "$INSTALL_DIR/${file##*/}" "$REPO/$file?$(date +%s)"
    echo "  ${file##*/}"
done

# --- 3. Copy trained model ---
echo "--- 3/5: Model ---"
MODEL_SRC=$(find /home -name "xgb_model.json" 2>/dev/null | head -1)
if [ -f "$MODEL_SRC" ]; then
    cp "$MODEL_SRC" "$INSTALL_DIR/models/xgb_model.json"
    echo "  Model copied from: $MODEL_SRC"
else
    # Try to find it in the project
    if [ -f "/home/vboxuser/wazuh-test/models/xgb_model.json" ]; then
        cp "/home/vboxuser/wazuh-test/models/xgb_model.json" "$INSTALL_DIR/models/"
        echo "  Model copied from wazuh-test project"
    fi
fi
ls -la "$INSTALL_DIR/models/xgb_model.json" 2>/dev/null || echo "  WARN: No model found"

# --- 4. Install Python deps ---
echo "--- 4/5: Python dependencies ---"
pip3 install -r "$INSTALL_DIR/requirements.txt" 2>&1 | tail -3

# --- 5. Install systemd services ---
echo "--- 5/5: Systemd services ---"
cp "$INSTALL_DIR/wazuh-inference.service" /etc/systemd/system/
cp "$INSTALL_DIR/wazuh-api.service" /etc/systemd/system/
systemctl daemon-reload

echo ""
echo "================================================================"
echo " DEPLOYMENT COMPLETE"
echo "================================================================"
echo ""
echo "  Start services:"
echo "    sudo systemctl enable --now wazuh-inference"
echo "    sudo systemctl enable --now wazuh-api"
echo ""
echo "  Check status:"
echo "    sudo journalctl -u wazuh-inference -f"
echo "    sudo journalctl -u wazuh-api -f"
echo ""
echo "  Test API:"
echo "    curl http://localhost:9090/health"
echo "    curl http://localhost:9090/stats"
echo "================================================================"
