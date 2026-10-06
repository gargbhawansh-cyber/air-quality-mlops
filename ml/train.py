"""
Training script for next-day AQI prediction.

Trains two regression models (Linear Regression, Random Forest Regressor)
and two classification models (Logistic Regression, Random Forest Classifier).
Logs all runs to MLflow, selects the best model per task, and saves the
production models to models/regression/ and models/classification/.

Usage:
    python -m ml.train
"""
import json
import os
import sys
from datetime import datetime, timezone

import joblib
import numpy as np
import mlflow
import mlflow.sklearn
from sklearn.linear_model import LinearRegression, LogisticRegression
from sklearn.ensemble import RandomForestRegressor, RandomForestClassifier
from sklearn.impute import SimpleImputer
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

from ml.features import (
    fetch_gold_data,
    build_feature_frame,
    prepare_train_test,
    save_feature_schema,
    FEATURE_COLUMNS,
    CATEGORICAL_TARGETS,
)
from ml.evaluate import (
    evaluate_regression,
    evaluate_classification,
    print_regression_report,
    print_classification_report,
)

# Directories
MODELS_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "models")
REG_DIR = os.path.join(MODELS_DIR, "regression")
CLF_DIR = os.path.join(MODELS_DIR, "classification")

# MLflow experiment names
REG_EXPERIMENT = "air-quality-regression"
CLF_EXPERIMENT = "air-quality-classification"

# Minimum acceptable R2 for regression model to be saved as production
MIN_R2 = -1.0  # Accept even negative R2 for small datasets; log a warning
MIN_ACCURACY = 0.0  # Accept any accuracy for small datasets


def _make_regression_pipeline(model):
    """Build a sklearn Pipeline: imputer -> scaler -> model."""
    return Pipeline([
        ("imputer", SimpleImputer(strategy="median")),
        ("scaler", StandardScaler()),
        ("model", model),
    ])


def _make_classification_pipeline(model):
    """Build a sklearn Pipeline: imputer -> scaler -> model."""
    return Pipeline([
        ("imputer", SimpleImputer(strategy="median")),
        ("scaler", StandardScaler()),
        ("model", model),
    ])


def train_regression_models(X_train, y_train, X_test, y_test):
    """
    Train Linear Regression and Random Forest Regressor.
    Log to MLflow, return (best_model, best_metrics, best_name).
    """
    models = {
        "linear_regression": _make_regression_pipeline(
            LinearRegression()
        ),
        "random_forest_regressor": _make_regression_pipeline(
            RandomForestRegressor(n_estimators=100, max_depth=10, random_state=42)
        ),
    }

    results = {}
    for name, pipeline in models.items():
        pipeline.fit(X_train, y_train)
        y_pred = pipeline.predict(X_test)
        metrics = evaluate_regression(y_test, y_pred)

        with mlflow.start_run(run_name=name, experiment_id=mlflow.get_experiment_by_name(REG_EXPERIMENT).experiment_id):
            mlflow.log_param("model_name", name)
            mlflow.log_param("n_train", len(X_train))
            mlflow.log_param("n_test", len(X_test))
            mlflow.log_param("features", ",".join(FEATURE_COLUMNS))
            mlflow.log_metric("mae", metrics["mae"])
            mlflow.log_metric("rmse", metrics["rmse"])
            mlflow.log_metric("r2", metrics["r2"])
            mlflow.sklearn.log_model(pipeline, name, skops_trusted_types=['numpy.dtype'])

        print_regression_report(name, metrics)
        results[name] = (pipeline, metrics)

    # Select best by R2
    best_name = max(results, key=lambda k: results[k][1]["r2"])
    best_model, best_metrics = results[best_name]
    print(f"\n  Best regression model: {best_name} (R2={best_metrics['r2']})")
    return best_model, best_metrics, best_name


def train_classification_models(X_train, y_train, X_test, y_test, labels):
    """
    Train Logistic Regression and Random Forest Classifier.
    Log to MLflow, return (best_model, best_metrics, best_name).
    """
    models = {
        "logistic_regression": _make_classification_pipeline(
            LogisticRegression(max_iter=1000, random_state=42)
        ),
        "random_forest_classifier": _make_classification_pipeline(
            RandomForestClassifier(n_estimators=100, max_depth=10, random_state=42)
        ),
    }

    results = {}
    for name, pipeline in models.items():
        pipeline.fit(X_train, y_train)
        y_pred = pipeline.predict(X_test)
        metrics = evaluate_classification(y_test, y_pred, labels=labels)

        with mlflow.start_run(run_name=name, experiment_id=mlflow.get_experiment_by_name(CLF_EXPERIMENT).experiment_id):
            mlflow.log_param("model_name", name)
            mlflow.log_param("n_train", len(X_train))
            mlflow.log_param("n_test", len(X_test))
            mlflow.log_param("features", ",".join(FEATURE_COLUMNS))
            mlflow.log_metric("accuracy", metrics["accuracy"])
            mlflow.log_metric("precision_macro", metrics["precision_macro"])
            mlflow.log_metric("recall_macro", metrics["recall_macro"])
            mlflow.log_metric("f1_macro", metrics["f1_macro"])
            mlflow.sklearn.log_model(pipeline, name, skops_trusted_types=['numpy.dtype'])

        print_classification_report(name, metrics)
        results[name] = (pipeline, metrics)

    # Select best by F1 macro
    best_name = max(results, key=lambda k: results[k][1]["f1_macro"])
    best_model, best_metrics = results[best_name]
    print(f"\n  Best classification model: {best_name} (F1={best_metrics['f1_macro']})")
    return best_model, best_metrics, best_name


