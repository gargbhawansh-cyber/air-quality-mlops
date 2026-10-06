"""
Evaluation metrics for regression and classification models.

Regression: MAE, RMSE, R2
Classification: Accuracy, Precision (macro), Recall (macro), F1 (macro), Confusion matrix
"""
import numpy as np
from sklearn.metrics import (
    mean_absolute_error,
    mean_squared_error,
    r2_score,
    accuracy_score,
    precision_score,
    recall_score,
    f1_score,
    confusion_matrix,
    classification_report,
)


def _safe_round(val, digits=4):
    """Round a value, converting NaN/inf to 0.0 for JSON safety."""
    try:
        v = float(val)
        if np.isnan(v) or np.isinf(v):
            return 0.0
        return round(v, digits)
    except (TypeError, ValueError):
        return 0.0


def evaluate_regression(y_true, y_pred):
    """Return a dict of regression metrics."""
    mae = mean_absolute_error(y_true, y_pred)
    rmse = float(np.sqrt(mean_squared_error(y_true, y_pred)))
    r2 = r2_score(y_true, y_pred)
    return {"mae": _safe_round(mae), "rmse": _safe_round(rmse), "r2": _safe_round(r2)}


def evaluate_classification(y_true, y_pred, labels=None):
    """Return a dict of classification metrics + confusion matrix."""
    metrics = {
        "accuracy": round(accuracy_score(y_true, y_pred), 4),
        "precision_macro": round(precision_score(y_true, y_pred, average="macro", zero_division=0), 4),
        "recall_macro": round(recall_score(y_true, y_pred, average="macro", zero_division=0), 4),
        "f1_macro": round(f1_score(y_true, y_pred, average="macro", zero_division=0), 4),
    }

    if labels is not None:
        cm = confusion_matrix(y_true, y_pred, labels=labels)
        metrics["confusion_matrix"] = cm.tolist()
        metrics["labels"] = list(labels)
        metrics["classification_report"] = classification_report(
            y_true, y_pred, labels=labels, zero_division=0, output_dict=True
        )
    else:
        cm = confusion_matrix(y_true, y_pred)
        metrics["confusion_matrix"] = cm.tolist()
        metrics["labels"] = sorted(set(list(y_true) + list(y_pred)))
        metrics["classification_report"] = classification_report(
            y_true, y_pred, zero_division=0, output_dict=True
        )

    return metrics


def print_regression_report(model_name, metrics):
    """Print a formatted regression metrics report."""
    print(f"\n  [{model_name}] Regression Metrics:")
    print(f"    MAE:  {metrics['mae']}")
    print(f"    RMSE: {metrics['rmse']}")
    print(f"    R2:   {metrics['r2']}")


def print_classification_report(model_name, metrics):
    """Print a formatted classification metrics report."""
    print(f"\n  [{model_name}] Classification Metrics:")
    print(f"    Accuracy:  {metrics['accuracy']}")
    print(f"    Precision: {metrics['precision_macro']}")
    print(f"    Recall:    {metrics['recall_macro']}")
    print(f"    F1:        {metrics['f1_macro']}")
    if "labels" in metrics:
        print(f"    Labels:    {metrics['labels']}")
