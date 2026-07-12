# Stage 1: alert collection from the Wazuh API.
#
# This script connects to the Wazuh manager API and fetches alerts that were
# generated within a configurable time window. It handles pagination internally
# so you get all matching alerts, not just the first page.
#
# The raw alerts are saved as JSONL (one JSON object per line) to make appending
# new data trivial and avoid the hassle of merging JSON arrays.
#
# Usage:
#   python pipeline/01_collect_alerts.py
#
# Environment variables:
#   WAZUH_API_USER      - Wazuh API username
#   WAZUH_API_PASSWORD  - Wazuh API password
#   WAZUH_API_URL       - optional override of the API URL from config.yaml
#
# Config keys used:
#   wazuh.api.*         - API connection settings
#   collection.*        - output format and storage paths

import sys
import os

# Ensure the project root is on the path so we can import the shared library.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def main():
    print("01_collect_alerts.py - not yet implemented")
    print("This script will:")
    print("  1. Load config/config.yaml")
    print("  2. Connect to the Wazuh API with credentials from env vars")
    print("  3. Fetch alerts from the configured lookback period")
    print("  4. Save them as JSONL in data/raw_alerts/")


if __name__ == "__main__":
    main()
