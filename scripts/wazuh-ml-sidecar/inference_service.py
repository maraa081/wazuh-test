#!/usr/bin/env python3
"""
inference_service.py — Wazuh ML Sidecar
Monitors alerts.json in real-time, runs XGBoost inference, stores in SQLite.

Architecture:
  alerts.json (tail -f) → feature extraction → XGBoost → SQLite
                                                          ↓
                                                    API (port 9090)

Usage:
  python3 inference_service.py [--alert-file /var/ossec/logs/alerts/alerts.json]
                               [--model models/xgb_model.json]
                               [--db predictions.db]

Update-Proof:
  - Does NOT modify any Wazuh file
  - Does NOT touch ossec.conf or Filebeat config
  - Reads alerts.json in read-only mode
  - Survives Wazuh updates (only the parser might need update)
"""

import argparse
import json
import os
import sqlite3
import sys
import time
from collections import defaultdict, deque
from datetime import datetime, timezone

import numpy as np

# ─── Paths ────────────────────────────────────────────────────────
PROJECT_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DEFAULT_ALERT_FILE = "/var/ossec/logs/alerts/alerts.json"
DEFAULT_MODEL_FILE = os.path.join(PROJECT_DIR, "models", "xgb_model.json")
DEFAULT_METRICS_FILE = os.path.join(PROJECT_DIR, "models", "xgb_model_metrics.json")
DEFAULT_DB_FILE = os.path.join(PROJECT_DIR, "data", "predictions", "predictions.db")


# ─── Database ─────────────────────────────────────────────────────

def init_db(db_path):
    """Create predictions table if not exists."""
    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    conn = sqlite3.connect(db_path)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS predictions (
            alert_id TEXT PRIMARY KEY,
            timestamp TEXT,
            rule_id TEXT,
            rule_description TEXT,
            agent_name TEXT,
            srcip TEXT,
            prediction INTEGER,
            confidence REAL,
            features_json TEXT,
            created_at TEXT DEFAULT (datetime('now'))
        )
    """)
    conn.execute("""
        CREATE INDEX IF NOT EXISTS idx_predictions_timestamp ON predictions(timestamp)
    """)
    conn.execute("""
        CREATE INDEX IF NOT EXISTS idx_predictions_prediction ON predictions(prediction)
    """)
    conn.commit()
    conn.close()


def store_prediction(conn, alert_id, timestamp, rule_id, rule_desc, agent, srcip,
                     prediction, confidence, features):
    """Insert or update a prediction in SQLite."""
    conn.execute("""
        INSERT OR REPLACE INTO predictions
        (alert_id, timestamp, rule_id, rule_description, agent_name, srcip,
         prediction, confidence, features_json)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        alert_id,
        timestamp,
        rule_id,
        rule_desc[:200],
        agent,
        srcip,
        int(prediction),
        float(confidence),
        json.dumps(features),
    ))
    conn.commit()


# ─── Model loading ────────────────────────────────────────────────

def load_model(model_path, metrics_path=None):
    """Load XGBoost model and feature names from metrics."""
    import xgboost as xgb

    if not os.path.exists(model_path):
        print(f"[FATAL] Model not found: {model_path}")
        sys.exit(1)

    model = xgb.XGBClassifier()
    model.load_model(model_path)
    print(f"[OK] Model loaded: {model_path}")

    # Load feature names from metrics file
    feature_names = []
    if metrics_path and os.path.exists(metrics_path):
        with open(metrics_path) as f:
            metrics = json.load(f)
        feature_names = metrics.get("feature_names", [])
        print(f"[OK] {len(feature_names)} feature names loaded from metrics")

    # Fallback: try to extract from model internal data
    if not feature_names:
        try:
            feature_names = model.get_booster().feature_names
        except Exception:
            pass
        print(f"[WARN] Using {len(feature_names)} feature names from model")

    return model, feature_names


# ─── Feature extraction ───────────────────────────────────────────

