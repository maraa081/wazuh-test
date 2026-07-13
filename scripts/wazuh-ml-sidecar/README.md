# Wazuh ML Sidecar

Micro-service d'inférence ML pour Wazuh. Lit les alertes en temps réel,
exécute le modèle XGBoost, et expose une API REST.

## Architecture

```mermaid
graph LR
    AJ[/var/ossec/logs/alerts/alerts.json] --> IS[inference_service.py]
    IS --> DB[(predictions.db)]
    DB --> API[api_service.py :9090]
    API --> D[Wazuh Dashboard]
```

## Démarrage rapide

```bash
# 1. Installer les dépendances
pip3 install -r requirements.txt

# 2. Lancer l'inférence (surveille alerts.json)
python3 inference_service.py &

# 3. Lancer l'API REST
python3 api_service.py --port 9090 --host 0.0.0.0 &

# 4. Tester
curl http://localhost:9090/health
curl http://localhost:9090/stats
curl http://localhost:9090/predictions?limit=10
```

## Installation permanente (systemd)

```bash
# Service d'inférence
sudo cp wazuh-inference.service /etc/systemd/system/
sudo systemctl enable wazuh-inference
sudo systemctl start wazuh-inference

# Service API
sudo cp wazuh-api.service /etc/systemd/system/
sudo systemctl enable wazuh-api
sudo systemctl start wazuh-api
```

## Endpoints API

| Méthode | Path | Description |
|---------|------|-------------|
| GET | `/health` | Health check |
| GET | `/stats` | Statistiques TP/FP |
| GET | `/predictions` | Liste paginée |
| GET | `/predictions/recent` | 50 dernières |
| GET | `/predictions/{id}` | Par alert_id |
| POST | `/predictions/query` | Par liste d'IDs |
| DELETE | `/predictions/cleanup` | Nettoyage (7j) |

## Update-Proof

Ce service ne modifie **aucun fichier Wazuh**. Il se contente de lire
`alerts.json` en mode read-only et d'écrire dans sa propre base SQLite.
Les mises à jour de Wazuh ne peuvent pas casser ce service.
