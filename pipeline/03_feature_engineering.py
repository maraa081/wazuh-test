# Stage 3: transform raw labeled alerts into numerical feature vectors.
#
# Raw alerts contain fields like rule.id, rule.level, srcip, etc. that are
# useful but not directly consumable by a model. This script converts them into
# numerical features:
#
#   - Categorical fields (rule.id, decoder.name, agent.name) -> one-hot encoding
#   - Numerical fields (rule.level, alert frequency) -> kept as-is or scaled
#   - Timestamp -> hour of day, day of week, weekend flag, business hours
#   - Frequency features -> rolling counts of alerts per rule and per srcip
#     over configurable time windows (1min, 5min, 15min)
#   - srcip features -> internal vs external IP, presence of source IP
#
# The output is a feature matrix saved alongside the labels for use by the
# training script.
#
# The feature pipeline (sklearn Pipeline + ColumnTransformer) is saved as well,
# so the same transformations can be applied to new alerts during inference
# without leaking training statistics.
#
# Usage:
#   python pipeline/03_feature_engineering.py
#
# Input:
#   data/labeled/labeled_dataset.csv  - labeled alerts from stage 2
#
# Outputs:
#   features/X.npy                    - feature matrix (numpy array)
#   features/y.npy                    - label vector (numpy array)
#   features/feature_pipeline.joblib  - serialized sklearn Pipeline
#   features/feature_names.txt        - column names for interpretability

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def main():
    print("03_feature_engineering.py - not yet implemented")
    print("This script will:")
    print("  1. Load labeled dataset from data/labeled/")
    print("  2. Extract and transform features using config/ features settings")
    print("  3. Compute sliding-window frequency features")
    print("  4. Encode categorical fields")
    print("  5. Save the feature matrix and the pipeline object")


if __name__ == "__main__":
    main()
