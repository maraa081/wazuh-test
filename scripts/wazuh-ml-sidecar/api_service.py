#!/usr/bin/env python3
"""
api_service.py — REST API for querying ML predictions.
Runs on port 9090. Callable from Wazuh Dashboard or any HTTP client.

Endpoints:
  GET  /health              → OK if service is alive
  GET  /stats               → Summary statistics (TP/FP counts)
  GET  /predictions         → Paginated predictions list
  GET  /predictions/{id}    → Single prediction by alert_id
  GET  /predictions/recent  → Last 50 predictions

Usage:
  python3 api_service.py [--db predictions.db] [--port 9090] [--host 0.0.0.0]

Update-Proof:
  - No dependency on Wazuh files or configs
  - Only reads its own SQLite database
  - Survives any Wazuh update
"""

import argparse
import json
import os
import sqlite3
from datetime import datetime

import uvicorn
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# ─── Paths ────────────────────────────────────────────────────────
PROJECT_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DEFAULT_DB_FILE = os.path.join(PROJECT_DIR, "data", "predictions", "predictions.db")

app = FastAPI(
    title="Wazuh ML Sidecar API",
    description="REST API for querying ML model predictions on Wazuh alerts",
    version="1.0.0",
)

# CORS: Allow requests from Wazuh Dashboard
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ─── Database connection ─────────────────────────────────────────

def get_db(db_path: str = None):
    if db_path is None:
        db_path = DEFAULT_DB_FILE
    """Return a connection to the SQLite DB (thread-safe for reads)."""
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn


# ─── Models ───────────────────────────────────────────────────────

class Prediction(BaseModel):
    alert_id: str
    timestamp: str
    rule_id: str
    rule_description: str
    agent_name: str
    srcip: str
    prediction: int
    confidence: float
    created_at: str

    class Config:
        from_attributes = True


class Stats(BaseModel):
    total_predictions: int
    true_positives: int
    false_positives: int
    fp_percentage: float
    tp_percentage: float
    last_alert_timestamp: str
    db_path: str


# ─── Endpoints ────────────────────────────────────────────────────

@app.get("/health")
async def health():
    """Health check."""
    return {"status": "ok", "timestamp": datetime.now().isoformat()}


@app.get("/stats")
async def stats():
    """Return summary statistics."""
    db = get_db()
    try:
        total = db.execute("SELECT COUNT(*) as c FROM predictions").fetchone()["c"]
        tp = db.execute("SELECT COUNT(*) as c FROM predictions WHERE prediction=1").fetchone()["c"]
        fp = total - tp
        last_ts = db.execute("SELECT MAX(timestamp) as ts FROM predictions").fetchone()
        last = last_ts["ts"] if last_ts and last_ts["ts"] else "N/A"
    finally:
        db.close()

    return {
        "total_predictions": total,
        "true_positives": tp,
        "false_positives": fp,
        "fp_percentage": round(fp / total * 100, 1) if total > 0 else 0,
        "tp_percentage": round(tp / total * 100, 1) if total > 0 else 0,
        "last_alert_timestamp": last,
        "db_path": DEFAULT_DB_FILE,
    }


@app.get("/predictions")
async def get_predictions(
    limit: int = Query(50, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    prediction: int = Query(None, ge=0, le=1, description="Filter: 0=FP, 1=TP"),
    rule_id: str = Query(None, description="Filter by rule ID"),
    since: str = Query(None, description="ISO timestamp: show alerts after this date"),
):
    """Return paginated predictions."""
    db = get_db()
    try:
        query = "SELECT * FROM predictions WHERE 1=1"
        params = []

        if prediction is not None:
            query += " AND prediction = ?"
            params.append(prediction)
        if rule_id:
            query += " AND rule_id = ?"
            params.append(rule_id)
        if since:
            query += " AND timestamp >= ?"
            params.append(since)

        # Count total matching
        count_query = query.replace("SELECT *", "SELECT COUNT(*) as total")
        total = db.execute(count_query, params).fetchone()["total"]

        # Fetch page
        query += " ORDER BY timestamp DESC LIMIT ? OFFSET ?"
        params.extend([limit, offset])
        rows = db.execute(query, params).fetchall()

        predictions_list = [dict(row) for row in rows]
        # Remove features_json from listing (it's large)
        for p in predictions_list:
            p.pop("features_json", None)
    finally:
        db.close()

    return {
        "total": total,
        "limit": limit,
        "offset": offset,
        "predictions": predictions_list,
    }


@app.get("/predictions/recent")
async def get_recent(limit: int = Query(50, ge=1, le=200)):
    """Get the most recent predictions."""
    return await get_predictions(limit=limit, offset=0)


@app.get("/predictions/{alert_id}")
async def get_prediction(alert_id: str):
    """Get prediction for a specific alert ID."""
    db = get_db()
    try:
        row = db.execute(
            "SELECT * FROM predictions WHERE alert_id = ?", (alert_id,)
        ).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Prediction not found")
        return dict(row)
    finally:
        db.close()


@app.post("/predictions/query")
async def query_by_ids(alert_ids: list[str]):
    """Get predictions for multiple alert IDs at once."""
    if not alert_ids:
        return {"predictions": []}
    
    db = get_db()
    try:
        placeholders = ",".join("?" for _ in alert_ids)
        rows = db.execute(
            f"SELECT * FROM predictions WHERE alert_id IN ({placeholders})",
            alert_ids,
        ).fetchall()
        return {"predictions": [dict(row) for row in rows]}
    finally:
        db.close()


# ─── Cleanup old predictions (optional) ───────────────────────────

@app.delete("/predictions/cleanup")
async def cleanup(keep_days: int = Query(7, ge=1)):
    """Delete predictions older than N days."""
    db = get_db()
    try:
        from datetime import timedelta
        cutoff = (datetime.utcnow() - timedelta(days=keep_days)).isoformat()
        deleted = db.execute(
            "DELETE FROM predictions WHERE timestamp < ?", (cutoff,)
        ).rowcount
        db.commit()
    finally:
        db.close()
    return {"deleted": deleted, "keep_days": keep_days}


# ─── Main ─────────────────────────────────────────────────────────

def main():
    global DEFAULT_DB_FILE
    parser = argparse.ArgumentParser(description="Wazuh ML Sidecar - REST API")
    parser.add_argument("--db", default=DEFAULT_DB_FILE)
    parser.add_argument("--port", type=int, default=9090)
    parser.add_argument("--host", default="0.0.0.0")
    parser.add_argument("--reload", action="store_true", help="Auto-reload on code change")
    args = parser.parse_args()

    DEFAULT_DB_FILE = args.db

    print("=" * 60)
    print(" WAZUH ML SIDECAR API")
    print("=" * 60)
    print(f"  Database: {args.db}")
    print(f"  Endpoint: http://{args.host}:{args.port}")
    print(f"  Docs:     http://{args.host}:{args.port}/docs")
    print(f"  Health:   http://{args.host}:{args.port}/health")
    print()
    print("  Endpoints:")
    print("    GET  /health")
    print("    GET  /stats")
    print("    GET  /predictions")
    print("    GET  /predictions/recent")
    print("    GET  /predictions/{alert_id}")
    print("    POST /predictions/query")
    print("    DELETE /predictions/cleanup")
    print()

    uvicorn.run(app, host=args.host, port=args.port, reload=args.reload)


if __name__ == "__main__":
    main()
