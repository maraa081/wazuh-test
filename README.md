# Wazuh AI Filter

Machine learning layer for Wazuh SIEM that distinguishes true positives from
false positives in Wazuh-generated alerts. The model is trained on your own
network data by running controlled attacks from Kali Linux and labeling the
resulting Wazuh alerts automatically.

## Why this exists

Wazuh is great at detecting security events, but it has no native intelligence
to separate real attacks from benign traffic that happens to match a rule.
This project adds that layer externally, without modifying Wazuh itself, so
upgrades and standard operations stay clean.

The core idea is simple: you run attacks in your lab, note the time windows,
and the pipeline labels every alert inside those windows as a true positive.
Everything outside (normal traffic flagged by Wazuh) is a candidate false
positive. Over time, you build a dataset specific to your own network, not
some generic benchmark that has nothing to do with your traffic patterns.

## Project structure

```
wazuh-test/
├── config/
│   ├── config.yaml             # all settings: API, feature engineering, model
│   └── attack_mapping.yaml     # attack types to Wazuh rule.groups mapping
│
├── pipeline/
│   ├── 01_collect_alerts.py    # fetches alerts from Wazuh API, stores raw
│   ├── 02_label_dataset.py     # labels alerts using attack time windows
│   ├── 03_feature_engineering.py # transforms raw alerts into feature vectors
│   ├── 04_train_model.py       # trains XGBoost classifier on features
│   └── 05_evaluate_model.py    # eval metrics, SHAP, confusion matrix
│
├── service/
│   ├── inference_service.py    # polling loop: API -> feature -> score -> store
│   ├── db_schema.py            # SQLite schema for prediction results
│   └── api.py                  # FastAPI read-only endpoint for querying results
│
├── wazuh_ai_filter/            # shared library (parsers, feature transformers)
│   └── __init__.py
│
├── data/
│   ├── attack_windows/         # user-provided CSV of attack time windows
│   ├── raw_alerts/             # collected alert JSONL files (gitignored)
│   ├── labeled/                # labeled dataset CSV (gitignored)
│   └── predictions/            # SQLite inference DB (gitignored)
│
├── features/                   # cached feature matrices (gitignored)
├── models/                     # trained model artifacts (gitignored)
├── reports/                    # evaluation reports (gitignored)
├── notebooks/                  # exploratory analysis notebooks
├── scratch/                    # throwaway experiments (gitignored)
│
├── config.yaml                 # DEPRECATED: use config/config.yaml instead
├── requirements.txt
├── .gitignore
└── README.md
```

## Architecture summary

```
Kali attacks (controlled)  +  Normal traffic
           |                         |
           v                         v
      Wazuh Manager (alerts via API) |
           |                         |
           v                         v
    01_collect_alerts.py  ----raw JSONL---->  data/raw_alerts/
           |
           |  + data/attack_windows/campaigns.csv
           v
    02_label_dataset.py  ----labeled CSV--->  data/labeled/
           |
           v
    03_feature_engineering.py  ----features--->  features/
           |
           v
    04_train_model.py  ----model--->  models/
           |
           v
    05_evaluate_model.py  ----report--->  reports/
           |
           v
    service/inference_service.py  (polling loop)
           |
           v
    SQLite predictions.db  <--->  FastAPI query API (port 9090)
```

## Getting started

### Prerequisites

- Python 3.10 or later
- A running Wazuh manager with API access (typically port 55000)
- A Kali Linux VM (or equivalent) to generate controlled attacks
- At least one Wazuh agent sending events to the manager

### Installation

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### Environment variables

The following must be set before running any script. Nothing is stored in
config files or committed to the repo.

| Variable | Required | Purpose |
|----------|----------|---------|
| `WAZUH_API_USER` | yes | Wazuh API username |
| `WAZUH_API_PASSWORD` | yes | Wazuh API password |
| `WAZUH_API_URL` | no | Override Wazuh API URL from config.yaml |

### Running the full pipeline

1. **Run a controlled attack from Kali.** Note the start and end timestamps
   (UTC), the type of attack, the target IP, and the tool used.

2. **Log the attack window** in `data/attack_windows/attack_campaigns.csv`:

   ```csv
   attack_id,start_utc,end_utc,attack_type,target_ip,target_port,tool,notes
   CAM001,2026-07-12T14:32:00Z,2026-07-12T14:41:00Z,ssh_bruteforce,192.168.1.100,22,hydra,hydra -l root -P rockyou.txt ssh://192.168.1.100
   ```

3. **Collect alerts from Wazuh:**

   ```bash
   python pipeline/01_collect_alerts.py
   ```

4. **Label the dataset:**

   ```bash
   python pipeline/02_label_dataset.py
   ```

5. **Extract features and train:**

   ```bash
   python pipeline/03_feature_engineering.py
   python pipeline/04_train_model.py
   ```

6. **Evaluate:**

   ```bash
   python pipeline/05_evaluate_model.py
   ```

7. **Start the inference service** (polling mode):

   ```bash
   python service/inference_service.py
   ```

8. **Query results** via the API:

   ```bash
   curl http://127.0.0.1:9090/predictions?since=2026-07-12T14:00:00Z
   ```

### Re-running after a new campaign

Just add new rows to `attack_campaigns.csv`, run the collection again (or
combine with existing data), then re-label, re-featurize, and re-train.
The pipeline is idempotent for the labeling step: existing rows with matching
alert_id and campaign_id are updated in place.

## Evaluation priority

The model is tuned for recall on true positives, not raw accuracy. In a SIEM
context, missing a real attack (false negative) is worse than investigating a
false positive. The evaluation report shows:

- Precision, recall, F1-score for both classes
- F2-score (weights recall x2 over precision)
- Confusion matrix
- ROC AUC and PR AUC
- SHAP summary plot (feature importance with direction)
- Threshold tuning curve

## Wrapper design

Everything runs outside Wazuh. The inference service:
- polls the Wazuh API for new alerts
- extracts the same features used during training
- scores each alert with the trained model
- stores the result (alert ID, TP probability, classification, timestamp) in
  a local SQLite database
- exposes a read-only HTTP API for querying predictions

No Wazuh configuration files are modified. No custom rules, decoders, or
integrations are added to the Wazuh manager. This makes the system robust
to Wazuh version upgrades: only the API contract matters.

## License

MIT
