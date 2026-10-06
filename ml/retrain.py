"""
Retraining workflow — triggered when monitoring detects significant drift.

Steps:
  1. Fetch latest data from the gold table
  2. Rebuild features
  3. Retrain regression and classification models
  4. Evaluate against the test set
  5. Log the run to MLflow
  6. Save the improved model only if it meets configured performance criteria
     (does NOT overwrite a better production model with a worse one)

Usage:
    python -m ml.retrain
"""
import json
import os
import sys
from datetime import datetime, timezone

import joblib
import mlflow
import mlflow.sklearn

from ml.features import (
    fetch_gold_data,
    build_feature_frame,
    prepare_train_test,
    save_feature_schema,
    FEATURE_COLUMNS,
)
from ml.evaluate import evaluate_regression, evaluate_classification
from ml.train import (
    train_regression_models,
    train_classification_models,
    save_model,
    save_metrics,
    REG_EXPERIMENT,
    CLF_EXPERIMENT,
    MODELS_DIR,
    REG_DIR,
    CLF_DIR,
)

# Performance criteria for promoting a retrained model
REGRESSION_IMPROVEMENT_THRESHOLD = 0.0  # New R2 must be >= old R2 + this threshold
CLASSIFICATION_IMPROVEMENT_THRESHOLD = 0.0  # New F1 must be >= old F1 + this threshold


def load_current_metrics():
    """Load the current production model metrics."""
    reg_metrics_path = os.path.join(REG_DIR, "metrics.json")
    clf_metrics_path = os.path.join(CLF_DIR, "metrics.json")

    reg_metrics = None
    clf_metrics = None

    if os.path.exists(reg_metrics_path):
        with open(reg_metrics_path) as f:
            reg_metrics = json.load(f)
    if os.path.exists(clf_metrics_path):
        with open(clf_metrics_path) as f:
            clf_metrics = json.load(f)

    return reg_metrics, clf_metrics


def main():
    print("=" * 60)
    print("  ML RETRAINING WORKFLOW")
    print("=" * 60)

    # Load current production model metrics for comparison
    current_reg_metrics, current_clf_metrics = load_current_metrics()

    if current_reg_metrics:
        print(f"\n  Current regression R2: {current_reg_metrics.get('r2', 'N/A')}")
    if current_clf_metrics:
        print(f"  Current classification F1: {current_clf_metrics.get('f1_macro', 'N/A')}")

    # 1. Fetch latest data
    print("\n--- Step 1: Fetch latest data ---")
    rows = fetch_gold_data()
    print(f"  Fetched {len(rows)} gold records")

    if len(rows) < 5:
        print("  ERROR: Not enough data to retrain.")
        sys.exit(1)

    # 2. Build features
    print("\n--- Step 2: Build features ---")
    df, feature_cols = build_feature_frame(rows)
    print(f"  Feature frame: {len(df)} rows, {len(feature_cols)} features")

    if len(df) < 3:
        print("  ERROR: Not enough rows with targets.")
        sys.exit(1)

    # 3. Train/test split
    print("\n--- Step 3: Time-aware split ---")
    X_train, y_train_reg, y_train_clf, X_test, y_test_reg, y_test_clf = prepare_train_test(
        df, feature_cols, test_size=0.3
    )
    print(f"  Train: {len(X_train)} | Test: {len(X_test)}")

    if len(X_test) == 0:
        X_test, y_test_reg, y_test_clf = X_train, y_train_reg, y_train_clf

    labels = sorted(set(list(y_train_clf) + list(y_test_clf)))

    # 4. Set up MLflow
    mlflow.set_experiment(REG_EXPERIMENT)
    mlflow.set_experiment(CLF_EXPERIMENT)

    # 5. Retrain
    print("\n--- Step 4: Retrain models ---")
    new_reg_model, new_reg_metrics, new_reg_name = train_regression_models(
        X_train, y_train_reg, X_test, y_test_reg
    )
    new_clf_model, new_clf_metrics, new_clf_name = train_classification_models(
        X_train, y_train_clf, X_test, y_test_clf, labels=labels
    )

    # 6. Compare with current production models
    print("\n--- Step 5: Compare with production models ---")

    reg_promoted = False
    clf_promoted = False

    if current_reg_metrics is not None:
        old_r2 = current_reg_metrics.get("r2", -999)
        new_r2 = new_reg_metrics["r2"]
        if new_r2 >= old_r2 + REGRESSION_IMPROVEMENT_THRESHOLD:
            print(f"  Regression: new R2={new_r2} >= old R2={old_r2} — PROMOTING")
            reg_promoted = True
        else:
            print(f"  Regression: new R2={new_r2} < old R2={old_r2} — KEEPING CURRENT MODEL")
    else:
        print("  Regression: no current model — promoting new model")
        reg_promoted = True

    if current_clf_metrics is not None:
        old_f1 = current_clf_metrics.get("f1_macro", -999)
        new_f1 = new_clf_metrics["f1_macro"]
        if new_f1 >= old_f1 + CLASSIFICATION_IMPROVEMENT_THRESHOLD:
            print(f"  Classification: new F1={new_f1} >= old F1={old_f1} — PROMOTING")
            clf_promoted = True
        else:
            print(f"  Classification: new F1={new_f1} < old F1={old_f1} — KEEPING CURRENT MODEL")
    else:
        print("  Classification: no current model — promoting new model")
        clf_promoted = True

    # 7. Save promoted models
    print("\n--- Step 6: Save models ---")
    if reg_promoted:
        save_feature_schema(feature_cols, os.path.join(MODELS_DIR, "feature_schema.json"))
        save_model(new_reg_model, os.path.join(REG_DIR, "model.joblib"))
        save_metrics(new_reg_metrics, os.path.join(REG_DIR, "metrics.json"))
    else:
        print("  Regression model NOT saved (current model is better)")

    if clf_promoted:
        save_model(new_clf_model, os.path.join(CLF_DIR, "model.joblib"))
        save_metrics(new_clf_metrics, os.path.join(CLF_DIR, "metrics.json"))
    else:
        print("  Classification model NOT saved (current model is better)")

    # Update metadata
    metadata = {
        "trained_at": datetime.now(timezone.utc).isoformat(),
        "regression_model": new_reg_name if reg_promoted else "unchanged",
        "classification_model": new_clf_name if clf_promoted else "unchanged",
        "n_train": len(X_train),
        "n_test": len(X_test),
        "regression_metrics": new_reg_metrics,
        "classification_metrics": new_clf_metrics,
        "regression_promoted": reg_promoted,
        "classification_promoted": clf_promoted,
        "feature_columns": feature_cols,
        "labels": labels,
    }
    meta_path = os.path.join(MODELS_DIR, "model_metadata.json")
    with open(meta_path, "w") as f:
        json.dump(metadata, f, indent=2, default=str)
    print(f"  Updated metadata at {meta_path}")

    # Update reference features for monitoring
    train_ref_path = os.path.join(MODELS_DIR, "reference_features.csv")
    df[feature_cols].to_csv(train_ref_path, index=False)
    print(f"  Updated reference features at {train_ref_path}")

    print("\n" + "=" * 60)
    print("  RETRAINING COMPLETE")
    print(f"  Regression promoted: {reg_promoted}")
    print(f"  Classification promoted: {clf_promoted}")
    print("=" * 60)

    return metadata


if __name__ == "__main__":
    main()
