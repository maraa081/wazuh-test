# Handover - Wazuh AI Filter Lab

> Passe de Veille a un autre agent OpenClaw
> Date: 2026-07-14

---

## 1. Infrastructure

### Machines

| Machine | IP | OS | User | Acces |
|---------|----|----|------|-------|
| **Manager** | 192.168.30.3 | Ubuntu 24.04 | vboxuser | Local (la ou tu tournes) |
| **Target** | 192.168.30.10 | Ubuntu 22.04 | vboxuser | `ssh target` (cle ED25519, NOPASSWD sudo) |
| **ParrotOS** | 192.168.30.9 | Parrot OS | live | `ssh -i ~/.ssh/id_ed25519_parrot live@192.168.30.9` |
| **Windows** | 192.168.30.1 | Windows 11 | - | Dashboard Wazuh |

### Connexions SSH
- Manager -> Target : cle `~/.ssh/id_ed25519` (alias `target` dans `~/.ssh/config`)
- Manager -> ParrotOS : cle `~/.ssh/id_ed25519_parrot` (user `live`)
- Attention : ParrotOS peut devenir injoignable (VM eteinte) - verifier avec `ping 192.168.30.9`

---

## 2. Services (Manager)

| Service | Role | Statut | Commande |
|---------|------|--------|----------|
| `wazuh-inference` | Inference ML XGBoost en temps reel | active | `systemctl is-active wazuh-inference` |
| `wazuh-api` | API REST :9090 | active | `systemctl is-active wazuh-api` |
| `wazuh-ml-sync` | Sync predictions SQLite -> OpenSearch (toutes les 30s) | active | `systemctl is-active wazuh-ml-sync` |
| `openclaw-gateway` | Gateway OpenClaw (user service) | active | `systemctl --user is-active openclaw-gateway` |

### Ports importants
- ML API : `127.0.0.1:9090`
- OpenSearch : `127.0.0.1:9200` (HTTPS, auth admin/YFrxHHO*3QK2y6l6JceItXgQ8zO6Jbwn)
- Wazuh Dashboard : `https://192.168.30.3:443`
- OpenClaw Control UI : `http://192.168.30.3:18789`
- Wazuh API : `127.0.0.1:55000`

---

## 3. Ce qui a ete fait pendant la session

### 3.1 Infrastructure
- [x] UFW configure sur Manager (11 regles restrictives)
- [x] UFW configure sur Target (SSH Manager + Windows)
- [x] Cle SSH Manager -> Target deployee
- [x] Cle SSH Manager -> ParrotOS generee et deployee
- [x] SSH active sur ParrotOS
- [x] hping3 installe sur Target

### 3.2 ML Pipeline
- [x] Service wazuh-inference installe et configure (`--model` + `--metrics` args)
- [x] Service wazuh-api installe et configure
- [x] Bug `len(None)` dans inference_service.py corrige
- [x] Pipeline ML 5 etapes operationnel (scripts dans `pipeline/`)
- [x] Modele XGBoost entraine : Recall 96.3%, F2 91.6%, ROC AUC 99.9%
- [x] Modele deployee dans `/opt/wazuh-ml/xgb_model.json`
- [x] 64 295 predictions generees en live

### 3.3 Integration Dashboard
- [x] Index OpenSearch `wazuh-ml-predictions` cree
- [x] Index pattern `wazuh-ml-predictions` cree (timeField: timestamp)
- [x] Service wazuh-ml-sync installe (sync SQLite -> OpenSearch toutes les 30s)
- [x] Visualisation pie chart TP/FP creee
- [x] Visualisation line chart cumul creee
- [x] Dashboard `ML Predictions Dashboard` cree

### 3.4 Attaques depuis ParrotOS
- [x] Script `attack-from-parrot.sh` corrige (IP 192.168.30.9, user live)
- [x] 4 attaques lancees avec succes
- [x] UFW temporaire ajoute/retire pendant les attaques

---

## 4. Emplacement des fichiers importants

### Scripts
| Fichier | Role |
|---------|------|
| `~/wazuh-test/pipeline/01_collect_alerts.py` | Collecte des alertes |
| `~/wazuh-test/pipeline/02_label_dataset.py` | Labellisation TP/FP |
| `~/wazuh-test/pipeline/03_feature_engineering.py` | Extraction de features |
| `~/wazuh-test/pipeline/04_train_model.py` | Entrainement XGBoost |
| `~/wazuh-test/pipeline/05_evaluate_model.py` | Evaluation SHAP |
| `~/wazuh-test/run_pipeline.py` | Orchestrateur du pipeline complet |
| `~/wazuh-test/scripts/lab-healthcheck.sh` | Healthcheck du labo |
| `~/wazuh-test/scripts/attack-from-parrot.sh` | Lance une attaque depuis ParrotOS |
| `~/wazuh-test/scripts/sync_opensearch.sh` | Installe le sync OpenSearch |
| `~/wazuh-test/fix/fix.sh` | Fix services ML + UFW |
| `~/wazuh-test/fix/fix2.sh` | Fix final inference + regles UFW |

