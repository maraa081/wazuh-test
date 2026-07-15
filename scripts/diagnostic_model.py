#!/usr/bin/env python3
"""Diagnostic : re-entraine XGBoost depuis la matrice de features et teste les predictions."""
import json, csv, xgboost as xgb, numpy as np
from sklearn.model_selection import train_test_split

print("Loading feature matrix...")
rows = list(csv.DictReader(open("features/feature_matrix.csv")))
feature_names = [k for k in rows[0].keys() if k not in ("timestamp", "label")]
X = np.array([[float(r[k]) for k in feature_names] for r in rows])
y = np.array([int(r["label"]) for r in rows])
print(f"Samples: {len(y)}, Features: {len(feature_names)}, TP: {y.sum()}")

# Split
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.25, random_state=42, stratify=y)
neg, pos = (y_train == 0).sum(), (y_train == 1).sum()
scale = neg / max(pos, 1)
print(f"Train: {len(y_train)}, Test: {len(y_test)}, Scale: {scale:.2f}")

# Old model test
print("\n--- Old model test ---")
old = xgb.XGBClassifier()
old.load_model("models/xgb_model.json")
old_proba = old.predict_proba(X_test[:5])[:, 1]
for i, p in enumerate(old_proba):
    print(f"  Sample {i}: actual={int(y_test[i])}, predicted={'TP' if p>=0.5 else 'FP'}, conf={p:.4f}")

# Retrain
print("\n--- Retraining ---")
model = xgb.XGBClassifier(n_estimators=300, max_depth=6, learning_rate=0.1,
    scale_pos_weight=scale, random_state=42, verbosity=0, early_stopping_rounds=20)
model.fit(X_train, y_train, eval_set=[(X_test, y_test)], verbose=False)

# New model test
probas = model.predict_proba(X_test[:5])[:, 1]
print("\n--- New model test ---")
for i, p in enumerate(probas):
    print(f"  Sample {i}: actual={int(y_test[i])}, predicted={'TP' if p>=0.5 else 'FP'}, conf={p:.4f}")

# Save
model.save_model("models/xgb_model_fixed.json")
print(f"\nSaved: models/xgb_model_fixed.json")

# Reload test
m2 = xgb.XGBClassifier()
m2.load_model("models/xgb_model_fixed.json")
p2 = m2.predict_proba(X_test[:5])[:, 1]
print("\n--- Reload test ---")
for i, p in enumerate(p2):
    print(f"  Sample {i}: actual={int(y_test[i])}, predicted={'TP' if p>=0.5 else 'FP'}, conf={p:.4f}")
