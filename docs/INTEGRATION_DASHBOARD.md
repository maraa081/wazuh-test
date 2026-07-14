# Integration des predictions ML dans le Dashboard Wazuh

## Objectif

Afficher les predictions ML (score, classe TP/FP) directement dans le dashboard
Wazuh pour voir en temps reel ce que le modele detecte.

## Architecture

```
SQLite (predictions.db)              OpenSearch (port 9200)
       │                                     │
       │ sync_predictions.py                 │ wazuh-ml-predictions index
       │ (lit les predictions et             │
       │  les indexe dans OpenSearch)        │
       ▼                                     ▼
  predictions.db ─────sync─────► OpenSearch ────► Wazuh Dashboard (Kibana)
                                                      │
                                               Index pattern + visualisations
```

## Etape 1 : Creer le script de synchronisation

Script à placer dans `/opt/wazuh-ml/sync_opensearch.py` :

```python
#!/usr/bin/env python3
"""Sync predictions from SQLite to OpenSearch for Wazuh dashboard."""

import json
import sqlite3
import time
from datetime import datetime
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError

# Configuration
SQLITE_DB = "/tmp/predictions.db"
OPENSEARCH_URL = "http://admin:YFrxHHO*3QK2y6l6JceItXgQ8zO6Jbwn@127.0.0.1:9200"
INDEX_NAME = "wazuh-ml-predictions"
POLL_INTERVAL = 30  # secondes

def es_request(method, path, body=None):
    """Execute une requete HTTP vers OpenSearch."""
    url = f"{OPENSEARCH_URL}/{path}"
    data = json.dumps(body).encode() if body else None
    req = Request(url, data=data, method=method)
    req.add_header("Content-Type", "application/json")
    try:
        with urlopen(req) as resp:
            return json.loads(resp.read())
    except HTTPError as e:
        print(f"[WARN] HTTP {e.code}: {e.read().decode()[:200]}")
        return None

def ensure_index():
    """Cree l'index avec mapping si pas existant."""
    mapping = {
        "settings": {"number_of_shards": 1, "number_of_replicas": 0},
        "mappings": {
            "properties": {
                "alert_id": {"type": "keyword"},
                "timestamp": {"type": "date"},
                "rule_id": {"type": "integer"},
                "rule_description": {"type": "text"},
                "src_ip": {"type": "ip"},
                "dst_ip": {"type": "ip"},
                "probability": {"type": "float"},
                "prediction": {"type": "integer"},
                "features_count": {"type": "integer"},
                "synced_at": {"type": "date"}
            }
        }
    }
    result = es_request("PUT", INDEX_NAME, mapping)
    if result:
        print(f"[OK] Index '{INDEX_NAME}' pret")
    else:
        print("[OK] Index existe deja")

def get_new_predictions(db_path, last_id):
    """Recupere les predictions non encore synchronisees."""
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute(
        "SELECT * FROM predictions WHERE rowid > ? ORDER BY rowid ASC LIMIT 500",
        (last_id,)
    )
    rows = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return rows

def bulk_index(predictions):
    """Indexe un lot de predictions dans OpenSearch (bulk API)."""
    if not predictions:
        return 0

    body_lines = []
    for pred in predictions:
        action = {"index": {"_index": INDEX_NAME, "_id": str(pred["alert_id"])}}
        doc = {
            "alert_id": pred["alert_id"],
            "timestamp": pred.get("timestamp", datetime.utcnow().isoformat()),
            "rule_id": pred.get("rule_id", 0),
            "rule_description": pred.get("rule_description", ""),
            "src_ip": pred.get("src_ip", "0.0.0.0"),
            "dst_ip": pred.get("dst_ip", "0.0.0.0"),
            "probability": float(pred.get("probability", 0.0)),
            "prediction": int(pred.get("prediction", 0)),
            "features_count": int(pred.get("features_count", 0)),
            "synced_at": datetime.utcnow().isoformat() + "Z"
        }
        body_lines.append(json.dumps(action))
        body_lines.append(json.dumps(doc))

    body = "\n".join(body_lines) + "\n"
    url = f"{OPENSEARCH_URL}/_bulk"
    req = Request(url, data=body.encode(), method="POST")
    req.add_header("Content-Type", "application/x-ndjson")
    try:
        with urlopen(req) as resp:
            result = json.loads(resp.read())
            if result.get("errors"):
                error_count = sum(1 for item in result["items"]
                                  if "error" in item.get("index", {}))
                print(f"[WARN] {error_count} erreurs d'indexation")
            return len(predictions)
    except HTTPError as e:
        print(f"[ERR] Bulk index failed: {e.read().decode()[:300]}")
        return 0

def main():
    print("=== Synchronisation SQLite -> OpenSearch ===")
    print(f"DB: {SQLITE_DB}")
    print(f"OpenSearch: {OPENSEARCH_URL}")
    print(f"Index: {INDEX_NAME}")
    print(f"Poll interval: {POLL_INTERVAL}s")
    print("")

    # Creer l'index au premier lancement
    ensure_index()

    # Recuperer le dernier ID deja indexe
    last_id = 0
    result = es_request("POST", f"{INDEX_NAME}/_search",
                        {"size": 1, "sort": [{"alert_id": {"order": "desc"}}],
                         "_source": False})
    if result and result["hits"]["hits"]:
        last_id = int(result["hits"]["hits"][0]["_id"])
        print(f"[INFO] Dernier ID deja indexe: {last_id}")

    # Boucle principale
    while True:
        try:
            predictions = get_new_predictions(SQLITE_DB, last_id)
            if predictions:
                synced = bulk_index(predictions)
                last_id = max(p["rowid"] for p in predictions
                            if "rowid" in p) if predictions else last_id
                print(f"[{datetime.utcnow().strftime('%H:%M:%S')}] "
                      f"Sync {synced} predictions (last_id: {last_id})")
            else:
                print(f"[{datetime.utcnow().strftime('%H:%M:%S')}] "
                      f"Rien de nouveau (last_id: {last_id})")
        except Exception as e:
            print(f"[ERR] {e}")

        time.sleep(POLL_INTERVAL)

if __name__ == "__main__":
    main()
```

