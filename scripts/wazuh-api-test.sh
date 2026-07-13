#!/bin/bash
# wazuh-api-test.sh — Test complet API Wazuh
# Usage: sudo WAZUH_API_PASS='password' bash wazuh-api-test.sh

echo "================================================================"
echo " WAZUH API TEST — $(date)"
echo "================================================================"

API_USER="${WAZUH_API_USER:-wazuh-wui}"
API_PASS="${WAZUH_API_PASS:-}"
BASE="https://localhost:55000"

if [ -z "$API_PASS" ]; then
  echo "Erreur: Mot de passe manquant."
  echo "Usage: sudo WAZUH_API_PASS='mon_password' bash $0"
  exit 1
fi

echo "--- 1. Authentification ---"
TMPFILE=$(mktemp)
curl -su "${API_USER}:${API_PASS}" -k "${BASE}/security/user/authenticate" > "$TMPFILE" 2>/dev/null
TOKEN=$(python3 -c "import json;print(json.load(open('$TMPFILE'))['data']['token'])" 2>/dev/null || echo "")
rm -f "$TMPFILE"
if [ -z "$TOKEN" ]; then
  echo "Echec auth"
  exit 1
fi
echo "OK (${#TOKEN} caracteres)"

echo ""
echo "--- 2. Endpoints ---"
for ep in "/" "/agents?limit=5" "/security/alerts?limit=5" "/alerts?limit=5"; do
  code=$(curl -sk -o /dev/null -w "%{http_code}" -H "Authorization: Bearer $TOKEN" "${BASE}${ep}" 2>/dev/null)
  echo "  ${ep} -> HTTP ${code}"
done

echo ""
echo "--- 3. Agents ---"
curl -sk -H "Authorization: Bearer $TOKEN" "${BASE}/agents?limit=20" 2>/dev/null | python3 -c "
import sys,json
d=json.load(sys.stdin)
items=d.get('data',{}).get('affected_items',d.get('data',[]))
for a in items:
  print('  [{}] {:20} IP: {:15} Status: {}'.format(a.get('id'),a.get('name','?'),a.get('ip','?'),a.get('status','?')))
"

echo ""
echo "--- 4. Scan alerts ---"
# Find working endpoint
EP="/alerts"
if curl -sk -o /dev/null -w "%{http_code}" -H "Authorization: Bearer $TOKEN" "${BASE}/security/alerts?limit=1" 2>/dev/null | grep -q 200; then
  EP="/security/alerts"
fi
curl -sk -H "Authorization: Bearer $TOKEN" "${BASE}${EP}?limit=50&sort=timestamp" 2>/dev/null | python3 -c "
import sys,json
d=json.load(sys.stdin)
items=d.get('data',{}).get('affected_items',d.get('data',[]))
print('  Total: {} items'.format(len(items)))
for a in items:
  desc=a.get('rule',{}).get('description','')
  if 'scan' in desc.lower() or 'nmap' in desc.lower():
    print('  [L{}] {} | {}'.format(a.get('rule',{}).get('level'),desc,a.get('agent',{}).get('name','?')))
"

echo ""
echo "--- 5. Fallback local ---"
python3 -c "
try:
  f=open('/var/ossec/logs/alerts/alerts.json')
  c=0
  for line in f:
    d=json.loads(line.strip())
    r=d.get('rule',{})
    if 'scan' in r.get('description','').lower():
      print('  [L{}] {} | {}'.format(r.get('level'),r.get('description'),d.get('agent',{}).get('name')))
      c+=1
      if c>=5: break
  f.close()
  if c==0: print('  Aucune alerte scan')
except:
  print('  Fichier non accessible: /var/ossec/logs/alerts/alerts.json')
" 2>/dev/null
