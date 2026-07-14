# Wazuh AI Filter — Présentation Labo

> Architecture complète : Attaque → Détection → ML → Dashboard

---

## 🧭 Schéma d'architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         Manager (192.168.30.3)                             │
│                                                                             │
│  ┌─────────────────┐   ┌──────────────────────┐   ┌───────────────────┐    │
│  │  Wazuh Manager   │   │  alerts.json         │   │  ML Inference     │    │
│  │  (all-in-one)    │──▶│  (57000+ alertes)    │──▶│  XGBoost → TP/FP  │    │
│  └─────────────────┘   └──────────────────────┘   └────────┬──────────┘    │
│                                        ▲                     │               │
│                                        │                     ▼               │
│  ┌─────────────────┐                  │            ┌───────────────────┐    │
│  │  Sync OpenSearch │◄─────────────────┼────────────│ predictions.db   │    │
│  │  (30s interval)  │                 │            │  (64000+ lignes)  │    │
│  └────────┬────────┘                   │            └───────────────────┘    │
│           │                            │                                     │
│           ▼                            │               ┌─────────────────┐  │
│  ┌─────────────────┐                  │               │  ML API :9090   │  │
│  │  OpenSearch     │                  │               └─────────────────┘  │
│  │  index: ml-preds │                 │                                     │
│  └────────┬────────┘                   │                                     │
│           │                            │  SSH (clé ED25519)                  │
│           ▼                            │                                     │
│  ┌─────────────────┐                  │                                     │
│  │  Dashboard      │                  │                                     │
│  │  https://:443   │                  │                                     │
│  └─────────────────┘                  │                                     │
└──────────────────────────────────────┼──────────────────────────────────────┘
                                       │
               ┌───────────────────────┼──────────────────────────────────────┐
               │       Target (192.168.30.10)                                 │
               │                       │                                      │
               │  ┌─────────────────┐  │      ┌───────────────────────────┐  │
               │  │  Suricata IDS   │◄─┼──────│  ParrotOS (192.168.30.9)  │  │
               │  │  (af-packet)    │  │      │                           │  │
               │  └────────┬────────┘  │      │  nmap, hydra, hping3      │  │
               │           │           │      │  ping flood, OS scan      │  │
               │           ▼           │      └───────────────────────────┘  │
               │  ┌─────────────────┐  │                                      │
               │  │  Wazuh Agent    │  │                                      │
               │  │  → Manager:1514 │  │                                      │
               │  └─────────────────┘  │                                      │
               └──────────────────────┼──────────────────────────────────────┘
```

---

## 📊 Flux de données

| Étape | Description | Où |
|-------|-------------|----|
| **① Attaque** | ParrotOS envoie nmap, hydra, hping3, ping flood | `192.168.30.9 → 192.168.30.10` |
| **② Détection** | Suricata capture via af-packet, génère alertes | `/var/log/suricata/eve.json` |
| **③ Remontée** | Wazuh Agent envoie les alertes au Manager | `1514/udp → Manager` |
| **④ Stockage** | Wazuh Manager écrit dans alerts.json | `/var/ossec/logs/alerts/alerts.json` |
| **⑤ Inférence ML** | XGBoost score chaque alerte (TP/FP) | `wazuh-inference.service` |
| **⑥ Stockage** | Prédictions en base SQLite | `/tmp/predictions.db` |
| **⑦ Sync OpenSearch** | Sync toutes les 30s vers Dashboard | `wazuh-ml-sync.service` |
| **⑧ Visualisation** | Pie chart TP/FP + courbe cumulée temps réel | `https://192.168.30.3:443` |

---

## 🎯 Pipeline ML (5 étapes)

### Étape 1 — Collecte des alertes
```bash
python3 pipeline/01_collect_alerts.py --days 1
```
Lit `alerts.json` et extrait au format JSONL (57 000+ lignes).

### Étape 2 — Labellisation TP/FP
```bash
python3 pipeline/02_label_dataset.py --alerts alerts.jsonl --campaign campaign.csv
```
Marque chaque alerte selon les fenêtres de campagne (ParrotOS + Docker).

