#!/bin/bash
# wazuh-api-check.sh — Vérifie l'API Wazuh et trouve les credentials
# Usage: sudo bash wazuh-api-check.sh
set -euo pipefail

echo "================================================================"
echo " WAZUH API CHECK — $(date)"
echo "================================================================"
echo ""

# ─── 1. Vérifier si l'API tourne ───
echo "=== 1. API Wazuh status ==="
systemctl is-active wazuh-api 2>/dev/null && echo "  API: running" || echo "  API: not running (unifié dans manager depuis 4.x)"
systemctl is-active wazuh-manager 2>/dev/null && echo "  Manager: running" || echo "  Manager: not running"

# ─── 2. Tester l'API sur ses ports ───
echo ""
echo "=== 2. Port API ==="
curl -sk https://localhost:55000 -o /dev/null -w "  Port 55000 (HTTPS): %{http_code}\n" 2>/dev/null || echo "  Port 55000: pas de réponse"
curl -sk http://localhost:55000 -o /dev/null -w "  Port 55000 (HTTP):  %{http_code}\n" 2>/dev/null || echo "  Port 55000 HTTP: pas de réponse"

# ─── 3. Chercher les credentials ───
echo ""
echo "=== 3. Recherche des credentials ==="

# Méthode 1: fichier internal_users
echo "--- Users connus (OpenSearch) ---"
sudo cat /etc/wazuh-indexer/opensearch-security/internal_users.yml 2>/dev/null | grep -E "^[a-z]" | grep -v "#" | grep -v "^\s" | grep ":" | sed 's/:$//' | while read u; do
    echo "  User trouvé: $u"
done

# Méthode 2: wazuh-dashboard config
echo "--- Config dashboard ---"
sudo grep -v "^#" /etc/wazuh-dashboard/opensearch_dashboards.yml 2>/dev/null | grep -v "^\s*$" | head -20

# Méthode 3: Fichier API users
echo "--- Config API users ---"
sudo cat /etc/wazuh-api/configuration/api.yaml 2>/dev/null | grep -A5 "users" || echo "  (pas de fichier dédié)"
sudo grep -r "password\|username" /var/ossec/api/ 2>/dev/null | head -5 || true

# Méthode 4: Installer Wazuh (password de l'assistant)
echo "--- Installation Wazuh (config) ---"
ls /etc/wazuh-indexer/certs/ 2>/dev/null | head -5 || echo "  (pas de dossier certs)"

# ─── 4. Tester des credentials courants ───
echo ""
echo "=== 4. Test de credentials courants ==="
PASSWORDS=("wazuh-wui" "wazuh" "admin" "Admin123" "kibanaserver" "Password123" "changeme")
for user in wazuh-wui admin wazuh; do
    for pass in "${PASSWORDS[@]}"; do
        code=$(curl -sku "$user:$pass" -o /dev/null -w "%{http_code}" "https://localhost:55000/security/user/authenticate" 2>/dev/null || echo "000")
        if [ "$code" = "200" ]; then
            echo "  ✅ $user / $pass = VALIDE"
            # Récupérer un token
            TOKEN=$(curl -sku "$user:$pass" "https://localhost:55000/security/user/authenticate" 2>/dev/null | python3 -c "import sys,json; print(json.load(sys.stdin).get('token',''))" 2>/dev/null || echo "")
            if [ -n "$TOKEN" ]; then
                echo "  Token: ${TOKEN:0:30}..."
                echo ""
                echo "=== 5. Test API avec token ==="
                curl -sk -H "Authorization: Bearer $TOKEN" \
                  "https://localhost:55000/security/alerts?limit=5&sort=timestamp" \
                  | python3 -c "
import sys, json
try:
    d = json.load(sys.stdin)
    items = d.get('data',{}).get('affected_items',[])
    print(f\"  {len(items)} alertes récupérées\")
    for a in items:
        r = a.get('rule',{})
        print(f\"  [L{r.get('level',0)}] {r.get('description','?')} | {a.get('agent',{}).get('name','?')}\")
except Exception as e:
    print(f\"  Erreur: {e}\")
    print(f\"  Réponse brute: {sys.stdin.read()[:200]}\")
" 2>/dev/null
                exit 0
            fi
        fi
    done
done

# ─── 5. Si rien trouvé, proposer les alternatives ───
echo ""
echo "=== 5. Aucun credential valide trouvé ==="
echo ""
echo "Solutions:"
echo ""
echo "  A) Reset via Security Admin:"
echo "     cd /usr/share/wazuh-indexer/plugins/opensearch-security/tools/"
echo "     sudo ./securityadmin.sh -cd /etc/wazuh-indexer/opensearch-security/ -cacert /etc/wazuh-indexer/certs/root-ca.pem -cert /etc/wazuh-indexer/certs/admin.pem -key /etc/wazuh-indexer/certs/admin-key.pem"
echo ""
echo "  B) Reset password wazuh-wui:"
echo "     sudo /usr/share/wazuh-indexer/plugins/opensearch-security/tools/hash.sh -p <NOUVEAU_PASS>"
echo "     (copier le hash, puis éditer internal_users.yml)"
echo ""
echo "  C) Voir les logs d'installation:"
echo "     sudo tail -100 /var/log/wazuh-install.log"
echo ""
echo "================================================================"
