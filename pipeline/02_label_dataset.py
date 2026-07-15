#!/usr/bin/env python3
"""
02_label_dataset.py — Labellise les alertes collectees avec les fenetres CSV de campagne.

Usage:
  python3 02_label_dataset.py \\
    --alerts /tmp/alerts_20260713_193152.jsonl \\
    --campaign /tmp/CAMP_DOCKER_20260713_204420.csv \\
    --output /tmp/dataset_labeled.csv
"""

import argparse
import csv
import json
import os
import sys
from datetime import datetime, timezone


def parse_iso(ts_str: str) -> datetime:
    """Parse ISO timestamp with timezone handling."""
    ts_str = ts_str.strip()
    if ts_str.endswith("Z"):
        ts_str = ts_str[:-1] + "+00:00"
    # Gestion du format +0200
    if "+" in ts_str[10:] and ":" not in ts_str[ts_str.index("+") :]:
        sign = "+" if "+" in ts_str[10:] else "-"
        parts = ts_str.split(sign)
        if len(parts) == 2 and len(parts[1]) == 4:
            h, m = parts[1][:2], parts[1][2:]
            ts_str = parts[0] + sign + h + ":" + m
    return datetime.fromisoformat(ts_str)


def load_campaigns(campaign_path: str) -> list:
    """Charge les fenetres de campagne depuis un CSV."""
    campaigns = []
    with open(campaign_path) as f:
        reader = csv.DictReader(f)
        for row in reader:
            campaigns.append({
                "id": row["attack_id"].strip(),
                "start": parse_iso(row["start_utc"]),
                "end": parse_iso(row["end_utc"]),
                "type": row["attack_type"].strip(),
                "count": int(row.get("container_count", 0)),
                "subnet": row.get("target_subnet", "").strip(),
            })
    return campaigns


def is_in_campaign(ts: datetime, campaigns: list) -> tuple:
    """Verifie si un timestamp tombe dans une fenetre de campagne.
    Returns (campaign_type, campaign_id) or (None, None)."""
    ts_ts = ts.timestamp()
    for c in campaigns:
        if c["start"].timestamp() <= ts_ts <= c["end"].timestamp():
            return (c["type"], c["id"])
    return (None, None)


SCAN_RULE_KEYWORDS = ["scan", "nmap", "portscan", "syn", "fingerprint"]


def is_alert_scan(alert: dict) -> bool:
    """Check if an alert is scan-related by rule description."""
    desc = alert.get("rule", {}).get("description", "")
    desc_lower = desc.lower()
    return any(kw in desc_lower for kw in SCAN_RULE_KEYWORDS)


def extract_srcip(alert: dict) -> str:
    """Extrait l'IP source de l'alerte."""
    for field in ["srcip", "src_ip", "data.srcip"]:
        parts = field.split(".")
        val = alert
        for p in parts:
            if isinstance(val, dict):
                val = val.get(p, "")
            else:
                break
        if val:
            return str(val)
    return ""


def extract_features(alert: dict) -> dict:
    """Extrait les champs de features de l'alerte."""
    r = alert.get("rule", {})
    a = alert.get("agent", {})
    d = alert.get("data", {})
    return {
        "timestamp": alert.get("timestamp", ""),
        "rule_id": r.get("id", ""),
        "rule_level": r.get("level", 0),
        "rule_groups": json.dumps(r.get("groups", [])),
        "rule_description": r.get("description", ""),
        "agent_id": a.get("id", ""),
        "agent_name": a.get("name", ""),
        "srcip": d.get("srcip", ""),
        "dstuser": d.get("dstuser", ""),
        "location": alert.get("location", ""),
        "full_log": (alert.get("full_log", "") or "")[:200],
    }