| Label | Quantité |
|-------|----------|
| ✅ **TP** (attaque détectée) | 107 |
| ⬜ **FP** (bruit de fond) | 3 000 |

### Étape 3 — Feature engineering
```bash
python3 pipeline/03_feature_engineering.py --input dataset_labeled.csv
```
Extrait **36 features** :
- ⏰ Temporelles : `hour`, `dayofweek`, `is_night`
- 📊 Fréquence : `count_rule_15min`, `count_srcip_15min` (les plus importantes)
- 🌐 IP : `srcip_type_lan`, `srcip_type_docker`
- 🎯 One-hot : `rule_86601`, `rule_40704`, etc.

### Étape 4 — Entraînement XGBoost
```bash
python3 pipeline/04_train_model.py --input features.csv
```

| Métrique | Valeur | Objectif |
|----------|--------|----------|
| **Recall** | **96.3%** | ✅ >95% |
| **F2-score** | **91.6%** | ✅ >90% |
| **ROC AUC** | **99.9%** | ✅ >95% |
| **Precision** | 76.5% | 🔶 >80% (à améliorer) |

### Étape 5 — Évaluation SHAP
```bash
python3 pipeline/05_evaluate_model.py --input features.csv --model model.json
```
Analyse SHAP des features les plus importantes :
```
count_srcip_15min   ███████████████████████████████████████ 0.398
count_rule_15min    ███████████████████████████████████████ 0.396
srcip_type_lan      ███ 0.024
```

---

## 🖥️ Services en production

| Service | Rôle | Port | Statut |
|---------|------|------|--------|
| `wazuh-inference` | Inference ML en continu | — | 🟢 actif |
| `wazuh-api` | API REST des prédictions | `:9090` | 🟢 actif |
| `wazuh-ml-sync` | Sync SQLite → OpenSearch | — | 🟢 actif |
| `openclaw-gateway` | Gateway OpenClaw + Telegram | `:18789` | 🟢 actif |
| Wazuh Manager | All-in-one | `:55000` | 🟢 actif |
| OpenSearch | Indexation | `:9200` (HTTPS) | 🟢 actif |

---

## 🔧 Commandes utiles

```bash
# Healthcheck complet du labo
bash ~/wazuh-test/scripts/lab-healthcheck.sh

# Lancer une attaque depuis ParrotOS (120s)
bash ~/wazuh-test/scripts/attack-from-parrot.sh 120

# Pipeline ML complet
python3 ~/wazuh-test/run_pipeline.py --all

# Stats en direct
curl http://127.0.0.1:9090/stats

# Dernières 10 prédictions
curl http://127.0.0.1:9090/predictions/recent?limit=10

# Dashboard Wazuh
# https://192.168.30.3:443

# Dashboard ML
# https://192.168.30.3/app/dashboards → "ML Predictions Dashboard"
```

---

## 🌐 Machines

| Machine | IP | OS | Rôle |
|---------|----|----|------|
| **Manager** | `192.168.30.3` | Ubuntu 24.04 | Wazuh + ML + Gateway OpenClaw |
| **Target** | `192.168.30.10` | Ubuntu 22.04 | Suricata + Wazuh Agent + Docker |
| **ParrotOS** | `192.168.30.9` | Parrot OS | Machine d'attaque |
| **Windows** | `192.168.30.1` | Windows 11 | Admin / Dashboard |

---

## 🔐 Sécurité

- **UFW Manager** : 11 règles restrictives — seuls Windows et Target autorisés
- **UFW Target** : SSH uniquement depuis Manager et Windows
- **ParrotOS** : Bloqué de tout par UFW → règles temporaires ajoutées/retirées pendant les attaques
- **SSH** : Clés ED25519 (Manager → Target, Manager → ParrotOS)

---

## 📈 Visualisations Dashboard

Accessible depuis le navigateur Windows : `https://192.168.30.3:443`

| Graphique | Type | Description |
|-----------|------|-------------|
| **TP/FP Répartition** | 🥧 Pie chart | Part des attaques détectées (TP) vs bruit (FP) |
| **Flux continu** | 📈 Line chart | Courbe cumulée des prédictions (toujours montante) |

Données synchronisées toutes les **30 secondes**.
