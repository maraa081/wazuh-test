#!/usr/bin/env python3
"""
01_collect_alerts.py — Collect alerts from local alerts.json and save as JSONL.
Usage:
  python3 01_collect_alerts.py
  python3 01_collect_alerts.py --output /tmp/dataset.jsonl
"""

import argparse
import json
import os
import sys
from datetime import datetime, timezone

ALERTS_FILE = "/var/ossec/logs/alerts/alerts.json"
PROJECT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW_DIR = os.path.join(PROJECT_DIR, "data", "raw_alerts")


def collect_local_alerts(alerts_path: str, days: int = 1) -> list:
    """Read alerts from local alerts.json, optionally filtered by age."""
    if not os.path.exists(alerts_path):
        print(f"ERROR: File not found: {alerts_path}")
        sys.exit(1)

    total_lines = sum(1 for _ in open(alerts_path))
    print(f"  File:      {alerts_path}")
    print(f"  Total:     {total_lines} lines")

    # If days <= 0, collect all
    if days <= 0:
        alerts = []
        with open(alerts_path) as f:
            for line in f:
                line = line.strip()
                if line:
                    try:
                        alerts.append(json.loads(line))
                    except json.JSONDecodeError:
                        pass
        print(f"  Collected: {len(alerts)} alerts (all time)")
        return alerts

    # Filter by date
    from datetime import timedelta
    cutoff = (datetime.now().astimezone() - timedelta(days=days)).timestamp()

    alerts = []
    skipped = 0
    with open(alerts_path) as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                d = json.loads(line)
                ts = d.get("timestamp", "")
                if ts:
                    # Parse ISO timestamp
                    try:
                        dt = datetime.fromisoformat(ts.replace("Z", "+00:00"))
                        if dt.timestamp() < cutoff:
                            skipped += 1
                            continue
                    except ValueError:
                        pass
                alerts.append(d)
            except json.JSONDecodeError:
                skipped += 1

    print(f"  Filtered:  {len(alerts)} alerts (last {days} day(s))")
    print(f"  Skipped:   {skipped} (out of range or invalid)")
    return alerts


def save_jsonl(alerts: list, output_path: str):
    """Save alerts as JSONL."""
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, "w") as f:
        for alert in alerts:
            f.write(json.dumps(alert) + "\n")
    size_mb = os.path.getsize(output_path) / (1024 * 1024)
    print(f"\n  ✅ Saved: {output_path} ({size_mb:.1f} MB, {len(alerts)} alerts)")


def main():
    parser = argparse.ArgumentParser(description="Collect Wazuh alerts for ML dataset")
    parser.add_argument("--days", type=int, default=1, help="Days to look back (0=all)")
    parser.add_argument("--output", type=str, default="", help="Output JSONL path")
    parser.add_argument("--input", type=str, default=ALERTS_FILE, help="Input alerts.json path")
    args = parser.parse_args()

    # Output path
    if args.output:
        output_path = args.output
    else:
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        os.makedirs(RAW_DIR, exist_ok=True)
        output_path = os.path.join(RAW_DIR, f"alerts_{ts}.jsonl")

    print("═══════════════════════════════════════════════════════════")
    print(" WAZUH ALERT COLLECTOR — 01_collect_alerts.py")
    print("═══════════════════════════════════════════════════════════")
    print(f"  Input:  {args.input}")
    print(f"  Output: {output_path}")
    print(f"  Days:   {args.days}")
    print("")

    # Collect
    print("--- Collecting ---")
    alerts = collect_local_alerts(args.input, args.days)

    if not alerts:
        print("  ⚠️  No alerts collected.")
        sys.exit(0)

    # Save
    print("--- Saving ---")
    save_jsonl(alerts, output_path)

    # Stats
    scan_alerts = [
        a for a in alerts
        if "scan" in a.get("rule", {}).get("description", "").lower()
        or "NMAP" in a.get("rule", {}).get("description", "")
    ]
    ssh_alerts = [
        a for a in alerts
        if "ssh" in a.get("rule", {}).get("description", "").lower()
        or "brute" in a.get("rule", {}).get("description", "").lower()
    ]
    print(f"\n  Stats:")
    print(f"    Total:    {len(alerts)}")
    print(f"    Scans:    {len(scan_alerts)}")
    print(f"    SSH:      {len(ssh_alerts)}")
    print(f"    Others:   {len(alerts) - len(scan_alerts) - len(ssh_alerts)}")

    # Sample
    if scan_alerts:
        print("\n--- Sample scan alert ---")
        s = scan_alerts[0]
        print(f"  {json.dumps(s, indent=2)[:300]}")

    print("\n═══════════════════════════════════════════════════════════")
    print(" Done. Next: python3 pipeline/02_label_dataset.py")
    print("═══════════════════════════════════════════════════════════")


if __name__ == "__main__":
    main()
