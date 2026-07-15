#!/usr/bin/env python3
"""
03_feature_engineering.py — Transforme les alertes labellisees en vecteurs de features.
Lit dataset_labeled.csv, produit features/feature_matrix.csv.
"""

import argparse
import csv
import json
import os
import sys
from collections import Counter, defaultdict
from datetime import datetime, timezone

PROJECT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULT_INPUT = os.path.join(PROJECT_DIR, "data", "labeled", "dataset_v2.csv")
DEFAULT_OUTPUT = os.path.join(PROJECT_DIR, "features", "feature_matrix.csv")


def parse_ts(s):
    """Parse ISO timestamp to datetime."""
    s = s.strip().replace("Z", "+00:00")
    return datetime.fromisoformat(s)


def load_dataset(path):
    """Charge le CSV labellise."""
    rows = []
    with open(path) as f:
        for row in csv.DictReader(f):
            rows.append(row)
    return rows


def build_features(rows):
    """Construit les vecteurs de features pour chaque alerte."""
    print(f"  Building features for {len(rows)} alerts...")

    # Pre-parse timestamps
    for r in rows:
        r["_ts"] = parse_ts(r["timestamp"])
        r["_ts_num"] = r["_ts"].timestamp()

    # Sort by time for window features
    rows.sort(key=lambda r: r["_ts_num"])

    # Find top rule IDs for one-hot encoding
    rule_counts = Counter(r["rule_id"] for r in rows)
    top_rules = {rid for rid, _ in rule_counts.most_common(30)}

    # Feature extraction
    feature_rows = []
    for i, r in enumerate(rows):
        ts = r["_ts"]
        ts_num = r["_ts_num"]

        # ── Temporal features ──
        hour = ts.hour
        dayofweek = ts.weekday()
        is_night = 1 if hour < 6 or hour > 22 else 0

        # ── Rule features ──
        rule_id = r["rule_id"]
        rule_level = int(r["rule_level"])

        # ── Source IP features ──
        srcip = r.get("srcip", "")
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

        # ── Frequency features (look back) ──
        lookback_1min = ts_num - 60
        lookback_5min = ts_num - 300
        lookback_15min = ts_num - 900

        count_rule_1min = 0
        count_rule_5min = 0
        count_rule_15min = 0
        count_srcip_1min = 0
        count_srcip_5min = 0
        count_srcip_15min = 0
        last_same_rule = ts_num  # interval since last same rule

        # Scan backwards from current alert
        for j in range(i - 1, -1, -1):
            prev = rows[j]
            prev_ts = prev["_ts_num"]
            diff = ts_num - prev_ts

            if diff > 900:
                break  # Too far back, stop

            same_rule = prev["rule_id"] == rule_id
            same_srcip = prev.get("srcip", "") == srcip

            if diff <= 60:
                if same_rule:
                    count_rule_1min += 1
                if same_srcip:
                    count_srcip_1min += 1
            if diff <= 300:
                if same_rule:
                    count_rule_5min += 1
                if same_srcip:
                    count_srcip_5min += 1
            if diff <= 900:
                if same_rule:
                    count_rule_15min += 1
                if same_srcip:
                    count_srcip_15min += 1

            if same_rule and last_same_rule == ts_num:
                last_same_rule = diff

        # ── One-hot top rules ──
        rule_ohe = {}
        for tr in top_rules:
            rule_ohe[f"rule_{tr}"] = 1 if rule_id == tr else 0

        # ── Agent features ──
        agent = r.get("agent", "")

        # ── Assemble feature vector ──
        feat = {
            "timestamp": r["timestamp"],
            "hour": hour,
            "dayofweek": dayofweek,
            "is_night": is_night,
            "rule_level": rule_level,
            "srcip_type_docker": 1 if srcip_type == "docker" else 0,
            "srcip_type_lan": 1 if srcip_type == "lan" else 0,
            "srcip_type_external": 1 if srcip_type == "external" else 0,
            "srcip_type_unknown": 1 if srcip_type == "unknown" else 0,
            "count_rule_1min": min(count_rule_1min, 999),
            "count_rule_5min": min(count_rule_5min, 999),
            "count_rule_15min": min(count_rule_15min, 999),
            "count_srcip_1min": min(count_srcip_1min, 999),
            "count_srcip_5min": min(count_srcip_5min, 999),
            "count_srcip_15min": min(count_srcip_15min, 999),
            "interval_since_last": min(last_same_rule, 999),
            "agent_CibleWazuh": 1 if agent == "CibleWazuh" else 0,
            "agent_vbox": 1 if agent == "vbox" else 0,
            "agent_UbuntuWazuh": 1 if agent == "UbuntuWazuh" else 0,
            # Label
            "label": int(r["label"]),
        }
        feat.update(rule_ohe)
        feature_rows.append(feat)

    return feature_rows, list(top_rules)


def save_features(feature_rows, output_path):
    """Sauvegarde la matrice de features en CSV."""
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=feature_rows[0].keys())
        writer.writeheader()
        writer.writerows(feature_rows)
    print(f"  Saved: {output_path}")
    print(f"  Size: {os.path.getsize(output_path) / 1024 / 1024:.1f} MB")
    print(f"  Features: {len(feature_rows[0].keys())} columns")
    return feature_rows


def main():
    parser = argparse.ArgumentParser(description="Feature engineering for Wazuh alerts")
    parser.add_argument("--input", default=DEFAULT_INPUT, help="Input labeled CSV")
    parser.add_argument("--output", default=DEFAULT_OUTPUT, help="Output feature CSV")
    args = parser.parse_args()

    print("=" * 60)
    print(" FEATURE ENGINEERING — 03_feature_engineering.py")
    print("=" * 60)
    print(f"  Input:  {args.input}")
    print(f"  Output: {args.output}")
    print("")

    # Load
    print("--- Loading dataset ---")
    rows = load_dataset(args.input)
    print(f"  {len(rows)} rows loaded")

    # Build features
    print("\n--- Building features ---")
    features, top_rules = build_features(rows)

    # Stats
    tp = sum(1 for f in features if f["label"] == 1)
    fp = sum(1 for f in features if f["label"] == 0)
    print(f"\n  TP: {tp} ({tp / len(features) * 100:.1f}%)")
    print(f"  FP: {fp} ({fp / len(features) * 100:.1f}%)")
    print(f"  Top rule IDs encoded: {len(top_rules)}")

    # Save
    print("\n--- Saving ---")
    save_features(features, args.output)

    print("\n" + "=" * 60)
    print(" Done. Next: python3 pipeline/04_train_model.py")
    print("=" * 60)


if __name__ == "__main__":
    main()
