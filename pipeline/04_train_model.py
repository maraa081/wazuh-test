#!/usr/bin/env python3
"""
04_train_model.py — Entraine le classifieur XGBoost sur la matrice de features.
Usage: python3 04_train_model.py [--input features/feature_matrix.csv]
"""

import argparse
import csv
import json
import os
import sys
import warnings
warnings.filterwarnings("ignore")

import numpy as np

PROJECT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULT_INPUT = os.path.join(PROJECT_DIR, "features", "feature_matrix.csv")
MODEL_DIR = os.path.join(PROJECT_DIR, "models")


def load_features(path):
    """Charge la matrice de features, separe X et y."""
    rows = []
    with open(path) as f:
        reader = csv.DictReader(f)
        for row in reader:
            rows.append(row)

    feature_names = [k for k in rows[0].keys() if k not in ("timestamp", "label")]
    X = []
    y = []
    timestamps = []
    for r in rows:
        X.append([float(r[k]) for k in feature_names])
        y.append(int(r["label"]))
        timestamps.append(r.get("timestamp", ""))

    return np.array(X), np.array(y), feature_names, timestamps


def train_xgboost(X, y, feature_names):
    """Entraine le classifieur XGBoost."""
    import xgboost as xgb
    from sklearn.model_selection import train_test_split

    # Separation train/test
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.25, random_state=42, stratify=y
    )

    print(f"  Train: {len(y_train)} samples ({y_train.sum()} TP)")
    print(f"  Test:  {len(y_test)} samples ({y_test.sum()} TP)")

    # Ratio d'equilibrage pour scale_pos_weight
    neg = (y_train == 0).sum()
    pos = (y_train == 1).sum()
    scale = neg / max(pos, 1)
    print(f"  Scale pos weight: {scale:.2f}")

    # Modele
    model = xgb.XGBClassifier(
        n_estimators=300,
        max_depth=6,
        learning_rate=0.1,
        subsample=0.8,
        colsample_bytree=0.8,
        scale_pos_weight=scale,
        eval_metric="aucpr",
        early_stopping_rounds=20,
        random_state=42,
        verbosity=0,
        use_label_encoder=False,
    )

    # Entrainement
    model.fit(
        X_train, y_train,
        eval_set=[(X_test, y_test)],
        verbose=False,
    )

    # Prediction
    y_pred = model.predict(X_test)
    y_proba = model.predict_proba(X_test)[:, 1]

    # Metriques
    from sklearn.metrics import (
        accuracy_score, precision_score, recall_score, f1_score, fbeta_score,
        confusion_matrix, roc_auc_score, average_precision_score,
    )

    acc = accuracy_score(y_test, y_pred)
    prec = precision_score(y_test, y_pred, zero_division=0)
    rec = recall_score(y_test, y_pred, zero_division=0)
    f1 = f1_score(y_test, y_pred, zero_division=0)
    f2 = fbeta_score(y_test, y_pred, beta=2, zero_division=0)
    roc_auc = roc_auc_score(y_test, y_proba)
    pr_auc = average_precision_score(y_test, y_proba)
    cm = confusion_matrix(y_test, y_pred)

    metrics = {
        "accuracy": round(acc, 4),
        "precision": round(prec, 4),
        "recall": round(rec, 4),
        "f1_score": round(f1, 4),
        "f2_score": round(f2, 4),
        "roc_auc": round(roc_auc, 4),
        "pr_auc": round(pr_auc, 4),
        "confusion_matrix": cm.tolist(),
        "scale_pos_weight": round(scale, 2),
        "train_samples": len(y_train),
        "test_samples": len(y_test),
        "test_tp": int(y_test.sum()),
    }

    print(f"\n  Accuracy:  {acc:.4f}")
    print(f"  Precision: {prec:.4f}")
    print(f"  Recall:    {rec:.4f}")
    print(f"  F1-score:  {f1:.4f}")
    print(f"  F2-score:  {f2:.4f}")
    print(f"  ROC AUC:   {roc_auc:.4f}")
    print(f"  PR AUC:    {pr_auc:.4f}")
    print(f"\n  Confusion Matrix:")
    print(f"               Pred TP    Pred FP")
    print(f"  Actual TP    {cm[1][1]:<10} {cm[1][0]}")
    print(f"  Actual FP    {cm[0][1]:<10} {cm[0][0]}")

    # Importance des features
    importance = model.feature_importances_
    top_features = sorted(
        zip(feature_names, importance), key=lambda x: x[1], reverse=True
    )[:15]

    print(f"\n  Top 15 features:")
    for name, imp in top_features:
        bar = "|" * int(imp * 100)
        print(f"    {name:<25} {imp:.3f}  {bar}")

    return model, metrics, top_features


def save_model(model, metrics, feature_names, top_features, model_path):
    """Sauvegarde le modele et les metriques."""
    os.makedirs(MODEL_DIR, exist_ok=True)

    # Save XGBoost model
    model.save_model(model_path)
    print(f"\n  Model saved: {model_path}")

    # Save metrics as JSON
    metrics_path = model_path.replace(".json", "_metrics.json")
    if metrics_path == model_path:
        metrics_path = os.path.join(MODEL_DIR, "metrics.json")

    metrics["feature_names"] = feature_names
    metrics["top_features"] = [
        {"name": n, "importance": round(float(i), 4)} for n, i in top_features
    ]

    with open(metrics_path, "w") as f:
        json.dump(metrics, f, indent=2)
    print(f"  Metrics: {metrics_path}")


def main():
    parser = argparse.ArgumentParser(description="Train XGBoost on Wazuh alerts")
    parser.add_argument("--input", default=DEFAULT_INPUT, help="Feature matrix CSV")
    parser.add_argument("--output", default="", help="Model output path")
    args = parser.parse_args()

    model_path = args.output or os.path.join(MODEL_DIR, "xgb_model.json")

    print("=" * 60)
    print(" XGBOOST TRAINING — 04_train_model.py")
    print("=" * 60)
    print(f"  Input:  {args.input}")
    print(f"  Output: {model_path}")
    print("")

    # Chargement
    print("--- Loading features ---")
    X, y, feature_names, timestamps = load_features(args.input)
    print(f"  Samples: {X.shape[0]}, Features: {X.shape[1]}")
    print(f"  TP: {y.sum()} ({y.sum() / len(y) * 100:.1f}%)")
    print(f"  FP: {(y == 0).sum()} ({(y == 0).sum() / len(y) * 100:.1f}%)")

    # Entrainement
    print("\n--- Training XGBoost ---")
    model, metrics, top_features = train_xgboost(X, y, feature_names)

    # Save
    print("\n--- Saving ---")
    save_model(model, metrics, feature_names, top_features, model_path)

    print("\n" + "=" * 60)
    print(" Training complete. Next: python3 pipeline/05_evaluate_model.py")
    print("=" * 60)


if __name__ == "__main__":
    main()
