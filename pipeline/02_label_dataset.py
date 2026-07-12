# Stage 2: label raw alerts using attack time windows.
#
# This script reads the attack windows CSV file (filled in by you after each
# Kali campaign) and the raw alerts collected in stage 1. For each alert, it
# checks whether the alert's timestamp falls within any attack window and
# whether the alert's rule.groups match the attack type in that window.
#
# Alerts inside an attack window with a matching rule type are labeled "1"
# (true positive). All others are labeled "0" (false positive).
#
# The attack mapping file (config/attack_mapping.yaml) defines which Wazuh
# rule.groups correspond to each attack_type value. This mapping is what
# connects your manual campaign notes to the automated labeling logic.
#
# Usage:
#   python pipeline/02_label_dataset.py
#
# Inputs:
#   data/raw_alerts/*.jsonl         - raw alerts from stage 1
#   data/attack_windows/*.csv       - your campaign time windows
#   config/attack_mapping.yaml      - attack type to rule groups mapping
#
# Output:
#   data/labeled/labeled_dataset.csv - alerts with a "label" column added

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def main():
    print("02_label_dataset.py - not yet implemented")
    print("This script will:")
    print("  1. Load raw alerts from data/raw_alerts/")
    print("  2. Load attack windows from data/attack_windows/")
    print("  3. Load the attack type mapping from config/attack_mapping.yaml")
    print("  4. For each alert: check if it falls in an attack window with")
    print("     matching rule type, then assign label 1 or 0")
    print("  5. Save the labeled dataset to data/labeled/labeled_dataset.csv")


if __name__ == "__main__":
    main()
