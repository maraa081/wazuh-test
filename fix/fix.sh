#!/bin/bash
# fix.sh — Correction du service inference + UFW
# À exécuter avec sudo sur le Manager

set -e

echo "=== Fix 1: Service inference avec les bons chemins ==="
sudo tee /etc/systemd/system/wazuh-inference.service << 'SERVICEEOF'
[Unit]
Description=Wazuh ML Inference Service
After=network.target
Wants=wazuh-manager.service

[Service]
Type=simple
User=root
WorkingDirectory=/opt/wazuh-ml
ExecStart=/usr/bin/python3 /opt/wazuh-ml/inference_service.py --model /opt/wazuh-ml/xgb_model.json --db /tmp/predictions.db
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
SERVICEEOF

echo "=== Fix 2: Service API (deja OK mais reload) ==="
sudo tee /etc/systemd/system/wazuh-api.service << 'SERVICEEOF'
[Unit]
Description=Wazuh ML API Service
After=network.target wazuh-inference.service
Wants=wazuh-inference.service

[Service]
Type=simple
User=root
WorkingDirectory=/opt/wazuh-ml
ExecStart=/usr/bin/python3 /opt/wazuh-ml/api_service.py --db /tmp/predictions.db --port 9090 --host 127.0.0.1
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
SERVICEEOF

echo "=== Fix 3: Reload + restart ==="
sudo systemctl daemon-reload
sudo systemctl restart wazuh-inference
sleep 3
sudo systemctl restart wazuh-api

echo "=== Fix 4: Verif ==="
echo "Inference: $(sudo systemctl is-active wazuh-inference)"
echo "API: $(sudo systemctl is-active wazuh-api)"
curl -s http://127.0.0.1:9090/health
echo ""
curl -s http://127.0.0.1:9090/model/status
echo ""

echo "=== Fix 5: UFW ==="
sudo ufw --force reset
sudo ufw default deny incoming
sudo ufw default allow outgoing

# SSH depuis Windows
sudo ufw allow from 192.168.30.1 to any port 22 proto tcp comment 'SSH depuis Windows'
# SSH depuis Target (debug)
sudo ufw allow from 192.168.30.10 to any port 22 proto tcp comment 'SSH depuis Target'
# OpenClaw UI depuis Windows
sudo ufw allow from 192.168.30.1 to any port 18789 proto tcp comment 'OpenClaw UI depuis Windows'
# ML API locale + Target
sudo ufw allow from 127.0.0.1 to any port 9090 proto tcp comment 'API ML locale'
sudo ufw allow from 192.168.30.10 to any port 9090 proto tcp comment 'API ML depuis Target'
# Wazuh API
sudo ufw allow from 127.0.0.1 to any port 55000 proto tcp comment 'Wazuh API locale'
sudo ufw allow from 192.168.30.10 to any port 55000 proto tcp comment 'Wazuh API Target'
# Wazuh Agent
sudo ufw allow from 192.168.30.10 to any port 1514 proto udp comment 'Wazuh Agent UDP'
sudo ufw allow from 192.168.30.10 to any port 1515 proto tcp comment 'Wazuh Agent TCP'
# OpenSearch local
sudo ufw allow from 127.0.0.1 to any port 9200 proto tcp comment 'OpenSearch local'
# Dashboard local
sudo ufw allow from 127.0.0.1 to any port 443 proto tcp comment 'Dashboard local'

sudo ufw --force enable
sudo ufw status numbered

echo ""
echo "=== DONE ==="
echo "Inference: $(sudo systemctl is-active wazuh-inference)"
echo "API: $(sudo systemctl is-active wazuh-api)"
echo "UFW: actif"
