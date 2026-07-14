#!/bin/bash
# sync_opensearch.sh — Deploie la synchro predictions ML -> Dashboard Wazuh
# Execute SUR LE MANAGER en une commande
# ============================================================

set -e

echo "=== Integration ML Predictions -> Dashboard Wazuh ==="
echo ""

# 1. Creer le script Python
echo "[1/4] Installation du script de synchronisation..."
sudo tee /opt/wazuh-ml/sync_opensearch.py > /dev/null << 'PYEOF'
#!/usr/bin/env python3
"""Sync predictions from SQLite to OpenSearch for Wazuh dashboard."""

import json
import sqlite3
import time
from datetime import datetime
from urllib.request import Request, urlopen
from urllib.error import HTTPError

SQLITE_DB = "/tmp/predictions.db"
OPENSEARCH_URL = "http://admin:YFrxHHO*3QK2y6l6JceItXgQ8zO6Jbwn@127.0.0.1:9200"
INDEX_NAME = "wazuh-ml-predictions"
POLL_INTERVAL = 30

def es(method, path, body=None):
    url = f"{OPENSEARCH_URL}/{path}"
    data = json.dumps(body).encode() if body else None
    req = Request(url, data=data, method=method)
    req.add_header("Content-Type", "application/json")
    try:
        with urlopen(req) as r:
            return json.loads(r.read())
    except HTTPError as e:
        body = e.read().decode()[:200]
        if e.code != 400:
            print(f"[WARN] HTTP {e.code}: {body}")
        return None

def ensure_index():
    mapping = {
        "settings": {"number_of_shards": 1, "number_of_replicas": 0},
        "mappings": {
            "properties": {
                "alert_id": {"type": "keyword"},
                "timestamp": {"type": "date"},
                "rule_id": {"type": "integer"},
                "rule_description": {"type": "text"},
                "src_ip": {"type": "ip"},
                "probability": {"type": "float"},
                "prediction": {"type": "integer"},
                "synced_at": {"type": "date"}
            }
        }
    }
    result = es("PUT", INDEX_NAME, mapping)
    if result:
        print(f"[OK] Index '{INDEX_NAME}' cree")
    else:
        print("[OK] Index existe deja")

def get_new(db_path, last_id):
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    try:
        c.execute("SELECT rowid,* FROM predictions WHERE rowid > ? ORDER BY rowid ASC LIMIT 500", (last_id,))
    except sqlite3.OperationalError:
        c.execute("SELECT *,rowid FROM predictions WHERE rowid > ? ORDER BY rowid ASC LIMIT 500", (last_id,))
    rows = [dict(r) for r in c.fetchall()]
    conn.close()
    return rows

def bulk_index(predictions):
    if not predictions:
        return 0
    lines = []
    for p in predictions:
        rid = p.get("rowid", p.get("alert_id", 0))
        lines.append(json.dumps({"index": {"_index": INDEX_NAME, "_id": str(rid)}}))
        lines.append(json.dumps({
            "alert_id": p.get("alert_id", rid),
            "timestamp": p.get("timestamp", datetime.utcnow().isoformat()),
            "rule_id": p.get("rule_id", 0),
            "rule_description": p.get("rule_description", ""),
            "src_ip": p.get("src_ip", "0.0.0.0"),
            "probability": float(p.get("probability", 0.0)),
            "prediction": int(p.get("prediction", 0)),
            "synced_at": datetime.utcnow().isoformat() + "Z"
        }))
    body = "\n".join(lines) + "\n"
    req = Request(f"{OPENSEARCH_URL}/_bulk", data=body.encode(), method="POST")
    req.add_header("Content-Type", "application/x-ndjson")
    try:
        with urlopen(req) as r:
            result = json.loads(r.read())
            errors = sum(1 for i in result.get("items", [])
                        if "error" in i.get("index", {}))
            if errors:
                print(f"[WARN] {errors} erreurs d'indexation")
            return len(predictions)
    except HTTPError as e:
        print(f"[ERR] Bulk: {e.read().decode()[:200]}")
        return 0

def main():
    print(f"Sync SQLite -> OpenSearch (index: {INDEX_NAME})")
    ensure_index()
    last_id = 0
    result = es("POST", f"{INDEX_NAME}/_search",
                {"size": 1, "sort": [{"alert_id": {"order": "desc"}}], "_source": False})
    if result and result["hits"]["hits"]:
        last_id = int(result["hits"]["hits"][0]["_id"])
        print(f"[INFO] Dernier ID indexe: {last_id}")
    while True:
        try:
            rows = get_new(SQLITE_DB, last_id)
            if rows:
                synced = bulk_index(rows)
                last_id = max(r.get("rowid", 0) for r in rows)
                print(f"[{datetime.utcnow().strftime('%H:%M:%S')}] Sync {synced} (last: {last_id})")
            else:
                print(f"[{datetime.utcnow().strftime('%H:%M:%S')}] Rien de nouveau")
        except Exception as e:
            print(f"[ERR] {e}")
        time.sleep(POLL_INTERVAL)

if __name__ == "__main__":
    main()
PYEOF

sudo chmod 755 /opt/wazuh-ml/sync_opensearch.py
echo "[OK] Script installe"

# 2. Service systemd
echo "[2/4] Installation du service systemd..."
sudo tee /etc/systemd/system/wazuh-ml-sync.service > /dev/null << 'SERVICEEOF'
[Unit]
Description=Sync ML predictions to OpenSearch for Wazuh dashboard
After=network.target wazuh-api.service

[Service]
Type=simple
User=root
WorkingDirectory=/opt/wazuh-ml
ExecStart=/usr/bin/python3 /opt/wazuh-ml/sync_opensearch.py
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
SERVICEEOF

sudo systemctl daemon-reload
sudo systemctl enable wazuh-ml-sync
echo "[OK] Service installe"

# 3. Creer l'index pattern dans Kibana
echo "[3/4] Creation de l index pattern dans Kibana..."
curl -s -u admin:'YFrxHHO*3QK2y6l6JceItXgQ8zO6Jbwn' \
  -X POST "http://127.0.0.1:9200/_plugins/kibana/api/saved_objects/index-pattern" \
  -H "Content-Type: application/json" \
  -H "osd-xsrf: true" \
  -d '{"attributes":{"title":"wazuh-ml-predictions","timeFieldName":"timestamp"}}' 2>/dev/null | python3 -c "
import sys,json
d=json.load(sys.stdin)
print(f'[OK] Index pattern cree: {d.get(\"id\",\"deja existant\")}')" 2>/dev/null || echo "[OK] Index pattern deja existant"

# 4. Demarrer le service
echo "[4/4] Demarrage du service de synchronisation..."
sudo systemctl start wazuh-ml-sync
sleep 2
systemctl is-active wazuh-ml-sync > /dev/null && echo "[OK] Sync en cours" || echo "[WARN] Verifier les logs: journalctl -u wazuh-ml-sync"

echo ""
echo "=== Integration terminee ==="
echo ""
echo "Prochaines etapes dans le dashboard Wazuh:"
echo "  1. Ouvre https://192.168.30.3:443"
echo "  2. Stack Management > Index Patterns > wazuh-ml-predictions"
echo "  3. Cree des visualisations (voir docs/INTEGRATION_DASHBOARD.md)"
echo ""
echo "Ou depuis le terminal :"
echo "  curl -s http://127.0.0.1:9200/wazuh-ml-predictions/_count | python3 -m json.tool"
