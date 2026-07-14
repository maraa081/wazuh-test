#!/bin/bash
# fix2.sh — Correction finale inference service + regles UFW manquantes

set -e

echo "=== Fix 1: Service inference avec metrics ==="
sudo tee /etc/systemd/system/wazuh-inference.service << 'SERVICEEOF'
[Unit]
Description=Wazuh ML Inference Service
After=network.target
Wants=wazuh-manager.service

[Service]
Type=simple
User=root
WorkingDirectory=/opt/wazuh-ml
ExecStart=/usr/bin/python3 /opt/wazuh-ml/inference_service.py --model /opt/wazuh-ml/xgb_model.json --metrics /opt/wazuh-ml/xgb_model_metrics.json --db /tmp/predictions.db
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
SERVICEEOF

echo "=== Fix 2: Ajout regles UFW manquantes ==="
sudo ufw allow from 192.168.30.10 to any port 9090 proto tcp comment 'API ML depuis Target'
sudo ufw allow from 192.168.30.10 to any port 55000 proto tcp comment 'Wazuh API Target'
sudo ufw allow from 127.0.0.1 to any port 55000 proto tcp comment 'Wazuh API locale'
sudo ufw allow from 192.168.30.10 to any port 1515 proto tcp comment 'Wazuh Agent TCP'
sudo ufw allow from 127.0.0.1 to any port 9200 proto tcp comment 'OpenSearch local'
sudo ufw allow from 127.0.0.1 to any port 443 proto tcp comment 'Dashboard local'
sudo ufw status numbered

echo "=== Fix 3: Reload inference + verif ==="
sudo systemctl daemon-reload
sudo systemctl restart wazuh-inference
sleep 4
echo "Inference: $(sudo systemctl is-active wazuh-inference)"

echo "=== Fix 4: Patch inference code (None -> []) ==="
sudo sed -i 's/feature_names = model.get_booster().feature_names/fn = model.get_booster().feature_names\n            feature_names = fn if fn else []/' /opt/wazuh-ml/inference_service.py
# Fallback si le sed n'a pas matché, approche plus robuste
sudo python3 -c "
import re
with open('/opt/wazuh-ml/inference_service.py', 'r') as f:
    content = f.read()
# Replace the dangerous block
old = '''        try:
            feature_names = model.get_booster().feature_names
        except Exception:
            pass
        print(f\"[WARN] Using {len(feature_names)} feature names from model\")'''
new = '''        try:
            fn = model.get_booster().feature_names
            feature_names = fn if fn else []
        except Exception:
            feature_names = []
        print(f\"[WARN] Using {len(feature_names)} feature names from model\")'''
if old in content:
    content = content.replace(old, new)
    with open('/opt/wazuh-ml/inference_service.py', 'w') as f:
        f.write(content)
    print('[OK] Inference code patched')
else:
    print('[OK] Already patched or different code path')
"

echo "=== Fix 5: Restart + verif finale ==="
sudo systemctl restart wazuh-inference
sleep 4
echo "Inference: $(sudo systemctl is-active wazuh-inference)"
sudo systemctl status wazuh-inference --no-pager -l 2>&1 | tail -10

echo "=== Verif API ML ==="
curl -s http://127.0.0.1:9090/health
echo ""
curl -s http://127.0.0.1:9090/stats
echo ""
curl -s http://127.0.0.1:9090/predictions/recent

echo ""
echo "=== DONE ==="