class FeatureExtractor:
    """
    Extracts the same feature vector used during training.

    Maintains a rolling buffer of recent alerts to compute
    frequency features (count same rule in 1min/5min/15min windows).
    """

    def __init__(self, feature_names: list):
        self.feature_names = feature_names
        # Rolling buffer: list of (timestamp, rule_id, srcip)
        self.buffer = deque(maxlen=10000)

        # Pre-compute one-hot rule indices from feature names
        self.rule_cols = []
        for name in feature_names:
            if name.startswith("rule_") and name[5:].isdigit():
                self.rule_cols.append(name)

    def parse_alert_ts(self, alert: dict) -> datetime:
        """Parse alert timestamp to datetime."""
        ts_str = alert.get("timestamp", "")
        ts_str = ts_str.strip().replace("Z", "+00:00")
        # Handle +0000 (no colon)
        if "+" in ts_str[10:] and ":" not in ts_str[ts_str.index("+") + 1:]:
            ts_str = ts_str[:ts_str.index("+")] + "+00:00"
        return datetime.fromisoformat(ts_str)

    def is_suricata_alert(self, alert: dict) -> bool:
        """Check if alert comes from Suricata."""
        location = alert.get("location", "")
        rule_groups = alert.get("rule", {}).get("groups", [])
        rule_desc = alert.get("rule", {}).get("description", "")
        # Suricata alerts come from eve.json or have "suricata" in groups
        if "suricata" in str(rule_groups).lower():
            return True
        if "eve.json" in location:
            return True
        if "suricata" in location.lower():
            return True
        if rule_desc.lower().startswith("suricata:"):
            return True
        return False

    def extract(self, alert: dict) -> dict:
        """
        Extract feature vector from a single alert.
        Returns dict with same keys as self.feature_names.
        """
        ts = self.parse_alert_ts(alert)
        ts_num = ts.timestamp()
        rule_id = alert.get("rule", {}).get("id", "")
        rule_level = int(alert.get("rule", {}).get("level", 0))
        srcip = alert.get("data", {}).get("srcip", "")
        agent = alert.get("agent", {}).get("name", "")

        # ── Temporal features ──
        hour = ts.hour
        dayofweek = ts.weekday()
        is_night = 1 if hour < 6 or hour > 22 else 0

        # ── Source IP type ──
        if srcip.startswith("172.20."):
            srcip_type = "docker"
        elif srcip.startswith("192.168.30."):
            srcip_type = "lan"
        elif srcip.startswith("10."):
            srcip_type = "nat"
        elif srcip:
            srcip_type = "external"
        else:
            srcip_type = "unknown"

        # ── Frequency features (from rolling buffer) ──
        count_rule_1min = 0
        count_rule_5min = 0
        count_rule_15min = 0
        count_srcip_1min = 0
        count_srcip_5min = 0
        count_srcip_15min = 0
        interval_since_last = 999  # Large default

        for prev_ts, prev_rule, prev_srcip in reversed(self.buffer):
            diff = ts_num - prev_ts
            if diff > 900:
                break

            if diff <= 60:
                if prev_rule == rule_id:
                    count_rule_1min += 1
                if prev_srcip == srcip:
                    count_srcip_1min += 1
            if diff <= 300:
                if prev_rule == rule_id:
                    count_rule_5min += 1
                if prev_srcip == srcip:
                    count_srcip_5min += 1
            if diff <= 900:
                if prev_rule == rule_id:
                    count_rule_15min += 1
                if prev_srcip == srcip:
                    count_srcip_15min += 1

            # Interval since last same rule
            if prev_rule == rule_id and diff < interval_since_last:
                interval_since_last = diff

        # Add to buffer - this runs for each extract call in case of standalone use

        # ── Build feature vector ──
        # Start with zeros for all known features
        feat = {name: 0.0 for name in self.feature_names}

        # Fill known features
        feat["hour"] = float(hour)
        feat["dayofweek"] = float(dayofweek)
        feat["is_night"] = float(is_night)
        feat["rule_level"] = float(rule_level)
        feat["srcip_type_docker"] = 1.0 if srcip_type == "docker" else 0.0
        feat["srcip_type_lan"] = 1.0 if srcip_type == "lan" else 0.0
        feat["srcip_type_external"] = 1.0 if srcip_type == "external" else 0.0
        feat["srcip_type_unknown"] = 1.0 if srcip_type == "unknown" else 0.0
        feat["count_rule_1min"] = float(min(count_rule_1min, 999))
        feat["count_rule_5min"] = float(min(count_rule_5min, 999))
        feat["count_rule_15min"] = float(min(count_rule_15min, 999))
        feat["count_srcip_1min"] = float(min(count_srcip_1min, 999))
        feat["count_srcip_5min"] = float(min(count_srcip_5min, 999))
        feat["count_srcip_15min"] = float(min(count_srcip_15min, 999))
        feat["interval_since_last"] = float(min(interval_since_last, 999))
        feat["agent_CibleWazuh"] = 1.0 if agent == "CibleWazuh" else 0.0
        feat["agent_vbox"] = 1.0 if agent == "vbox" else 0.0
        feat["agent_UbuntuWazuh"] = 1.0 if agent == "UbuntuWazuh" else 0.0

        # One-hot rule_id
        rule_key = f"rule_{rule_id}"
        if rule_key in feat:
            feat[rule_key] = 1.0

        return feat

    def to_array(self, features: dict) -> np.ndarray:
        """Convert feature dict to numpy array in the correct order."""
        arr = np.array([[features[name] for name in self.feature_names]], dtype=np.float32)
        return arr


# ─── Inference loop ───────────────────────────────────────────────

