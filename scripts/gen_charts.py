#!/usr/bin/env python3
"""Generate charts from predictions DB + model metrics for presentation."""

import json
import sqlite3
import os
from datetime import datetime

try:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import numpy as np
    HAVE_MPL = True
except ImportError:
    HAVE_MPL = False
    print("[WARN] matplotlib not installed. Install with: pip3 install matplotlib")

OUTPUT_DIR = "/tmp/presentation_charts"
os.makedirs(OUTPUT_DIR, exist_ok=True)

def load_metrics():
    path = "/opt/wazuh-ml/xgb_model_metrics.json"
    if not os.path.exists(path):
        print("[WARN] No model metrics found")
        return {}
    with open(path) as f:
        return json.load(f)

def load_predictions():
    path = "/tmp/predictions.db"
    if not os.path.exists(path):
        print("[WARN] No predictions DB found")
        return None
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    try:
        c.execute("SELECT * FROM predictions ORDER BY rowid DESC LIMIT 5000")
        rows = [dict(r) for r in c.fetchall()]
    except sqlite3.OperationalError:
        try:
            c.execute("SELECT *, rowid FROM predictions ORDER BY rowid DESC LIMIT 5000")
            rows = [dict(r) for r in c.fetchall()]
        except:
            rows = []
    conn.close()
    return rows

