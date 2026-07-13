# Dataset AI Filter — Plan de collecte

## Architecture de collecte

```
ParrotOS / Kali                Cible Ubuntu 22.04              Wazuh Manager
  │                                │                              │
  ├── nmap scan ─────────────────► │                              │
  ├── hydra bruteforce ──────────► │                              │
  ├── hping3 flood ──────────────► │                              │
  ├── trafic bénin (SSH, DNS……)─► │                              │
  │                                ▼                              │
  │                           Suricata 8.0.6                     │
  │                           ├── eve.json ──────────────────►    │
  │                           │   (alertes scan)                  │
  │                           │                                   │
  │                           Wazuh agent                        │
  │                           ├── lit eve.json                   │
  │                           └── envoie au manager ──────────►   │
  │                                                              │
  │◄────────────────────────────────────────────────────── API ──│
  │                                port 55000                    │
  │                                curl -u user:pass              │
  │                                /security/alerts               │
```

## Logs à collecter

### Classe 1 — Nmap scans (TP)
| Alerte | Règle Suricata | Commentaire |
|--------|---------------|-------------|
| SYNC scan -sS | 1000001 | Scan furtif standard |
| OS fingerprint | 1000002 | Détection d'OS Nmap |
| -sV version | 1000006 | Scan de services |
| -sT connect | 1000003 | Scan connect complet |
| ping sweep | 1000005 | Scan ICMP |
| Port scan (module) | portscan | Détection générique module |

### Classe 2 — SSH bruteforce (TP)
| Alerte | Règle Wazuh/Suricata | Commentaire |
|--------|---------------------|-------------|
| sshd auth failed | 5760 | Échec d'authentification unique |
| SSH bruteforce | 5710 | Multiples échecs en rafale |
| SSH scan attack | 5712 | Scan d'utilisateurs SSH |

### Classe 3 — Trafic bénin (FP)
| Type | Source | Commentaire |
|------|--------|-------------|
| SSH sudo | logs sudo/PAM | Administrateur normal |
| DNS | Suricata/réseau | Trafic DNS légitime |
| Trafic web | Apache/nginx | Requêtes HTTP normales |
| Mises à jour apt | Système | Trafic package manager |

## Format d'enregistrement

Chaque alerte collectée via l'API Wazuh contient :

```json
{
  "timestamp": "2026-07-13T19:48:16.000+0000",
  "rule": {
    "id": "1000001",
    "level": 3,
    "description": "Suricata: Alert - ET SCAN NMAP SYN scan -sS",
    "groups": ["suricata", "scan"]
  },
  "agent": {
    "id": "002",
    "name": "CibleWazuh"
  },
  "data": {
    "srcip": "192.168.30.9",
    "srcport": "60682",
    "dstuser": null
  },
  "location": "suricata"
}
```

## Features pour le modèle

1. **rule.id** — type d'alerte
2. **rule.level** — sévérité (3-15)
3. **data.srcip** — IP source
4. **data.srcport** — port source
5. **Fréquence même rule en 1min/5min/15min** — détection de rafale
6. **Fréquence même srcip en 1min/5min/15min** — attaquant unique
7. **Heure du jour** — pattern temporel
8. **Intervalle depuis dernière alerte** — régularité outillage

## Labeling

- **TP (True Positive)** = alerte dans une fenêtre d'attaque (campagne Kali/ParrotOS)
- **FP (False Positive)** = alerte hors fenêtre (trafic normal)

Les fenêtres d'attaque sont documentées dans `data/attack_windows/attack_campaigns.csv`
au format :
```
attack_id,start_utc,end_utc,attack_type,target_ip,target_port,tool
NMAP001,2026-07-13T19:48:00Z,2026-07-13T19:49:00Z,nmap_syn_scan,192.168.30.10,22,hydra
```

## Pipeline final

```
01_collect_alerts.py    → interroge API Wazuh, stocke JSONL
02_label_dataset.py     → croise alertes + attack_campaigns.csv → CSV labellisé
03_feature_engineering.py → transforme en features numériques
04_train_model.py       → entraîne XGBoost
05_evaluate_model.py    → métriques, SHAP, matrice confusion
```

## Vérification du pipeline complet

Pour confirmer que tout remonte bien :

```bash
# Sur la cible — Suricata voit les alertes ?
sudo tail -3 /var/log/suricata/fast.log

# Sur le Manager — Wazuh reçoit les alertes ?
sudo grep "suricata" /var/ossec/logs/alerts/alerts.json | tail -3

# Via l'API — accessible pour le collecteur ?
curl -u 'wazuh-wui:<password>' -k \
  'https://localhost:55000/security/alerts?limit=5' \
  | python3 -m json.tool | grep -E "description|srcip"
```
