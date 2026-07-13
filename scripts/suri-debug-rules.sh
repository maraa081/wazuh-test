#!/bin/bash
# suri-debug-rules.sh — Debug des règles Suricata
# Usage: sudo bash suri-debug-rules.sh

echo "=========================================="
echo " DEBUG REGLES SURICATA"
echo "=========================================="

# 1 — Où sont les règles ?
echo ""
echo "=== 1. Default rule path ==="
grep "default-rule-path" /etc/suricata/suricata.yaml

echo ""
echo "=== 2. Rule-files chargés ==="
sed -n '/rule-files:/,/^[a-z]/p' /etc/suricata/suricata.yaml | head -10

echo ""
echo "=== 3. local.rules existe-t-il au bon endroit ? ==="
DEFAULT_PATH=$(grep "default-rule-path" /etc/suricata/suricata.yaml | awk '{print $2}')
echo "  Default path: $DEFAULT_PATH"
ls -la "$DEFAULT_PATH/local.rules" 2>/dev/null || echo "  ❌ PAS de local.rules dans $DEFAULT_PATH"
ls -la "/etc/suricata/rules/local.rules" 2>/dev/null || echo "  ❌ PAS de local.rules dans /etc/suricata/rules/"

echo ""
echo "=== 4. Copie de local.rules dans le bon dossier ==="
if [ -f /etc/suricata/rules/local.rules ]; then
    cp /etc/suricata/rules/local.rules /var/lib/suricata/rules/local.rules
    chown suricata:suricata /var/lib/suricata/rules/local.rules 2>/dev/null || true
    echo "  ✅ Copié dans $DEFAULT_PATH"
fi
ls -la /var/lib/suricata/rules/local.rules

echo ""
echo "=== 5. Vérification des flux (flows récents dans eve.json) ==="
python3 -c "
import json
count = 0
with open('/var/log/suricata/eve.json') as f:
    for line in f:
        d = json.loads(line.strip())
        if d.get('event_type') == 'flow':
            print(f\"  flow: {d.get('src_ip')}:{d.get('src_port','?')} -> {d.get('dest_ip')}:{d.get('dest_port','?')} proto={d.get('proto')} app={d.get('app_proto','?')}\")
            count += 1
            if count >= 5: break
"

echo ""
echo "=== 6. Test direct: Suricata vérifie-t-il les règles ? ==="
suricata -T -c /etc/suricata/suricata.yaml 2>&1 | tail -10

echo ""
echo "=========================================="
echo " RÉSULTAT:"
echo " Si tests OK, relance nmap depuis ParrotOS"
echo " Puis compte: sudo python3 -c \"import json;a=p=0;f=open('/var/log/suricata/eve.json');[exec('d=json.loads(l);exec(\\\"a+=1\\\" if d[\\\"event_type\\\"]==\\\"alert\\\" else \\\"p+=1\\\" if d[\\\"event_type\\\"]==\\\"portscan\\\" else \\\"\\\")') for l in f];print(f'A={a} P={p}')\" 2>/dev/null"
echo "=========================================="
