#!/usr/bin/env python3
"""
01_collect_alerts.py — Collect alerts from Wazuh API and save as JSONL.

Usage:
  python3 01_collect_alerts.py
  python3 01_collect_alerts.py --days 7
  python3 01_collect_alerts.py --output /tmp/my_alerts.jsonl

Environment variables:
  WAZUH_API_USER  (default: wazuh-wui)
  WAZUH_API_PASS  (required)
  WAZUH_API_URL   (default: https://192.168.30.3:55000)
"""

import argparse
import json
import os
import sys
import time
from datetime import datetime, timezone

import urllib.request
import urllib.error
import base64

# ─── Config ───────────────────────────────────────────────────────
API_USER = os.environ.get("WAZUH_API_USER", "wazuh-wui")
API_PASS = os.environ.get("WAZUH_API_PASS", "")
API_URL = os.environ.get("WAZUH_API_URL", "https://192.168.30.3:55000")

PROJECT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW_DIR = os.path.join(PROJECT_DIR, "data", "raw_alerts")

# ─── Auth ─────────────────────────────────────────────────────────

def get_token() -> str:
    """Authenticate and return a Bearer token."""
    if not API_PASS:
        print("ERROR: WAZUH_API_PASS environment variable not set")
        sys.exit(1)

    auth_str = f"{API_USER}:{API_PASS}"
    b64_auth = base64.b64encode(auth_str.encode()).decode()

    req = urllib.request.Request(
        f"{API_URL}/security/user/authenticate",
        method="GET",
        headers={"Authorization": f"Basic {b64_auth}"},
    )
    try:
        ctx = _ssl_ctx()
        with urllib.request.urlopen(req, context=ctx, timeout=15) as resp:
            data = json.loads(resp.read())
            token = data.get("data", {}).get("token", "")
            if not token:
                print(f"ERROR: No token in response: {data}")
                sys.exit(1)
            return token
    except Exception as e:
        print(f"ERROR: Auth failed: {e}")
        sys.exit(1)


def _ssl_ctx():
    """Return an SSL context that accepts self-signed certs."""
    import ssl
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    return ctx


# ─── API calls ────────────────────────────────────────────────────

def api_get(token: str, path: str, params: dict = None) -> dict:
    """Make a GET request to the Wazuh API."""
    url = f"{API_URL}{path}"
    if params:
        qs = "&".join(f"{k}={urllib.parse.quote_plus(str(v))}" for k, v in params.items())
        url = f"{url}?{qs}"

    req = urllib.request.Request(
        url,
        method="GET",
        headers={"Authorization": f"Bearer {token}"},
    )
    try:
        ctx = _ssl_ctx()
        with urllib.request.urlopen(req, context=ctx, timeout=30) as resp:
            return json.loads(resp.read())
    except urllib.error.HTTPError as e:
        print(f"  HTTP {e.code}: {e.read().decode()[:200]}")
        return {}
    except Exception as e:
        print(f"  Request failed: {e}")
        return {}


def find_alerts_endpoint(token: str) -> str:
    """Try different API endpoints to find alerts."""
    for ep in ["/alerts", "/security/alerts"]:
        resp = api_get(token, ep, {"limit": 1})
        items = resp.get("data", {}).get("affected_items", resp.get("data", []))
        if items or resp.get("error") == 0:
            return ep
    return "/alerts"


def collect_alerts(token: str, endpoint: str, days: int = 1) -> list:
    """Collect all alerts from the last N days."""
    all_alerts = []
    offset = 0
    limit = 500
    total = None

    print(f"  Endpoint: {endpoint}")
    print(f"  Period:   {days} day(s)")
    print(f"  Batch:    {limit} alerts per page")
    print("")

    while True:
        params = {
            "limit": limit,
            "offset": offset,
            "sort": "timestamp",
        }
        # If days limited, filter by time
        if days > 0:
            from datetime import timedelta
            since = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
            params["time"] = f"{since},"

        resp = api_get(token, endpoint, params)
        items = resp.get("data", {}).get("affected_items", resp.get("data", []))
        if total is None:
            total = resp.get("data", {}).get("total_affected_items", 0)
            if total == 0:
                total = len(items)
            print(f"  Total alerts available: {total}")

        if not items:
            break

        all_alerts.extend(items)
        offset += limit

        pct = len(all_alerts) / total * 100 if total > 0 else 0
        print(f"  Collected: {len(all_alerts)}/{total} ({pct:.0f}%)", end="\r")

        if len(items) < limit:
            break

        time.sleep(0.3)  # API rate limiting

    print(f"\n  ✅ Collected {len(all_alerts)} alerts total")
    return all_alerts


# ─── Save ─────────────────────────────────────────────────────────

def save_jsonl(alerts: list, output_path: str):
    """Save alerts as JSONL."""
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, "w") as f:
        for alert in alerts:
            f.write(json.dumps(alert) + "\n")
    size_mb = os.path.getsize(output_path) / (1024 * 1024)
    print(f"  ✅ Saved to: {output_path}")
    print(f"     Size: {size_mb:.1f} MB")


# ─── Main ─────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Collect Wazuh alerts for ML dataset")
    parser.add_argument("--days", type=int, default=1, help="Days to look back (0=all)")
    parser.add_argument("--output", type=str, default="", help="Output JSONL path")
    args = parser.parse_args()

    # Generate output path
    if args.output:
        output_path = args.output
    else:
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        os.makedirs(RAW_DIR, exist_ok=True)
        output_path = os.path.join(RAW_DIR, f"alerts_{ts}.jsonl")

    print("═══════════════════════════════════════════════════════════")
    print(" WAZUH ALERT COLLECTOR — 01_collect_alerts.py")
    print("═══════════════════════════════════════════════════════════")
    print(f"  API:   {API_URL}")
    print(f"  User:  {API_USER}")
    print(f"  Days:  {args.days}")
    print("")

    # Auth
    print("--- Authenticating ---")
    token = get_token()
    print(f"  ✅ Token obtained ({len(token)} chars)")

    # Find endpoint
    print("\n--- Finding alerts endpoint ---")
    endpoint = find_alerts_endpoint(token)
    print(f"  ✅ Using: {endpoint}")

    # Collect
    print("\n--- Collecting alerts ---")
    alerts = collect_alerts(token, endpoint, args.days)

    if not alerts:
        print("  ⚠️  No alerts collected. Nothing to save.")
        sys.exit(0)

    # Save
    print("\n--- Saving ---")
    save_jsonl(alerts, output_path)

    # Stats
    scan_alerts = [a for a in alerts if "scan" in a.get("rule", {}).get("description", "").lower() or "NMAP" in a.get("rule", {}).get("description", "")]
    print(f"\n  Scan alerts: {len(scan_alerts)} / {len(alerts)} total")

    # Show sample
    if scan_alerts:
        print("\n--- Sample scan alert ---")
        s = scan_alerts[0]
        r = s.get("rule", {})
        print(f"  Timestamp:   {s.get('timestamp', '?')}")
        print(f"  Rule:        [{r.get('level', '?')}] {r.get('description', '?')}")
        print(f"  Agent:       {s.get('agent', {}).get('name', '?')}")
        print(f"  Groups:      {r.get('groups', [])}")

    print("\n═══════════════════════════════════════════════════════════")
    print(f" Done. Next: python3 pipeline/02_label_dataset.py")
    print("═══════════════════════════════════════════════════════════")


if __name__ == "__main__":
    main()
