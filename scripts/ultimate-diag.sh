#!/bin/bash
set -euo pipefail
# suricata-ultimate-diag.sh — Diagnostic complet Suricata pour Ubuntu 22.04

echo "================================================================"
echo " SURICATA ULTIMATE DIAGNOSTIC — $(date)"
echo "================================================================"

echo ""
echo "==================== 1. RÉSEAU & INTERFACES ===================="
echo ""
echo "--- Interfaces ---"
ip -br a 2>/dev/null || ip a
echo ""
echo "--- Route ---"
ip r 2>/dev/null || route -n
echo ""
echo "--- Promiscuité ---"
for iface in $(ip -br link | awk '{print $1}' | grep -v lo); do
    promisc=$(ip -br link show "$iface" 2>/dev/null | grep -o "PROMISC" || echo "OFF")
    echo "  $iface: $promisc"
done

echo ""
echo "==================== 2. STATUT SERVICE ========================="
echo ""
systemctl status suricata --no-pager 2>&1 | head -12
echo ""
echo "--- Journal récent ---"
journalctl -u suricata --since "5 min ago" --no-pager 2>/dev/null | tail -20

echo ""
echo "==================== 3. FICHIER DE CONFIGURATION ==============="
echo ""
echo "--- HOME_NET ---"
grep "^    HOME_NET" /etc/suricata/suricata.yaml || echo "  (non trouvé)"
echo ""
echo "--- EXTERNAL_NET ---"
grep "^    EXTERNAL_NET" /etc/suricata/suricata.yaml || echo "  (non trouvé)"
echo ""
echo "--- af-packet interfaces ---"
grep -A50 "^af-packet:" /etc/suricata/suricata.yaml | grep "interface:" | head -5
echo ""
echo "--- default-rule-path ---"
grep "^default-rule-path" /etc/suricata/suricata.yaml
echo ""
echo "--- rule-files ---"
sed -n '/^rule-files:/,/^[a-z#]/p' /etc/suricata/suricata.yaml | head -10
echo ""
echo "--- eve-log enabled: ---"
grep -A3 "eve-log:" /etc/suricata/suricata.yaml | grep "enabled:" | head -3
echo ""
echo "--- fast.log enabled: ---"
grep -A3 "fast:" /etc/suricata/suricata.yaml | grep "enabled:" | head -3
echo ""
echo "--- portscan module ---"
grep -A8 "^portscan:" /etc/suricata/suricata.yaml || echo "  (ABSENT — module portscan pas configuré)"

echo ""
echo "==================== 4. RÈGLES ================================="
echo ""
DEFAULT_RULES=$(grep "^default-rule-path" /etc/suricata/suricata.yaml | awk '{print $2}')
echo "--- Chemin configuré: $DEFAULT_RULES ---"
if [ -f "$DEFAULT_RULES/suricata.rules" ]; then
    echo "  suricata.rules présent"
    echo "  Taille: $(wc -l < "$DEFAULT_RULES/suricata.rules") lignes"
    echo "  Poids: $(du -h "$DEFAULT_RULES/suricata.rules" | cut -f1)"
else
    echo "  ❌ suricata.rules ABSENT dans $DEFAULT_RULES"
fi
echo ""
echo "--- local.rules ---"
if [ -f "$DEFAULT_RULES/local.rules" ]; then
    echo "  local.rules présent (taille: $(wc -l < "$DEFAULT_RULES/local.rules") règles)"
    cat "$DEFAULT_RULES/local.rules"
else
    echo "  ❌ PAS de local.rules dans $DEFAULT_RULES"
    if [ -f /etc/suricata/rules/local.rules ]; then
        echo "  → local.rules TROUVÉ dans /etc/suricata/rules/ (Mauvais endroit !)"
    fi
fi

echo ""
echo "--- Règles chargées (logs) ---"
grep "rules successfully loaded" /var/log/suricata/suricata.log 2>/dev/null | tail -3 || echo "  (log pas trouvé)"

echo ""
echo "==================== 5. COMPTAGE EVE.JSON ====================="
echo ""
EVE=/var/log/suricata/eve.json
if [ -f "$EVE" ]; then
    python3 << 'PYEOF'
import json, os
eve = "/var/log/suricata/eve.json"
alerts = portscans = flows = stats = others = total = 0
last5 = []
try:
    f = open(eve)
    for line in f:
        total += 1
        d = json.loads(line.strip())
        et = d.get('event_type', '?')
        if et == 'alert': alerts += 1
        elif et == 'portscan': portscans += 1
        elif et == 'flow': flows += 1
        elif et == 'stats': stats += 1
        else: others += 1
        if total > total - 5:
            last5.append(d)
    f.close()
except Exception as e:
    print(f"  Erreur: {e}")

print(f"  Lignes totales:  {total}")
print(f"  Alerts:          {alerts}")
print(f"  Portscans:       {portscans}")
print(f"  Flows:           {flows}")
print(f"  Stats:           {stats}")
print(f"  Autres:          {others}")

if total > 0:
    print(f"\n  Dernières 3 lignes (event_type):")
    try:
        import subprocess
        r = subprocess.run(['tail', '-3', eve], capture_output=True, text=True)
        for line in r.stdout.strip().split('\n'):
            if line.strip():
                d = json.loads(line)
                t = d.get('event_type', '?')
                print(f"    {t}: src={d.get('src_ip','?')} dst={d.get('dest_ip','?')} proto={d.get('proto','?')}")
    except:
        pass
PYEOF
else
    echo "  ❌ eve.json n'existe pas"
fi

echo ""
echo "==================== 6. TEST SYNTAXE SURICATA ================="
echo ""
sudo suricata -T -c /etc/suricata/suricata.yaml -v 2>&1 | tail -15

echo ""
echo "==================== 7. TEST DE TRAFIC RAPIDE ================="
echo ""
echo "--- Test de connectivité vers le Wazuh Manager ---"
ping -c 2 -W 2 192.168.30.3 2>&1 | tail -3
echo ""
echo "--- Capture 3 paquets sur enp0s8 (attends le scan) ---"
timeout 4 tcpdump -i enp0s8 -c 3 -n 2>&1 | tail -5 || echo "  (pas de trafic pendant le test)"

echo ""
echo "================================================================"
echo " DIAGNOSTIC TERMINÉ"
echo " Copie-colle toute cette sortie dans le chat."
echo "================================================================"