def label_dataset(alerts_path: str, campaigns: list, output_path: str):
    """Labellise toutes les alertes et ecrit le CSV labellise."""
    print("--- Labeling ---")

    labeled = []
    total = 0
    for line in open(alerts_path):
        line = line.strip()
        if not line:
            continue
        try:
            alert = json.loads(line)
        except json.JSONDecodeError:
            continue
        total += 1

        # Parse le timestamp
        try:
            ts_str = alert.get("timestamp", "")
            ts = parse_iso(ts_str)
        except (ValueError, TypeError):
            continue

        # Check campaign
        camp_type, camp_id = is_in_campaign(ts, campaigns)
        is_scan = is_alert_scan(alert)

        # Logique de labellisation :
        # - Si l'alerte est dans une campagne malicious_* → label = 1 (vrai positif)
        # - Si l'alerte est dans une campagne benign_* → label = 0 (bruit de fond benign)
        # - Si l'alerte est hors de toute fenetre → label = 0
        if camp_id:
            if camp_type.startswith("malicious_"):
                label = 1  # True Positive: alert during malicious campaign
            else:
                label = 0  # Benign background traffic
        else:
            label = 0  # Outside campaign = normal traffic

        features = extract_features(alert)
        features["label"] = label
        features["campaign_id"] = camp_id or ""
        features["campaign_type"] = camp_type or ""
        features["is_scan"] = 1 if is_scan else 0
        labeled.append(features)

    # Write CSV
    with open(output_path, "w", newline="") as f:
        if labeled:
            writer = csv.DictWriter(f, fieldnames=labeled[0].keys())
            writer.writeheader()
            writer.writerows(labeled)
        else:
            f.write("label\n")

    # Stats
    tp = sum(1 for l in labeled if l["label"] == 1)
    fp = sum(1 for l in labeled if l["label"] == 0)
    total_labeled = len(labeled)

    print(f"\n  Dataset:       {total_labeled} rows / {total} total alerts")
    print(f"  True Positive: {tp} ({tp/total_labeled*100:.1f}%)" if total_labeled > 0 else "  True Positive: 0")
    print(f"  False Positive:{fp} ({fp/total_labeled*100:.1f}%)" if total_labeled > 0 else "  False Positive: 0")
    print(f"  Output:        {output_path}")
    size_mb = os.path.getsize(output_path) / (1024 * 1024)
    print(f"  Size:          {size_mb:.1f} MB")

    # Sample
    if labeled:
        print("\n--- Sample TP ---")
        for l in labeled:
            if l["label"] == 1:
                print(f"  [{l['timestamp']}] Rule {l['rule_id']}: {l['rule_description'][:60]}")
                print(f"  SrcIP: {l['srcip']} | Agent: {l['agent_name']}")
                break

        print("\n--- Sample FP ---")
        for l in labeled:
            if l["label"] == 0:
                print(f"  [{l['timestamp']}] Rule {l['rule_id']}: {l['rule_description'][:60]}")
                print(f"  SrcIP: {l['srcip']} | Agent: {l['agent_name']}")
                break

    return labeled


def main():
    parser = argparse.ArgumentParser(description="Label Wazuh alerts using campaign CSV")
    parser.add_argument("--alerts", default="/tmp/alerts_20260713_193152.jsonl",
                        help="Path to alerts JSONL file")
    parser.add_argument("--campaign", default="/tmp/CAMP_DOCKER_20260713_204420.csv",
                        help="Path to campaign CSV file")
    parser.add_argument("--output", default="",
                        help="Output labeled CSV path")
    args = parser.parse_args()

    output = args.output or args.alerts.replace(".jsonl", "_labeled.csv")

    print("=========================================")
    print(" DATASET LABELER — 02_label_dataset.py")
    print("=========================================")
    print(f"  Alerts:   {args.alerts}")
    print(f"  Campaign: {args.campaign}")
    print(f"  Output:   {output}")
    print("")

    # Load campaigns
    print("--- Loading campaigns ---")
    campaigns = load_campaigns(args.campaign)
    print(f"  {len(campaigns)} campaign window(s)")
    for c in campaigns:
        print(f"    {c['id']}: {c['type']} ({c['start']} → {c['end']})")

    # Label
    label_dataset(args.alerts, campaigns, output)

    print("\n=========================================")
    print(" Done. Next: python3 pipeline/03_feature_engineering.py")
    print("=========================================")


if __name__ == "__main__":
    main()
