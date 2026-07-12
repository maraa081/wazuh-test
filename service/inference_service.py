# Inference service: polling loop that scores new alerts.
#
# This is the production component. It runs as a standalone service that:
#
#   1. Polls the Wazuh API at regular intervals for new alerts (based on the
#      last processed alert timestamp, stored in the SQLite database).
#   2. Extracts the same features used during model training, using the saved
#      feature pipeline.
#   3. Runs the trained XGBoost model to get a TP probability for each alert.
#   4. Stores the prediction (alert ID, timestamp, TP probability, binary
#      classification, feature values used) in a local SQLite database.
#
# The service does not modify any Wazuh files. It is a read-only consumer of
# the Wazuh API and a write-only producer for its own database.
#
# A separate FastAPI server (api.py) provides read access to the stored
# predictions for dashboards and manual queries.
#
# Usage:
#   python service/inference_service.py
#
# The service runs until interrupted with Ctrl+C. Intended to be run under
# systemd or supervisord for long-term operation.

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def main():
    print("inference_service.py - not yet implemented")
    print("This service will:")
    print("  1. Load config, model, and feature pipeline at startup")
    print("  2. Initialize the SQLite database (create tables if needed)")
    print("  3. Enter a polling loop:")
    print("     a. Fetch new alerts from Wazuh API (since last_processed)")
    print("     b. Extract features for each new alert")
    print("     c. Score each alert with the model")
    print("     d. Store the prediction in SQLite")
    print("     e. Sleep for poll_interval_seconds")
    print("  4. Gracefully shut down on SIGTERM/SIGINT")


if __name__ == "__main__":
    main()