## Etape 2 : Creer le service systemd

```bash
sudo tee /etc/systemd/system/wazuh-ml-sync.service << 'EOF'
[Unit]
Description=Sync ML predictions to OpenSearch for Wazuh dashboard
After=network.target wazuh-api.service
Wants=wazuh-api.service

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
EOF

sudo systemctl daemon-reload
sudo systemctl enable wazuh-ml-sync
sudo systemctl start wazuh-ml-sync
sudo systemctl status wazuh-ml-sync
```

## Etape 3 : Creer l'index pattern dans Wazuh Dashboard

Depuis le navigateur, ouvrir le dashboard Wazuh :
```
https://192.168.30.3:443
```

Ou via API directement :

```bash
# 1. Creer l'index pattern via API OpenSearch
curl -s -u admin:'YFrxHHO*3QK2y6l6JceItXgQ8zO6Jbwn' \
  -X POST "http://127.0.0.1:9200/_plugins/kibana/api/saved_objects/index-pattern" \
  -H "Content-Type: application/json" \
  -H "osd-xsrf: true" \
  -d '{
    "attributes": {
      "title": "wazuh-ml-predictions",
      "timeFieldName": "timestamp"
    }
  }'
```

## Etape 4 : Creer les visualisations

Depuis le dashboard Wazuh (Stack Management -> Index Patterns) :

1. Aller dans **Stack Management** > **Index Patterns**
2. Cliquer sur **Create index pattern**
3. Entrer `wazuh-ml-predictions` comme nom
4. Selectionner `timestamp` comme champ temps
5. Valider

Puis creer des visualisations :

### Visualisation 1 : Predictions recentes (tableau)
- Aller dans **Visualize** > **Create visualization**
- Choisir **Data Table**
- Source : `wazuh-ml-predictions`
- Metrics : Count
- Buckets : Split rows → Terms → `prediction` (TP=1, FP=0)

### Visualisation 2 : Score au fil du temps
- Choisir **Line chart**
- Source : `wazuh-ml-predictions`
- X-axis : Date histogram (`timestamp`)
- Y-axis : Average (`probability`)

### Visualisation 3 : Dernieres predictions suspectes
- Choisir **Data Table**
- Source : `wazuh-ml-predictions`
- Filter : `prediction: 1` (TP uniquement)
- Rows : Top 10 par `timestamp`

### Visualisation 4 : Dashboard resume
Creer un dashboard avec les 3 visualisations + un compteur de predictions total.

## Etape 5 : Script pour creer les visualisations automatiquement

Script optionnel pour creer les visualisations via API OpenSearch :

```bash
#!/bin/bash
# setup-dashboard.sh — Cree les visualisations Wazuh ML automatiquement
OPENSEARCH="http://admin:YFrxHHO*3QK2y6l6JceItXgQ8zO6Jbwn@127.0.0.1:9200"

echo "=== Configuration du dashboard ML ==="

# 1. Creer l'index pattern
curl -s -X POST "$OPENSEARCH/_plugins/kibana/api/saved_objects/index-pattern" \
  -H "Content-Type: application/json" \
  -H "osd-xsrf: true" \
  -d '{
    "attributes": {
      "title": "wazuh-ml-predictions",
      "timeFieldName": "timestamp"
    }
  }' | python3 -m json.tool

echo ""
echo "=== Fait ==="
echo "Ouvre le dashboard Wazuh : https://192.168.30.3:443"
echo "Va dans Stack Management > Index Patterns"
echo "Verifie que 'wazuh-ml-predictions' est la"
echo "Puis cree les visualisations depuis Visualize > Create"
```

---

## Resumé des commandes

```bash
# 1. Copier le script de sync
sudo cp /home/vboxuser/wazuh-test/docs/INTEGRATION_DASHBOARD.md /opt/wazuh-ml/sync_opensearch.py
# (extraire la partie Python du fichier)

# 2. Creer le service
sudo tee /etc/systemd/system/wazuh-ml-sync.service << 'SERVICEEOF'
[Unit]
Description=Sync ML predictions to OpenSearch
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=/opt/wazuh-ml
ExecStart=/usr/bin/python3 /opt/wazuh-ml/sync_opensearch.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
SERVICEEOF

sudo systemctl daemon-reload
sudo systemctl enable --now wazuh-ml-sync

# 3. Creer l'index pattern dans Kibana
curl -s -u admin:'YFrxHHO*3QK2y6l6JceItXgQ8zO6Jbwn' \
  -X POST "http://127.0.0.1:9200/_plugins/kibana/api/saved_objects/index-pattern" \
  -H "Content-Type: application/json" \
  -H "osd-xsrf: true" \
  -d '{"attributes":{"title":"wazuh-ml-predictions","timeFieldName":"timestamp"}}'

# 4. Verifier
curl -s http://127.0.0.1:9090/stats | python3 -m json.tool
```
