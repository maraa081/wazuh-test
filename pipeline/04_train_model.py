# Stage 4: train the XGBoost classifier on the engineered features.
#
# This script trains a binary classifier (true positive vs false positive) on
# the feature matrix from stage 3. It uses XGBoost with hyperparameters tuned
# for imbalanced classes: the scale_pos_weight parameter counteracts the
# expected class imbalance (typically far more FPs than TPs in a real network).
#
# Training includes:
#   - Train/test split (stratified to preserve class proportions)
#   - Cross-validation on the training set
#   - Early stopping based on validation AUC-PR (precision-recall AUC is more
#     informative than ROC AUC when classes are imbalanced)
#   - Feature importance tracking
#
# The trained model is saved for use by the evaluation script and the inference
# service.
#
# Usage:
#   python pipeline/04_train_model.py
#
# Inputs:
#   features/X.npy                   - feature matrix
#   features/y.npy                   - labels
#   features/feature_pipeline.joblib - feature pipeline (copied to model dir)
#
# Outputs:
#   models/model_v1.joblib            - trained XGBoost model
#   models/model_metadata.json        - training params, CV scores, feature names
#   models/feature_pipeline.joblib    - copy of the feature pipeline for inference

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def main():
    print("04_train_model.py - not yet implemented")
    print("This script will:")
    print("  1. Load features and labels from features/")
    print("  2. Split into train/test sets")
    print("  3. Train XGBoost with cross-validation and early stopping")
    print("  4. Save the trained model and training metadata")


if __name__ == "__main__":
    main()
