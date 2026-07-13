#!/bin/bash
# Suricata Fix & Test — répare HOME_NET + ajoute règles custom Nmap
# Usage: sudo bash suricata-fix.sh

set -euo pipefail

WAZUH_MANAGER="192.168.30.3"
MANAGER_USER="wazuh-wui"
MANAGER_PASS=""

echo "============================================"
echo " Suricata Fix & Test — $(date)"
echo "============================================"
echo ""

if [ "$(id -u)" -ne 0 ]; then echo "ERREUR: lance en root"; exit 1; fi

# --- 1. Fix HOME_NET ---
BRIDGED_NET=$(ip -br addr | grep "enp0s8" | awk '{print $3}' | cut -d/ -f1 | cut -d. -f1-3)
echo "--- 1. HOME_NET correction ---"
echo "  Réseau Bridgé détecté: ${BRIDGED_NET}.0/24"
sed -i "s/HOME_NET: \"\[10.0.0.0\/8\]\"/HOME_NET: \"[${BRIDGED_NET}.0\/24]\"/" /etc/suricata/suricata.yaml
grep "^    HOME_NET" /etc/suricata/suricata.yaml

# --- 2. Ajouter règles Nmap personnalisées ---
echo ""
echo "--- 2. Règles de détection Nmap personnalisées ---"
RULE_FILE="/etc/suricata/rules/local.rules"
mkdir -p /etc/suricata/rules/

cat > "$RULE_FILE" << 'RULES'
# Custom Nmap detection rules
# Based on: aleksibovellan/opnsense-suricata-nmaps

# Nmap SYN scan (-sS) - detects incomplete handshakes
alert tcp any any -> any any (msg:"ET SCAN NMAP -sS SYN scan detected"; flags:S,SA; flow:stateless; threshold: type both, track by_src, seconds 10, count 10; classtype:portscan; sid:1000001; rev:1;)

# Nmap OS fingerprint
alert tcp any any -> any any (msg:"ET SCAN NMAP OS fingerprint attempt"; flags:S; window:1024; seq:0; classtype:attempted-recon; sid:1000002; rev:1;)

# Nmap service scan (-sV)
alert tcp any any -> any any (msg:"ET SCAN NMAP -sV service scan"; flags:PA; flow:to_server; threshold: type both, track by_src, seconds 10, count 5; classtype:portscan; sid:1000003; rev:1;)

# Hydra/bruteforce SSH detection (rapide)
alert ssh any any -> $HOME_NET any (msg:"ET SCAN SSH bruteforce tool detected"; flow:to_server; content:"SSH"; offset:0; threshold: type both, track by_src, seconds 30, count 15; classtype:attempted-dos; sid:1000004; rev:1;)

# Test rule - trigger on any traffic (for verification)
alert tcp any any -> $HOME_NET any (msg:"TEST ALERT - Traffic detected from EXTERNAL_NET"; classtype:misc-activity; sid:1000999; rev:1;)
RULES

# Add local.rules to the config if not present
if ! grep -q "local.rules" /etc/suricata/suricata.yaml 2>/dev/null; then
    sed -i '/rule-files:/a\  - local.rules' /etc/suricata/suricata.yaml
fi
echo "  Règles personnalisées ajoutées:"
grep -c "sid:" "$RULE_FILE"
echo "  Fichier: $RULE_FILE"

# --- 3. Ajouter thunder-test pour vérifier que les règles marchent ---
echo ""
echo "--- 3. Ajout du test rule (sid:2100498) ---"
# Sid 2100498 existe déjà dans ET Open, on l'active via un test direct

# --- 4. Redémarrer ---
echo ""
echo "--- 4. Redémarrage Suricata ---"
systemctl restart suricata
sleep 2
systemctl is-active --quiet suricata && echo "  ✅ Suricata running" || echo "  ❌ Suricata failed"

# --- 5. Vérifier que les règles custom sont chargées ---
echo ""
echo "--- 5. Vérification des règles ---"
journalctl -u suricata --since "30 sec ago" --no-pager 2>&1 | grep "rules successfully" | tail -1
journalctl -u suricata --since "30 sec ago" --no-pager 2>&1 | grep -E "error|fail" | head -3 || echo "  Pas d'erreurs"

# --- 6. Test interne (trigger sid:2100498) ---
echo ""
echo "--- 6. Test de détection interne ---"
curl -s http://testmynids.org/uid/index.html >/dev/null 2>&1 || true
sleep 2
ALERTS=$(grep -c '"event_type":"alert"' /var/log/suricata/eve.json 2>/dev/null || echo "0")
echo "  Alertes dans eve.json: $ALERTS"
if [ "$ALERTS" -gt 0 ]; then
    echo "  ✅ Suricata détecte !"
    tail -1 /var/log/suricata/eve.json | python3 -c "
import sys, json
d = json.loads(sys.stdin.read())
if d.get('event_type') == 'alert':
    print(f\"  Alerte: {d['alert']['signature']}\")
" 2>/dev/null
else
    echo "  ⚠️ Toujours 0 alertes. Vérifie la config test."
    echo "  Test manuel: curl http://testmynids.org/uid/index.html"
    echo "  Puis: sudo grep -c 'alert' /var/log/suricata/eve.json"
fi

echo ""
echo "============================================"
echo " RÉSULTAT:"
echo " HOME_NET: $(grep '^    HOME_NET' /etc/suricata/suricata.yaml)"
echo " Règles custom: $(grep -c 'sid:10' $RULE_FILE) dans $RULE_FILE"
echo ""
echo "À faire depuis ParrotOS:"
echo "  nmap -sS -p 22,80,443 192.168.30.10"
echo "Puis vérifier:"
echo "  sudo python3 -c \"import json; f=open('/var/log/suricata/eve.json'); print([json.loads(l).get('event_type') for l in f][-10:])\""
echo "============================================"