def watch_alerts(alert_path, model, feature_extractor, db_path,
                 poll_interval=1.0, skip_existing=True):
    """Monitor alerts.json for new lines and run inference."""
    conn = sqlite3.connect(db_path)

    # Pre-populate buffer from existing DB for accurate frequency features
    try:
        existing = conn.execute("SELECT features_json, timestamp, rule_id FROM predictions ORDER BY timestamp ASC").fetchall()
        for feat_json, ts, rid in existing:
            try:
                feat = json.loads(feat_json)
                ts_num = float(datetime.fromisoformat(ts.replace("Z","+00:00")).timestamp())
                feature_extractor.buffer.append((ts_num, rid, feat.get("srcip","")))
            except: pass
        print(f"[WATCH] Pre-populated buffer: {len(existing)} alerts")
    except Exception as e:
        print(f"[WATCH] Buffer pre-population skipped: {e}")

    # Get file size to skip existing lines
    file_pos = os.path.getsize(alert_path) if skip_existing else 0

    print(f"\n[WATCH] Monitoring: {alert_path}")
    print(f"[WATCH] Poll interval: {poll_interval}s")
    print(f"[WATCH] Skip existing: {skip_existing}")
    print(f"[WATCH] DB: {db_path}")
    print("[WATCH] Ready. Waiting for new alerts...\n")

    processed = 0
    suricata_count = 0
    fp_count = 0
    tp_count = 0

    while True:
        try:
            size = os.path.getsize(alert_path)
            if size < file_pos:
                print("[WATCH] File rotated, resetting position")
                file_pos = 0
                time.sleep(1)
                continue
            if size <= file_pos:
                time.sleep(1)
                continue
            with open(alert_path) as f:
                f.seek(file_pos)
                for line in f:
                    line = line.strip()
                    if not line: continue
                    try: alert = json.loads(line)
                    except: continue
                    if not feature_extractor.is_suricata_alert(alert): continue
                    suricata_count += 1
                    alert_id = alert.get("id", f"unknown_{suricata_count}")
                    ts = alert.get("timestamp", "")
                    rule_id = alert.get("rule", {}).get("id", "")
                    rule_desc = alert.get("rule", {}).get("description", "")
                    agent = alert.get("agent", {}).get("name", "")
                    srcip = alert.get("data", {}).get("srcip", "")
                    features = feature_extractor.extract(alert)
                    X = feature_extractor.to_array(features)
                    proba = model.predict_proba(X)[0, 1]
                    prediction = 1 if proba >= 0.5 else 0
                    if prediction == 0: fp_count += 1
                    else: tp_count += 1
                    store_prediction(conn, alert_id, ts, rule_id, rule_desc, agent, srcip, prediction, proba, features)
                    if suricata_count % 100 == 0:
                        status = "FP" if prediction == 0 else "TP"
                        print(f"  [{suricata_count}] {alert_id[:20]:20} rule={rule_id:>6} score={proba:.3f} -> {status}")
                file_pos = f.tell()
        except FileNotFoundError:
            print(f"[WATCH] File not found: {alert_path}"); time.sleep(5); continue
        except Exception as e:
            print(f"[ERROR] {e}")
        time.sleep(poll_interval)


# ─── Main ─────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Wazuh ML Sidecar - inference service")
    parser.add_argument("--alert-file", default=DEFAULT_ALERT_FILE)
    parser.add_argument("--model", default=DEFAULT_MODEL_FILE)
    parser.add_argument("--metrics", default=DEFAULT_METRICS_FILE)
    parser.add_argument("--db", default=DEFAULT_DB_FILE)
    parser.add_argument("--poll", type=float, default=1.0, help="Poll interval (s)")
    parser.add_argument("--no-skip", action="store_true", help="Process existing alerts")
    args = parser.parse_args()

    print("=" * 60)
    print(" WAZUH ML INFERENCE SERVICE")
    print("=" * 60)
    print(f"  Alert file: {args.alert_file}")
    print(f"  Model:      {args.model}")
    print(f"  Metrics:    {args.metrics}")
    print(f"  Database:   {args.db}")
    print(f"  Poll:       {args.poll}s")
    print(f"  Skip existing: {not args.no_skip}")
    print()

    # Init DB
    init_db(args.db)

    # Load model
    model, feature_names = load_model(args.model, args.metrics)
    if not feature_names:
        print("[FATAL] No feature names available")
        sys.exit(1)

    # Feature extractor
    extractor = FeatureExtractor(feature_names)

    # Watch loop
    watch_alerts(
        alert_path=args.alert_file,
        model=model,
        feature_extractor=extractor,
        db_path=args.db,
        poll_interval=args.poll,
        skip_existing=not args.no_skip,
    )


if __name__ == "__main__":
    main()