### Donnees
| Fichier | Role |
|---------|------|
| `/var/ossec/logs/alerts/alerts.json` | Alertes Wazuh (57k+ lignes) |
| `/tmp/predictions.db` | Base SQLite des predictions (64k lignes) |
| `/tmp/pipeline_alerts2.jsonl` | Dernier export d'alertes |
| `/tmp/pipeline_labeled2.csv` | Dataset labellise (107 TP / 3000 FP) |
| `/tmp/pipeline_sample_features.csv` | Feature matrix (36 features, 3107 lignes) |
| `/tmp/pipeline_model.json` | Modele XGBoost entraine |
| `/tmp/pipeline_model_metrics.json` | Metriques du modele |
| `~/wazuh-test/data/labeled/campaign_merged.csv` | 35 fenetres de campagne (Docker + ParrotOS) |
| `~/wazuh-test/data/labeled/campaign_parrot.csv` | Fenetres ParrotOS uniquement |
| `~/wazuh-test/data/raw_alerts/` | Archives d'alertes JSONL |

### Modeles
| Fichier | Role |
|---------|------|
| `/opt/wazuh-ml/xgb_model.json` | Modele XGBoost actif (utilise par inference) |
| `/opt/wazuh-ml/xgb_model_metrics.json` | Metriques + feature names |
| `/opt/wazuh-ml/inference_service.py` | Service d'inference en continu |
| `/opt/wazuh-ml/api_service.py` | API REST :9090 |
| `/opt/wazuh-ml/sync_opensearch.py` | Sync SQLite -> OpenSearch |

### Configuration
| Fichier | Role |
|---------|------|
| `~/.openclaw/openclaw.json` | Config Gateway OpenClaw |
| `~/.ssh/config` | Alias SSH (target) |
| `~/.ssh/id_ed25519` | Cle Manager -> Target |
| `~/.ssh/id_ed25519_parrot` | Cle Manager -> ParrotOS |
| `/etc/systemd/system/wazuh-inference.service` | Service systemd inference |
| `/etc/systemd/system/wazuh-api.service` | Service systemd API |
| `/etc/systemd/system/wazuh-ml-sync.service` | Service systemd sync |
| `/etc/sudoers.d/vboxuser` | NOPASSWD sudo (deja corrige) |

### Documentation
| Fichier | Role |
|---------|------|
| `~/wazuh-test/docs/PRESENTATION_LABO.html` | Rapport complet avec graphiques (454 KB) |
| `~/wazuh-test/docs/PRESENTATION_LABO.md` | Version Markdown (lisible sur GitHub) |
| `~/wazuh-test/docs/INTEGRATION_DASHBOARD.md` | Guide d'integration dashboard |
| `~/wazuh-test/SETUP.md` | Blueprint d'installation |
| `~/wazuh-test/PROGRES.md` | Suivi de progression |
| `~/wazuh-test/docs/JOURNAL_DE_BORD.md` | Journal de bord du projet |

---

## 5. Commandes essentielles

```bash
# Healthcheck complet
bash ~/wazuh-test/scripts/lab-healthcheck.sh

# Lancer une attaque (120s)
bash ~/wazuh-test/scripts/attack-from-parrot.sh 120

# Stats ML en direct
curl http://127.0.0.1:9090/stats

# Pipeline ML complet
python3 ~/wazuh-test/run_pipeline.py --all

# Voir les logs inference
sudo journalctl -u wazuh-inference -n 20 --no-pager

# Dashboard ML
# https://192.168.30.3/app/dashboards -> ML Predictions Dashboard

# Verifier les services
systemctl is-active wazuh-inference wazuh-api wazuh-ml-sync
```

---

## 6. Bugs et points d'attention

1. **ParrotOS parfois hors ligne** - Verifier avec `ping 192.168.30.9` avant d'attaquer
2. **Token GitHub invalide** - Le token `ghp_F...9UE` ne fonctionne plus, generer un nouveau sur github.com/settings/tokens
3. **Feature engineering lent** - Le script `03_feature_engineering.py` a une complexite O(n^2) - limiter a <5000 lignes pour etre rapide
4. **Modele predit 0 (FP)** - Le modele classe tout en FP car entraine avec seulement 107 TP. Lancer plus d'attaques pour enrichir le dataset
5. **Dashboard HTML non rendu sur GitHub** - Activer GitHub Pages (Settings > Pages > branch main / folder docs)
6. **Le OpenClaw Gateway est un user service** - Les commandes systemctl normales ne le voient pas, utiliser `systemctl --user`

---

## 7. Liens GitHub

- Repository : https://github.com/maraa081/wazuh-test
- Rapport HTML : https://github.com/maraa081/wazuh-test/blob/main/docs/PRESENTATION_LABO.html
- Rapport Markdown : https://github.com/maraa081/wazuh-test/blob/main/docs/PRESENTATION_LABO.md
- Setup : https://github.com/maraa081/wazuh-test/blob/main/SETUP.md
