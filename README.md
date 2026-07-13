# Wazuh AI Filter 🔧

Filtre intelligent pour alertes Wazuh basé sur le Machine Learning.  
Distingue les **vrais positifs** (attaques réelles) des **faux positifs** (trafic normal qui déclenche une alerte).

## Problème

Wazuh détecte des milliers d'alertes par jour. L'analyste passe 80% de son temps à trier les faux positifs.

## Solution

Un modèle XGBoost entraîné **sur votre propre réseau**, qui apprend les motifs de vos attaques réelles et filtre le bruit automatiquement.

```mermaid
graph TD
    A[Trafic rÃ©seau] --> B[Suricata IDS]
    B --> C[eve.json]
    C --> D[Wazuh Agent]
    D --> E[Wazuh Manager]
    E --> F[API / alerts.json]
    F --> G[Pipeline ML]
    G --> H{XGBoost}
    H -->|Score > 0.5| I[ALERTE - Vrai positif]
    H -->|Score < 0.5| J[FILTRE - Faux positif]
```

## Architecture du labo

```mermaid
graph LR
    subgraph "RÃ©seau BridgÃ© 192.168.30.0/24"
        K[ParrotOS\nAttaquant]
        C[Ubuntu 22.04\nCible + Suricata]
        M[Ubuntu 24.04\nWazuh Manager]
    end
    
    subgraph "Docker 172.20.0.0/16"
        B1[agent-001\nbenign_ssh]
        B2[agent-031\nbenign_dns]
        B3[agent-061\nbenign_http]
        B4[agent-091\nbenign_ping]
        A1[agent-100\nmalicious]
    end

    K -->|nmap -sS| C
    C -->|eve.json| D[Wazuh Agent]
    D --> M
    M -->|API| P[Pipeline ML]
    B1 -->|SSH| M
    B2 -->|DNS| C
    B3 -->|HTTP| C
    B4 -->|PING| C
    A1 -->|nmap + hydra| C
```

## Pipeline

```mermaid
graph LR
    C[Campagne Docker] --> CSV[attack_campaigns.csv]
    CSV --> L[02_label_dataset.py]
    A1[01_collect_alerts.py] --> L
    L --> D[Dataset labellisÃ©]
    D --> F[03_feature_engineering.py]
    F --> M[04_train_model.py]
    M --> E[05_evaluate_model.py]
    E --> R[ModÃ¨le final]\nreports/
```

## Installation rapide

```bash
git clone https://github.com/maraa081/wazuh-test.git
cd wazuh-test
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Structure

```
wazuh-test/
├── config/                    # Configuration (Wazuh, features, model)
├── pipeline/                  # 5 Ã©tapes du pipeline ML
│   ├── 01_collect_alerts.py   # Collecte des alertes Wazuh
│   ├── 02_label_dataset.py    # Labelisation via campagnes
│   ├── 03_feature_engineering.py # Calcul des features
│   ├── 04_train_model.py      # EntraÃ®nement XGBoost
│   └── 05_evaluate_model.py   # Ã‰valuation + SHAP
├── data/                      # DonnÃ©es (gitignored)
│   ├── attack_windows/        # CSV des campagnes d'attaque
│   ├── raw_alerts/            # Alertes brutes JSONL
│   └── labeled/               # Datasets labellisÃ©s
├── service/                   # Service d'infÃ©rence
├── scripts/                   # Scripts utilitaires
│   ├── docker-dataset/        # GÃ©nÃ©ration de dataset massif
│   └── campaign-runner.sh     # GÃ©nÃ©ration d'attaques
├── docs/                      # Documentation
├── features/                  # Matrices de features (gitignored)
├── models/                    # ModÃ¨les entraÃ®nÃ©s (gitignored)
└── reports/                   # Rapports d'Ã©valuation (gitignored)
```

## Licence

MIT
