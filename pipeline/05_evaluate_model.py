# Stage 5: evaluate the trained model on the held-out test set.
#
# This script loads the trained model and runs it against the test set to
# produce a comprehensive evaluation report. The report covers:
#
#   - Classification metrics: precision, recall, F1 for each class, plus
#     macro and weighted averages
#   - F2-score: recall-weighted F-score that penalizes false negatives harder
#   - Confusion matrix (raw counts and normalized percentages)
#   - ROC curve and PR curve plots
#   - Precision-recall threshold curve (to help select the operating point)
#   - SHAP summary plot: feature importance with direction of impact
#   - Per-attack-type breakdown: how well the model performs on SSH bruteforce
#     vs nmap scans
#
# The priority metric is recall on the true positive class: we want to catch
# as many real attacks as possible, even if it means investigating a few more
# false positives.
#
# Usage:
#   python pipeline/05_evaluate_model.py
#
# Inputs:
#   models/model_v1.joblib            - trained model
#   features/X.npy, features/y.npy    - full feature matrix and labels
#   features/feature_names.txt        - feature column names for SHAP
#
# Output:
#   reports/eval_report_v1.html        - standalone HTML report with all plots
#   reports/eval_metrics_v1.json       - numerical metrics in structured format

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def main():
    print("05_evaluate_model.py - not yet implemented")
    print("This script will:")
    print("  1. Load the trained model and test data")
    print("  2. Compute all evaluation metrics")
    print("  3. Generate precision-recall and ROC curves")
    print("  4. Run SHAP analysis and generate feature importance plots")
    print("  5. Save the evaluation report as HTML + JSON")


if __name__ == "__main__":
    main()
