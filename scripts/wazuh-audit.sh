#!/bin/bash
# wazuh-audit.sh — Audit de l'environnement Wazuh pour intégration ML
# Usage: sudo bash wazuh-audit.sh
set -uo pipefail

echo "================================================================"
echo " WAZUH ENVIRONMENT AUDIT — $(date)"
echo "================================================================"
echo ""

if [ "$(id -u)" -ne 0 ]; then echo "ERREUR: Lance en root"; exit 1; fi

# ─── 1. Version Wazuh ───
echo "=== 1. VERSIONS ==="
echo ""
echo "--- Wazuh Manager ---"
dpkg -l | grep wazuh-manager 2>/dev/null | awk '{print "  Package: " $2 "  Version: " $3}'
/var/ossec/bin/wazuh-control status 2>/dev/null | head -5
echo ""
echo "--- Wazuh Indexer (OpenSearch) ---"
dpkg -l | grep wazuh-indexer 2>/dev/null | awk '{print "  Package: " $2 "  Version: " $3}'
systemctl is-active wazuh-indexer 2>/dev/null && echo "  Service: running" || echo "  Service: not found"
echo ""
echo "--- Wazuh Dashboard ---"
dpkg -l | grep wazuh-dashboard 2>/dev/null | awk '{print "  Package: " $2 "  Version: " $3}'
systemctl is-active wazuh-dashboard 2>/dev/null && echo "  Service: running" || echo "  Service: not found/running"

# ─── 2. Alerts.json ───
echo ""
echo "=== 2. FICHIER D'ALERTES ==="
echo ""
for f in /var/ossec/logs/alerts/alerts.json /var/ossec/logs/alerts/alerts.log; do
    if [ -f "$f" ]; then
        size=$(du -h "$f" | cut -f1)
        lines=$(wc -l < "$f")
        echo "  $f"
        echo "    Size: $size | Lines: $lines"
        echo "    Perms: $(stat -c '%a %U:%G' "$f")"
    else
        echo "  $f: NOT FOUND"
    fi
done

# ─── 3. Filebeat ───
echo ""
echo "=== 3. FILEBEAT ==="
echo ""
if command -v filebeat &>/dev/null; then
    echo "  Filebeat installed: $(filebeat version 2>/dev/null | head -1)"
else
    echo "  Filebeat: NOT INSTALLED"
fi
if [ -f /etc/filebeat/filebeat.yml ]; then
    echo "  Config: /etc/filebeat/filebeat.yml"
    echo "  Output:"
    grep -A5 "output." /etc/filebeat/filebeat.yml 2>/dev/null | head -10 || echo "    (no output configured)"
else
    echo "  Config: NOT FOUND"
fi
systemctl is-active filebeat 2>/dev/null && echo "  Service: running" || echo "  Service: not running"

# ─── 4. Intégrations Wazuh ───
echo ""
echo "=== 4. INTEGRATIONS EXISTANTES ==="
echo ""
ls /var/ossec/integrations/ 2>/dev/null | grep -v ".pyc" | head -10 || echo "  (no integrations directory)"
echo ""
echo "--- config (ossec.conf integrations) ---"
grep -A3 "<integration>" /var/ossec/etc/ossec.conf 2>/dev/null || echo "  (no integrations configured)"

# ─── 5. Ressources système ───
echo ""
echo "=== 5. RESSOURCES ==="
echo ""
echo "--- RAM ---"
free -h | grep -E "^Mem|^Swap"
echo ""
echo "--- CPU ---"
nproc
echo ""
echo "--- RAM libre pour inference ---"
mem_avail=$(free -m | awk '/^Mem:/{print $7}')
echo "  RAM disponible: ${mem_avail}MB"
echo "  Est. besoin inference ML: ~200MB"
if [ "$mem_avail" -gt 500 ]; then
    echo "  SUFFISANT pour tourner sur le Manager"
else
    echo "  INSUFFISANT pour le Manager (preferer micro-service dedie)"
fi

# ─── 6. Python / Dépendances ───
echo ""
echo "=== 6. PYTHON & ML ==="
echo ""
python3 --version 2>/dev/null || echo "  Python3: NOT FOUND"
python3 -c "import xgboost; print('  xgboost:', xgboost.__version__)" 2>/dev/null || echo "  xgboost: NOT INSTALLED"
python3 -c "import numpy; print('  numpy:', numpy.__version__)" 2>/dev/null || echo "  numpy: NOT INSTALLED"

# ─── 7. Mode de déploiement ───
echo ""
echo "=== 7. MODE DEPLOIEMENT ==="
echo ""
echo "--- Outputs configurés (ossec.conf) ---"
grep -E "<server>|<node>" /var/ossec/etc/ossec.conf 2>/dev/null | head -5 || echo "  (check config)"
echo ""
echo "--- Architecture ---"
if systemctl is-active wazuh-indexer 2>/dev/null | grep -q active; then
    echo "  All-in-One (Manager + Indexer + Dashboard sur la meme machine)"
else
    echo "  Manager only (ou architecture distribuee)"
fi

echo ""
echo "================================================================"
echo " AUDIT COMPLETE"
echo "================================================================"
