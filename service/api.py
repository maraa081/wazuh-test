# FastAPI read-only API for querying prediction results.
#
# This is a lightweight HTTP API that allows dashboards, scripts, or ad-hoc
# curl commands to query the predictions stored in SQLite by the inference
# service.
#
# Endpoints:
#
#   GET /health                       - health check
#   GET /predictions                  - list predictions with filters:
#       ?since=ISO8601                - alerts inferred after this timestamp
#       ?until=ISO8601                - alerts inferred before this timestamp
#       ?min_probability=0.0          - minimum TP probability threshold
#       ?max_probability=1.0          - maximum TP probability threshold
#       ?prediction=1|0               - filter by binary classification
#       ?agent=agent_name             - filter by agent
#       ?rule_id=1234                 - filter by Wazuh rule ID
#       ?limit=100                    - number of results (default 100, max 1000)
#       ?offset=0                     - pagination offset
#
#   GET /predictions/{alert_id}       - single prediction by Wazuh alert ID
#   GET /stats/summary                - aggregate stats:
#       total predictions, TP count, FP count, high-risk TP count
#
#   GET /stats/by_rule                - predictions grouped by rule.id
#   GET /stats/by_agent               - predictions grouped by agent.name
#
# Usage:
#   uvicorn service.api:app --host 127.0.0.1 --port 9090
#
# Or via the inference service wrapper that starts the API alongside the
# polling loop.

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def main():
    print("api.py - not yet implemented")
    print("This module will expose a FastAPI application with:")
    print("  - GET /health")
    print("  - GET /predictions with filter parameters")
    print("  - GET /predictions/{alert_id}")
    print("  - GET /stats/summary, /stats/by_rule, /stats/by_agent")


if __name__ == "__main__":
    main()
