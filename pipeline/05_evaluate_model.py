#!/usr/bin/env python3
"""
05_evaluate_model.py — Evalue le XGBoost avec SHAP, courbes et rapports.
Usage: python3 05_evaluate_model.py [--input features/feature_matrix.csv]
"""

import argparse
import json
import os
import sys
import warnings
warnings.filterwarnings("ignore")

import numpy as np

PROJECT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULT_INPUT = os.path.join(PROJECT_DIR, "features", "feature_matrix.csv")
MODEL_DIR = os.path.join(PROJECT_DIR, "models")
REPORT_DIR = os.path.join(PROJECT_DIR, "reports")


def load(path):
    """Charge la matrice de features."""
    import csv
    rows = list(csv.DictReader(open(path)))
    feature_names = [k for k in rows[0].keys() if k not in ("timestamp", "label")]
    X = np.array([[float(r[k]) for k in feature_names] for r in rows])
    y = np.array([int(r["label"]) for r in rows])
    timestamps = [r.get("timestamp", "") for r in rows]
    return X, y, feature_names, timestamps


def evaluate(model_path, X, y, feature_names, output_dir):
    """Execute l'evaluation : SHAP, courbes, reglage du seuil, rapport."""
    import xgboost as xgb
    from sklearn.model_selection import train_test_split
    from sklearn.metrics import (
        precision_score, recall_score, f1_score, fbeta_score,
        roc_auc_score, average_precision_score, precision_recall_curve,
        roc_curve,
    )

    os.makedirs(output_dir, exist_ok=True)

    # Separation train/test
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.25, random_state=42, stratify=y
    )

    # Chargement du modele
    model = xgb.XGBClassifier()
    model.load_model(model_path)

    # Predictions
    y_pred = model.predict(X_test)
    y_proba = model.predict_proba(X_test)[:, 1]

    # ── Metriques ──
    metrics = {
        "precision": round(precision_score(y_test, y_pred, zero_division=0), 4),
        "recall": round(recall_score(y_test, y_pred, zero_division=0), 4),
        "f1": round(f1_score(y_test, y_pred, zero_division=0), 4),
        "f2": round(fbeta_score(y_test, y_pred, beta=2, zero_division=0), 4),
        "roc_auc": round(roc_auc_score(y_test, y_proba), 4),
        "pr_auc": round(average_precision_score(y_test, y_proba), 4),
    }

    print(f"\n  Metrics:")
    for k, v in metrics.items():
        print(f"    {k}: {v}")

    # ── Reglage du seuil ──
    precisions, recalls, thresholds = precision_recall_curve(y_test, y_proba)
    best_f2 = 0
    best_thresh = 0.5
    for i, t in enumerate(thresholds):
        if t >= 0.99:
            continue
        p = precisions[i] if i < len(precisions) else 0
        r = recalls[i] if i < len(recalls) else 0
        f2 = (5 * p * r) / (4 * p + r) if (4 * p + r) > 0 else 0
        if f2 > best_f2:
            best_f2 = f2
            best_thresh = t

    print(f"\n  Best threshold: {best_thresh:.3f} (F2={best_f2:.4f})")
    metrics["best_threshold"] = round(best_thresh, 3)
    metrics["best_f2"] = round(best_f2, 4)

    # ── Importance des features (modele) ──
    importance = model.feature_importances_
    top_idx = np.argsort(importance)[-15:][::-1]
    top_features = []
    print(f"\n  Top 15 features (importance):")
    for idx in top_idx:
        top_features.append({"name": feature_names[idx], "importance": round(float(importance[idx]), 4)})
        bar = "|" * int(importance[idx] * 100)
        print(f"    {feature_names[idx]:<30} {importance[idx]:.4f}  {bar}")

    # ── Analyse SHAP ──
    print("\n  Computing SHAP values (this may take a moment)...")
    try:
        import shap
        explainer = shap.TreeExplainer(model)
        shap_values = explainer.shap_values(X_test[:100])  # Sample for speed

        # Top SHAP features
        mean_shap = np.abs(shap_values).mean(axis=0)
        shap_top = np.argsort(mean_shap)[-10:][::-1]

        print(f"\n  Top 10 SHAP features:")
        for idx in shap_top:
            print(f"    {feature_names[idx]:<30} mean|SHAP|={mean_shap[idx]:.4f}")

        # Graphique SHAP
        try:
            import matplotlib
            matplotlib.use("Agg")
            import matplotlib.pyplot as plt

            plt.figure(figsize=(10, 6))
            shap.summary_plot(shap_values, X_test[:100], feature_names=feature_names,
                              show=False, max_display=10)
            shap_path = os.path.join(output_dir, "shap_summary.png")
            plt.tight_layout()
            plt.savefig(shap_path, dpi=150, bbox_inches="tight")
            plt.close()
            print(f"\n  SHAP plot saved: {shap_path}")
            metrics["shap_plot"] = shap_path
        except Exception as e:
            print(f"  SHAP plot failed: {e}")

        shap_metrics = {
            "top_shap": [
                {"feature": feature_names[idx], "importance": float(mean_shap[idx])}
                for idx in shap_top[:5]
            ]
        }
        metrics.update(shap_metrics)

    except ImportError:
        print("  SHAP not installed. Install: pip install shap")
    except Exception as e:
        print(f"  SHAP error: {e}")

    # ── Sauvegarde du rapport ──
    report_path = os.path.join(output_dir, "evaluation_report.json")
    with open(report_path, "w") as f:
        json.dump(metrics, f, indent=2)
    print(f"\n  Report saved: {report_path}")

    # ── Resume ──
    print(f"\n  {'=' * 50}")
    print(f"  EVALUATION SUMMARY")
    print(f"  {'=' * 50}")
    print(f"  Recall (TPR):    {metrics['recall']:.4f}  (cible: >0.95)")
    print(f"  Precision:       {metrics['precision']:.4f}  (cible: >0.80)")
    print(f"  F2-score:        {metrics['f2']:.4f}  (cible: >0.90)")
    print(f"  ROC AUC:         {metrics['roc_auc']:.4f}  (cible: >0.95)")
    print(f"  PR AUC:          {metrics['pr_auc']:.4f}  (cible: >0.90)")
    print(f"  Best threshold:  {metrics['best_threshold']:.3f}")
    print(f"  {'=' * 50}")

    return metrics


def main():
    parser = argparse.ArgumentParser(description="Evaluate XGBoost model")
    parser.add_argument("--input", default=DEFAULT_INPUT, help="Feature matrix CSV")
    parser.add_argument("--model", default="", help="Model path")
    parser.add_argument("--output", default=REPORT_DIR, help="Report directory")
    args = parser.parse_args()

    model_path = args.model or os.path.join(MODEL_DIR, "xgb_model.json")
    output_dir = args.output

    print("=" * 60)
    print(" MODEL EVALUATION — 05_evaluate_model.py")
    print("=" * 60)
    print(f"  Input:  {args.input}")
    print(f"  Model:  {model_path}")
    print(f"  Output: {output_dir}")
    print("")

    if not os.path.exists(model_path):
        print(f"ERROR: Model not found at {model_path}")
        print("Run 04_train_model.py first.")
        sys.exit(1)

    # Chargement des donnees
    print("--- Loading data ---")
    X, y, feature_names, timestamps = load(args.input)
    print(f"  Samples: {X.shape[0]}, Features: {X.shape[1]}")

    # Evaluate
    print("\n--- Evaluating ---")
    evaluate(model_path, X, y, feature_names, output_dir)

    print("\n" + "=" * 60)
    print(" Evaluation complete.")
    print("=" * 60)


if __name__ == "__main__":
    main()
