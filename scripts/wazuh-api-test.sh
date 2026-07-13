#!/bin/bash
# wazuh-api-test.sh — Test complet API Wazuh
# Usage: sudo bash wazuh-api-test.sh

echo "================================================================"
echo " WAZUH API TEST — $(date)"
echo "================================================================"
echo ""

# Credentials (extracted from install tar)
API_USER="wazuh-wui"
API_PASS="tpuKUfY7Auj2kd9yeRBwgiNjHH+mmNso"
BASE="https://localhost:55000"

# Get token
echo "--- 1. Authentification ---"
AUTH_JSON=*** -su "${API_USER}:${API_PASS}" -k "${BASE}/security/user/authenticate" 2>/dev/null)
if [ $? -ne 0 ] || [ -z "$AUTH_JSON" ]; then
    echo "❌ Échec authentification"
    exit 1
fi

TOKEN=$(echo "$AUTH_JSON" | python3 -c "import sys,json;print(json.load(sys.stdin).get('data',{}).get('token',''))" 2>/dev/null)
if [ -z "$TOKEN" ]; then
    echo "❌ Token vide"
    echo "Réponse brute: $AUTH_JSON"
    exit 1
fi
echo "✅ Token obtenu: ${TOKEN:***"

# Test endpoints
echo ""
echo "--- 2. Test endpoints ---"
for ep in "/" "/security/alerts" "/alerts" "/agents" "/agents?limit=5"; do
    code=$(curl -sk -o /tmp/api_resp.json -w "%{http_code}" -H "Authorization: Bearer $TOKEN" "${BASE}${ep}" 2>/dev/null)
    echo "  ${ep} → HTTP ${code}"
    if [ "$code" = "200" ]; then
        # Show first structure
        python3 -c "
import json
d = json.load(open('/tmp/api_resp.json'))
print(f\"    Keys: {list(d.keys())}\")
items = d.get('data',{}).get('affected_items',[]) or d.get('data',[])
if isinstance(items, list) and len(items) > 0:
    print(f\"    Items: {len(items)}\")
    print(f\"    Sample keys: {list(items[0].keys())[:8]}\")
" 2>/dev/null
    fi
done

# Show agents
echo ""
echo "--- 3. Agents connectés ---"
curl -sk -H "Authorization: Bearer $TOKEN" "${BASE}/agents?limit=20" 2>/dev/null | python3 -c "
import sys,json
d = json.load(sys.stdin)
for a in d.get('data',{}).get('affected_items',[]):
    print(f\"  [{a.get('id','?')}] {a.get('name','?'):20} IP: {a.get('ip','?'):15} Status: {a.get('status','?')}\")
" 2>/dev/null

# Show recent alerts (try different endpoints)
echo ""
echo "--- 4. Alertes récentes ---"
for ep in "/security/alerts" "/alerts"; do
    resp=$(curl -sk -o /tmp/alerts.json -w "%{http_code}" -H "Authorization: Bearer $TOKEN" "${BASE}${ep}?limit=5&sort=timestamp" 2>/dev/null)
    if [ "$resp" = "200" ]; then
        echo "  Endpoint ${ep}:"
        python3 -c "
import json
d = json.load(open('/tmp/alerts.json'))
items = d.get('data',{}).get('affected_items',[])
if not items:
    # essayer data directement
    items = d.get('data',[])
print(f\"    {len(items)} alertes\")
for a in items[:5]:
    r = a.get('rule',{})
    if r:
        print(f\"    [L{r.get('level')}] {r.get('description','?')}\")
    else:
        print(f\"    {list(a.keys())[:5]}\")
" 2>/dev/null
        break
    fi
done

# If no alerts found, try to get them from the Manager's alerts.json directly
echo ""
echo "--- 5. Fallback: alerts.json local ---"
if [ -f /var/ossec/logs/alerts/alerts.json ]; then
    python3 -c "
import json
count=0
with open('/var/ossec/logs/alerts/alerts.json') as f:
    for line in f:
        try:
            d = json.loads(line.strip())
            r = d.get('rule',{})
            cp = d.get('agent',{}).get('name','?')
            if 'scan' in r.get('description','').lower() or 'nmap' in r.get('description','').lower():
                print(f\"  [L{r.get('level')}] {r.get('description','?')} | {cp}\")
                count+=1
                if count>=5: break
        except: pass
if count==0:
    print('  Aucune alerte scan dans le fichier local')
    print('  Fais d abord un nmap depuis ParrotOS')
    print('  nmap -sS -p 22,80 192.168.30.10')
" 2>/dev/null
fi

echo ""
echo "================================================================"
echo " TEST TERMINÉ"
echo "================================================================"
