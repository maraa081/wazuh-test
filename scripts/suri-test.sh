#!/bin/bash
# suri-test.sh — Test complet Suricata
# Usage: sudo bash suri-test.sh
# Affiche alertes, erreurs, fait un test de détection, un comptage.

set -euo pipefail
LOG=/var/log/suricata/eve.json

echo "=========================================="
echo " SURICATA TEST — $(date)"
echo "=========================================="
echo ""

# 1 — Statut
echo "=== 1. Service ==="
systemctl is-active suricata && echo "  OK: running" || echo "  KO: not running"

# 2 — Erreurs récentes
echo ""
echo "=== 2. Dernières erreurs ==="
journalctl -u suricata --since "5 min ago" --no-pager 2>/dev/null | grep -iE "error|fail|warning" | tail -5 || echo "  Aucune erreur"

# 3 — Règles chargées
echo ""
echo "=== 3. Règles ==="
echo "  Fichier custom:"
cat /etc/suricata/rules/local.rules 2>/dev/null | grep "^alert" | sed 's/.*sid:/  sid:/' || echo "  (pas de fichier)"
echo ""
journalctl -u suricata --since "10 min ago" --no-pager 2>/dev/null | grep "rules successfully" | tail -1

# 4 — Test de détection (NIDS test rule)
echo ""
echo "=== 4. Test détection (testmynids.org) ==="
curl -s http://testmynids.org/uid/index.html >/dev/null 2>&1 && echo "  Test envoyé" || echo "  Échec requête"
sleep 1

# 5 — Comptage eve.json
echo ""
echo "=== 5. Comptage eve.json ==="
python3 << 'PYEOF'
import json
alerts = 0
portscans = 0
flows = 0
stats = 0
total = 0
try:
    with open('/var/log/suricata/eve.json') as f:
        for line in f:
            total += 1
            d = json.loads(line.strip())
            et = d.get('event_type', '')
            if et == 'alert': alerts += 1
            elif et == 'portscan': portscans += 1
            elif et == 'flow': flows += 1
            elif et == 'stats': stats += 1
except Exception as e:
    print(f"  Erreur lecture: {e}")

print(f"  Lignes totales: {total}")
print(f"  Alerts:        {alerts}")
print(f"  Portscans:     {portscans}")
print(f"  Flows:         {flows}")
print(f"  Stats:         {stats}")

# Afficher les 5 dernières alertes si existent
if alerts > 0:
    print(f"\n  Dernières alertes:")
    count = 0
    for line in open('/var/log/suricata/eve.json'):
        d = json.loads(line.strip())
        if d.get('event_type') == 'alert':
            print(f"    [{d.get('src_ip')}] {d.get('alert',{}).get('signature','?')}")
            count += 1
            if count >= 5: break
else:
    print(f"\n  ⚠️ Aucune alerte détectée.")
    print(f"  Dernières 3 lignes du fichier:")
    import subprocess
    result = subprocess.run(['tail', '-3', '/var/log/suricata/eve.json'], capture_output=True, text=True)
    for line in result.stdout.strip().split('\n'):
        if line:
            d = json.loads(line)
            print(f"    {d.get('event_type')}: src={d.get('src_ip','?')} dst={d.get('dest_ip','?')}")
PYEOF

echo ""
echo "=========================================="
echo " Si 0 alertes, vérifie depuis ParrotOS :"
echo "   nmap -sS -p 22,80 192.168.30.10"
echo " Puis relance: sudo bash suri-test.sh"
echo "=========================================="