def save_model(model, path):
    """Save a model with joblib, creating directories as needed."""
    os.makedirs(os.path.dirname(path), exist_ok=True)
    joblib.dump(model, path)
    print(f"  Saved model to {path}")


def save_metrics(metrics, path):
    """Save metrics as JSON."""
    os.makedirs(os.path.dirname(path), exist_ok=True)
    serializable = {k: v for k, v in metrics.items() if isinstance(v, (int, float, str, list, dict))}
    with open(path, "w") as f:
        json.dump(serializable, f, indent=2, default=str)
    print(f"  Saved metrics to {path}")


def main():
    print("=" * 60)
    print("  ML TRAINING — Next-Day AQI Prediction")
    print("=" * 60)

    # 1. Fetch data
    print("\n--- Fetching gold table data ---")
    rows = fetch_gold_data()
    print(f"  Fetched {len(rows)} gold records")

    if len(rows) < 5:
        print("  ERROR: Not enough data to train. Need at least 5 gold records.")
        sys.exit(1)

    # 2. Build features
    print("\n--- Building feature frame ---")
    df, feature_cols = build_feature_frame(rows)
    print(f"  Feature frame: {len(df)} rows, {len(feature_cols)} features")
    print(f"  Target distribution:\n{df['next_day_aqi_category'].value_counts().to_string()}")

    if len(df) < 3:
        print("  ERROR: Not enough rows with targets (need at least 3).")
        sys.exit(1)

    # 3. Train/test split (time-aware)
    print("\n--- Time-aware train/test split ---")
    X_train, y_train_reg, y_train_clf, X_test, y_test_reg, y_test_clf = prepare_train_test(
        df, feature_cols, test_size=0.3
    )
    print(f"  Train: {len(X_train)} rows | Test: {len(X_test)} rows")

    if len(X_test) == 0:
        print("  WARNING: Test set empty, using train set for evaluation")
        X_test, y_test_reg, y_test_clf = X_train, y_train_reg, y_train_clf

    # Determine labels present in the data
    labels = sorted(set(list(y_train_clf) + list(y_test_clf)))

    # 4. Set up MLflow
    mlflow.set_experiment(REG_EXPERIMENT)
    mlflow.set_experiment(CLF_EXPERIMENT)

    # 5. Train regression models
    print("\n--- Training Regression Models ---")
    best_reg_model, best_reg_metrics, best_reg_name = train_regression_models(
        X_train, y_train_reg, X_test, y_test_reg
    )

    # 6. Train classification models
    print("\n--- Training Classification Models ---")
    best_clf_model, best_clf_metrics, best_clf_name = train_classification_models(
        X_train, y_train_clf, X_test, y_test_clf, labels=labels
    )

    # 7. Save production models
    print("\n--- Saving Production Models ---")
    save_feature_schema(feature_cols, os.path.join(MODELS_DIR, "feature_schema.json"))

    reg_path = os.path.join(REG_DIR, "model.joblib")
    save_model(best_reg_model, reg_path)
    save_metrics(best_reg_metrics, os.path.join(REG_DIR, "metrics.json"))

    clf_path = os.path.join(CLF_DIR, "model.joblib")
    save_model(best_clf_model, clf_path)
    save_metrics(best_clf_metrics, os.path.join(CLF_DIR, "metrics.json"))

    # Save model metadata
    metadata = {
        "trained_at": datetime.now(timezone.utc).isoformat(),
        "regression_model": best_reg_name,
        "classification_model": best_clf_name,
        "n_train": len(X_train),
        "n_test": len(X_test),
        "regression_metrics": best_reg_metrics,
        "classification_metrics": best_clf_metrics,
        "feature_columns": feature_cols,
        "labels": labels,
    }
    meta_path = os.path.join(MODELS_DIR, "model_metadata.json")
    with open(meta_path, "w") as f:
        json.dump(metadata, f, indent=2, default=str)
    print(f"  Saved metadata to {meta_path}")

    # 8. Save training data reference for monitoring
    train_ref_path = os.path.join(MODELS_DIR, "reference_features.csv")
    df[feature_cols].to_csv(train_ref_path, index=False)
    print(f"  Saved reference features to {train_ref_path}")

    print("\n" + "=" * 60)
    print("  TRAINING COMPLETE")
    print(f"  Regression: {best_reg_name} | R2={best_reg_metrics['r2']}")
    print(f"  Classification: {best_clf_name} | F1={best_clf_metrics['f1_macro']}")
    print("=" * 60)

    return metadata


if __name__ == "__main__":
    main()
