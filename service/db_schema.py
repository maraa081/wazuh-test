# SQLite schema definition for prediction storage.
#
# The inference service stores every scored alert in a local SQLite database.
# This module handles table creation and provides helper functions for
# inserting and querying predictions.
#
# Schema:
#
#   predictions
#   -----------
#   id                INTEGER PRIMARY KEY AUTOINCREMENT
#   alert_id          TEXT UNIQUE       -- Wazuh alert ID (string, not int)
#   alert_timestamp   TEXT              -- original alert timestamp (ISO 8601)
#   rule_id           INTEGER           -- for convenience queries
#   rule_level        INTEGER           -- for convenience queries
#   rule_groups       TEXT              -- comma-separated, for ad-hoc filtering
#   agent_name        TEXT              -- which agent generated the alert
#   srcip             TEXT              -- source IP (if present)
#   tp_probability    REAL              -- model output: P(TP | features)
#   prediction        INTEGER           -- binary: 1 = TP, 0 = FP
#   model_version     TEXT              -- which model was used
#   inference_at      TEXT              -- when the inference was run (ISO 8601)
#   features_json     TEXT              -- the feature vector as JSON (optional,
#                                        useful for debugging)
#
#   state
#   -----
#   key               TEXT PRIMARY KEY  -- e.g. "last_processed_timestamp"
#   value             TEXT              -- stored value

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def main():
    print("db_schema.py - not yet implemented")
    print("This module will:")
    print("  1. Define the predictions and state table schemas")
    print("  2. Provide init_db() - create tables if they do not exist")
    print("  3. Provide insert_prediction() - insert or update a prediction row")
    print("  4. Provide query_predictions() - read-only query helpers")


if __name__ == "__main__":
    main()
