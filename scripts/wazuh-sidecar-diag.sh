#!/bin/bash
# wazuh-sidecar-diag.sh — Diagnostic complet du sidecar ML
# Usage: bash wazuh-sidecar-diag.sh

echo "================================================================"
echo " WAZUH ML SIDECAR DIAGNOSTIC — $(date)"
echo "================================================================"
echo ""

# 1 — Processus
echo "=== 1. Processus ==="
INF_PID=$(ps aux | grep inference | grep -v grep | awk '{print $2}')
API_PID=$(ps aux | grep api_service | grep -v grep | awk '{print $2}')
if [ -n "$INF_PID" ]; then echo "  Inference: PID $INF_PID (OK)"; else echo "  Inference: NOT RUNNING"; fi
if [ -n "$API_PID" ]; then echo "  API:       PID $API_PID (OK)"; else echo "  API:       NOT RUNNING"; fi

# 2 — Port 9090
echo ""
echo "=== 2. Port 9090 ==="
ss -tlnp | grep 9090 || echo "  Rien n ecoute sur 9090"

# 3 — Endpoints
echo ""
echo "=== 3. Endpoints ==="
for ep in "/health" "/stats" "/predictions?limit=2"; do
    code=$(curl -s -o /dev/null -w "%{http_code}" "http://127.0.0.1:9090$ep" 2>/dev/null || echo "000")
    if [ "$code" = "200" ]; then
        echo "  GET $ep -> $code (OK)"
    else
        echo "  GET $ep -> $code (FAIL)"
    fi
done

# 4 — DB
echo ""
echo "=== 4. Base SQLite ==="
DB="/tmp/predictions.db"
if [ -f "$DB" ]; then
    SZ=$(du -h "$DB" | cut -f1)
    echo "  Fichier: $DB ($SZ)"
    python3 -c "
import sqlite3
c = sqlite3.connect('$DB')
total = c.execute('SELECT COUNT(*) FROM predictions').fetchone()[0]
tp = c.execute('SELECT COUNT(*) FROM predictions WHERE prediction=1').fetchone()[0]
fp = total - tp
print(f'  Predictions: {total} (TP: {tp}, FP: {fp})')
recent = c.execute('SELECT timestamp, rule_id, prediction, confidence FROM predictions ORDER BY timestamp DESC LIMIT 3').fetchall()
print(f'  3 dernieres:')
for ts, rid, pred, conf in recent:
    print(f'    {ts[:19]} | rule={rid} | {\"TP\" if pred else \"FP\"} | conf={conf:.3f}')
"
else
    echo "  DB NOT FOUND: $DB"
fi

# 5 — alerts.json
echo ""
echo "=== 5. Fichier d alertes ==="
AJ="/var/ossec/logs/alerts/alerts.json"
if [ -f "$AJ" ]; then
    SZ=$(du -h "$AJ" | cut -f1)
    LINES=$(wc -l < "$AJ")
    echo "  Fichier: $AJ ($SZ, $LINES lignes)"
    echo "  Perms: $(stat -c '%a %U:%G' "$AJ" 2>/dev/null || echo 'N/A')"
    # Dernière alerte Suricata
    SURICATA=$(grep -c "suricata" "$AJ" 2>/dev/null || echo "0")
    echo "  Alertes Suricata: $SURICATA"
    tail -1 "$AJ" 2>/dev/null | python3 -c "
import sys,json
try:
    d=json.loads(sys.stdin.read())
    print(f'  Derniere alerte: {d.get(\"timestamp\",\"?\")} | {d[\"rule\"][\"description\"][:50]}')
except: print('  (derniere alerte indisponible)')
" 2>/dev/null
else
    echo "  NOT FOUND"
fi

# 6 — Modele
echo ""
echo "=== 6. Modele XGBoost ==="
MODEL="/tmp/xgb_model.json"
if [ -f "$MODEL" ]; then
    SZ=$(du -h "$MODEL" | cut -f1)
    echo "  Fichier: $MODEL ($SZ)"
    python3 -c "import xgboost; m=xgboost.XGBClassifier(); m.load_model('$MODEL'); print(f'  OK: {m.get_params()}')" 2>/dev/null || echo "  FAIL: modele corrompu"
else
    echo "  NOT FOUND: $MODEL"
fi

echo ""
echo "================================================================"
echo " DIAGNOSTIC TERMINE"
echo "================================================================"