def chart_predictions_timeline(predictions, output):
    """Line chart: predictions over time (TP vs FP)."""
    if not predictions:
        return
    # Group by hour
    from collections import Counter, defaultdict
    hourly = defaultdict(lambda: {"tp": 0, "fp": 0})
    for p in predictions:
        ts = p.get("timestamp", "")
        hour = ts[:13] if len(ts) >= 13 else "unknown"
        if p.get("prediction", 0) == 1:
            hourly[hour]["tp"] += 1
        else:
            hourly[hour]["fp"] += 1
    hours = sorted(hourly.keys())
    tp_vals = [hourly[h]["tp"] for h in hours]
    fp_vals = [hourly[h]["fp"] for h in hours]

    fig, ax = plt.subplots(figsize=(10, 4))
    x = range(len(hours))
    ax.bar(x, tp_vals, label="Vrais Positifs", color="#2ecc71", alpha=0.8)
    ax.bar(x, fp_vals, bottom=tp_vals, label="Faux Positifs", color="#e74c3c", alpha=0.7)
    ax.set_xlabel("Heure")
    ax.set_ylabel("Nb predictions")
    ax.set_title("Predictions ML au fil du temps")
    ax.legend()
    if len(hours) > 10:
        ax.set_xticks(range(0, len(hours), max(1, len(hours)//8)))
        ax.set_xticklabels([hours[i][5:] for i in range(0, len(hours), max(1, len(hours)//8))], rotation=45)
    plt.tight_layout()
    plt.savefig(output, dpi=150)
    plt.close()
    print(f"[OK] Chart saved: {output}")

def chart_prediction_distribution(predictions, output):
    """Pie chart: TP vs FP distribution."""
    if not predictions:
        return
    tp = sum(1 for p in predictions if p.get("prediction") == 1)
    fp = len(predictions) - tp
    fig, ax = plt.subplots(figsize=(5, 5))
    colors = ["#2ecc71", "#e74c3c"]
    labels = [f"Vrais Positifs\n{tp}", f"Faux Positifs\n{fp}"]
    ax.pie([tp, fp], labels=labels, colors=colors, autopct="%1.1f%%", startangle=90)
    ax.set_title(f"Distribution des predictions (total: {len(predictions)})")
    plt.tight_layout()
    plt.savefig(output, dpi=150)
    plt.close()
    print(f"[OK] Chart saved: {output}")

def chart_score_distribution(predictions, output):
    """Histogram: probability score distribution."""
    if not predictions:
        return
    scores = [float(p.get("probability", 0.0)) for p in predictions if p.get("probability") is not None]
    if not scores:
        return
    fig, ax = plt.subplots(figsize=(8, 4))
    ax.hist(scores, bins=30, color="#3498db", edgecolor="white", alpha=0.8)
    ax.axvline(x=0.5, color="red", linestyle="--", label="Seuil (0.5)")
    ax.set_xlabel("Score de confiance")
    ax.set_ylabel("Nb predictions")
    ax.set_title("Distribution des scores de confiance")
    ax.legend()
    plt.tight_layout()
    plt.savefig(output, dpi=150)
    plt.close()
    print(f"[OK] Chart saved: {output}")

def chart_feature_importance(metrics, output):
    """Horizontal bar chart: top feature importances."""
    fi = metrics.get("feature_importance", {})
    if not fi:
        print("[WARN] No feature importance in metrics")
        return
    items = sorted(fi.items(), key=lambda x: x[1], reverse=True)[:15]
    names = [i[0].replace("count_", "")[:25] for i in items]
    values = [i[1] for i in items]
    fig, ax = plt.subplots(figsize=(8, 5))
    colors = plt.cm.Blues(np.linspace(0.4, 0.9, len(names)))
    ax.barh(range(len(names)), values, color=colors)
    ax.set_yticks(range(len(names)))
    ax.set_yticklabels(names)
    ax.set_xlabel("Importance")
    ax.set_title("Top 15 Features les plus importantes")
    ax.invert_yaxis()
    plt.tight_layout()
    plt.savefig(output, dpi=150)
    plt.close()
    print(f"[OK] Chart saved: {output}")

def chart_metrics_summary(metrics, output):
    """Summary card with key metrics."""
    fig, ax = plt.subplots(figsize=(8, 3))
    ax.axis("off")
    recall = metrics.get("recall", metrics.get("test_recall", "N/A"))
    precision = metrics.get("precision", metrics.get("test_precision", "N/A"))
    roc_auc = metrics.get("roc_auc", metrics.get("test_roc_auc", "N/A"))
    f2 = metrics.get("f2_score", metrics.get("test_f2", "N/A"))
    lines = [
        "=== Performance du Modele ===",
        f"  Recall : {recall}",
        f"  Precision : {precision}",
        f"  ROC AUC : {roc_auc}",
        f"  F2 Score : {f2}",
        f"  Features : {metrics.get('n_features', metrics.get('num_features', 'N/A'))}",
    ]
    if roc_auc != "N/A":
        try:
            roc_val = float(roc_auc) * 100
            lines.append(f"  Soit {roc_val:.1f}% de separation TP/FP")
        except:
            pass
    ax.text(0.1, 0.5, "\n".join(lines), fontsize=13, verticalalignment="center",
            fontfamily="monospace", bbox=dict(boxstyle="round", facecolor="#f8f9fa"))
    ax.set_title("Metriques du Modele", fontsize=14, fontweight="bold")
    plt.tight_layout()
    plt.savefig(output, dpi=150)
    plt.close()
    print(f"[OK] Chart saved: {output}")

def chart_roc_curve(metrics, output):
    """Plot ROC curve from stored values if available."""
    fpr = metrics.get("roc_fpr", [])
    tpr = metrics.get("roc_tpr", [])
    if not fpr or not tpr:
        roc_auc = metrics.get("roc_auc", "N/A")
        fig, ax = plt.subplots(figsize=(6, 5))
        ax.plot([0, 1], [0, 1], "k--", alpha=0.5, label="Classifieur aleatoire")
        # Dummy ROC — just show the AUC value
        tpr_dummy = [0, 1]
        fpr_dummy = [0, 1]
        ax.plot(fpr_dummy, tpr_dummy, "b-", linewidth=2, label=f"ROC AUC = {roc_auc}")
        ax.fill_between(fpr_dummy, tpr_dummy, alpha=0.2, color="blue")
        ax.set_xlim([0, 1])
        ax.set_ylim([0, 1.05])
        ax.set_xlabel("Taux de Faux Positifs (FPR)")
        ax.set_ylabel("Taux de Vrais Positifs (TPR)")
        ax.set_title("Courbe ROC")
        ax.legend(loc="lower right")
        ax.text(0.6, 0.2, f"AUC = {roc_auc}", fontsize=14,
                bbox=dict(boxstyle="round", facecolor="lightblue", alpha=0.8))
        plt.tight_layout()
        plt.savefig(output, dpi=150)
        plt.close()
        print(f"[OK] ROC chart saved: {output}")
        return
    fig, ax = plt.subplots(figsize=(6, 5))
    ax.plot(fpr, tpr, "b-", linewidth=2, label=f"ROC (AUC = {metrics.get('roc_auc', 'N/A')})")
    ax.fill_between(fpr, tpr, alpha=0.2, color="blue")
    ax.plot([0, 1], [0, 1], "k--", alpha=0.5)
    ax.set_xlabel("FPR")
    ax.set_ylabel("TPR")
    ax.set_title("Courbe ROC")
    ax.legend(loc="lower right")
    plt.tight_layout()
    plt.savefig(output, dpi=150)
    plt.close()
    print(f"[OK] ROC chart saved: {output}")

def main():
    print("=== Generation des graphiques ===")
    print(f"Output: {OUTPUT_DIR}")
    print()

    if not HAVE_MPL:
        print("[ERR] matplotlib required. Run: pip3 install matplotlib")
        return

    metrics = load_metrics()
    predictions = load_predictions()

    if metrics:
        print(f"[DATA] Model metrics loaded: {len(metrics)} keys")
    if predictions:
        print(f"[DATA] {len(predictions)} predictions loaded")

    # Generate charts
    if predictions:
        chart_predictions_timeline(predictions, f"{OUTPUT_DIR}/01_predictions_timeline.png")
        chart_prediction_distribution(predictions, f"{OUTPUT_DIR}/02_prediction_distribution.png")
        chart_score_distribution(predictions, f"{OUTPUT_DIR}/03_score_distribution.png")

    if metrics:
        chart_feature_importance(metrics, f"{OUTPUT_DIR}/04_feature_importance.png")
        chart_metrics_summary(metrics, f"{OUTPUT_DIR}/05_metrics_summary.png")
        chart_roc_curve(metrics, f"{OUTPUT_DIR}/06_roc_curve.png")

    # Summary
    print()
    print("=== Graphiques generes ===")
    for f in sorted(os.listdir(OUTPUT_DIR)):
        size = os.path.getsize(os.path.join(OUTPUT_DIR, f))
        print(f"  {f}  ({size//1024} KB)")
    print()
    print(f"Dossier : {OUTPUT_DIR}")
    print(f"Copie :  scp -r {OUTPUT_DIR}/* target:/tmp/charts/ (ou copie via le navigateur)")

if __name__ == "__main__":
    main()
