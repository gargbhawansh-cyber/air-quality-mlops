"""
Monitoring and drift detection module.

Monitors:
  - Input feature distributions
  - Missing values
  - Prediction distribution
  - Data drift between training/reference data and new data (using PSI)

PSI (Population Stability Index):
  PSI < 0.1   — no significant drift
  0.1 <= PSI < 0.25 — moderate drift (monitor)
  PSI >= 0.25 — significant drift (RETRAINING RECOMMENDED)
"""
import json
import os
from datetime import datetime, timezone

import numpy as np
import pandas as pd

from config import PROJECT_ROOT

MODELS_DIR = PROJECT_ROOT / "models"
REFERENCE_PATH = MODELS_DIR / "reference_features.csv"
METADATA_PATH = MODELS_DIR / "model_metadata.json"
MONITORING_DIR = PROJECT_ROOT / "monitoring"

# PSI thresholds
PSI_NO_DRIFT = 0.1
PSI_MODERATE_DRIFT = 0.25

# Number of bins for PSI calculation
N_BINS = 10


def calculate_psi(reference, current, bins="auto"):
    """
    Calculate Population Stability Index (PSI) for a single feature.

    PSI = sum( (p_current - p_reference) * ln(p_current / p_reference) )

    Args:
        reference: array-like, reference distribution (training data)
        current: array-like, current distribution (new data)
        bins: number of bins or binning strategy

    Returns:
        float: PSI value
    """
    reference = np.array(reference, dtype=float)
    current = np.array(current, dtype=float)

    # Remove NaN/inf
    reference = reference[np.isfinite(reference)]
    current = current[np.isfinite(current)]

    if len(reference) == 0 or len(current) == 0:
        return 0.0

    # Determine bin edges from reference distribution
    try:
        if bins == "auto":
            edges = np.histogram_bin_edges(reference, bins=N_BINS)
        else:
            edges = np.linspace(reference.min(), reference.max(), bins + 1)
    except Exception:
        return 0.0

    if len(edges) < 3:
        return 0.0

    # Compute proportions in each bin
    ref_counts, _ = np.histogram(reference, bins=edges)
    cur_counts, _ = np.histogram(current, bins=edges)

    ref_props = ref_counts / len(reference)
    cur_props = cur_counts / len(current)

    # Avoid division by zero — add small epsilon
    epsilon = 1e-6
    ref_props = np.clip(ref_props, epsilon, None)
    cur_props = np.clip(cur_props, epsilon, None)

    psi = np.sum((cur_props - ref_props) * np.log(cur_props / ref_props))
    return float(psi)


def check_missing_values(df):
    """Check for missing values in each column of a DataFrame."""
    missing = {}
    for col in df.columns:
        n_missing = int(df[col].isna().sum())
        pct = round(n_missing / len(df) * 100, 2) if len(df) > 0 else 0.0
        missing[col] = {"count": n_missing, "percentage": pct}
    return missing


def get_drift_status(psi_value):
    """Return a human-readable drift status from a PSI value."""
    if psi_value < PSI_NO_DRIFT:
        return "no_drift"
    elif psi_value < PSI_MODERATE_DRIFT:
        return "moderate_drift"
    else:
        return "significant_drift"


def run_monitoring(current_data=None, current_path=None, output_path=None):
    """
    Run a full monitoring report comparing reference (training) data
    to current data.

    Args:
        current_data: DataFrame of current feature values. If None, loads from current_path.
        current_path: Path to a CSV file with current feature data.
        output_path: Where to save the monitoring report JSON.

    Returns:
        dict: The monitoring report.
    """
    print("=" * 60)
    print("  ML MONITORING — Drift Detection")
    print("=" * 60)

    # Load reference data
    if not REFERENCE_PATH.exists():
        print("  ERROR: Reference features not found. Train models first.")
        return {"error": "reference_features.csv not found"}

    reference_df = pd.read_csv(str(REFERENCE_PATH))
    print(f"  Reference data: {len(reference_df)} rows, {len(reference_df.columns)} features")

    # Load current data
    if current_data is not None:
        current_df = current_data
    elif current_path is not None:
        current_df = pd.read_csv(current_path)
    else:
        # Use the latest gold table data as current data
        from ml.features import fetch_gold_data, build_feature_frame
        rows = fetch_gold_data()
        df, feature_cols = build_feature_frame(rows)
        current_df = df[feature_cols] if not df.empty else reference_df.copy()

    print(f"  Current data: {len(current_df)} rows")

    # Align columns
    common_cols = [c for c in reference_df.columns if c in current_df.columns]
    reference_df = reference_df[common_cols]
    current_df = current_df[common_cols]

    # Check missing values
    ref_missing = check_missing_values(reference_df)
    cur_missing = check_missing_values(current_df)

    # Calculate PSI per feature
    feature_reports = []
    any_significant = False
    any_moderate = False

    for col in common_cols:
        ref_vals = reference_df[col].dropna()
        cur_vals = current_df[col].dropna()

        if len(ref_vals) == 0 or len(cur_vals) == 0:
            psi = 0.0
            status = "no_data"
        else:
            psi = calculate_psi(ref_vals, cur_vals)
            status = get_drift_status(psi)

        if status == "significant_drift":
            any_significant = True
        elif status == "moderate_drift":
            any_moderate = True

        feature_reports.append({
            "feature": col,
            "psi": round(psi, 4),
            "drift_status": status,
            "reference_missing_pct": ref_missing.get(col, {}).get("percentage", 0),
            "current_missing_pct": cur_missing.get(col, {}).get("percentage", 0),
        })

    # Overall status
    if any_significant:
        overall_status = "RETRAINING RECOMMENDED"
    elif any_moderate:
        overall_status = "MODERATE DRIFT — MONITOR"
    else:
        overall_status = "HEALTHY"

    report = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "reference_rows": len(reference_df),
        "current_rows": len(current_df),
        "features_checked": len(common_cols),
        "overall_status": overall_status,
        "feature_reports": feature_reports,
        "thresholds": {
            "no_drift": PSI_NO_DRIFT,
            "moderate_drift": PSI_MODERATE_DRIFT,
        },
    }

    # Print summary
    print(f"\n  Overall Status: {overall_status}")
    print(f"\n  {'Feature':<25} {'PSI':>8} {'Status':<20} {'Ref Miss%':>10} {'Cur Miss%':>10}")
    print("  " + "-" * 75)
    for fr in feature_reports:
        print(f"  {fr['feature']:<25} {fr['psi']:>8.4f} {fr['drift_status']:<20} "
              f"{fr['reference_missing_pct']:>10.1f} {fr['current_missing_pct']:>10.1f}")

    if any_significant:
        print("\n  *** RETRAINING RECOMMENDED ***")
        print("  Significant drift detected in one or more features.")
        print("  Run: python -m ml.retrain")

    # Save report
    if output_path is None:
        output_path = str(MONITORING_DIR / "drift_report.json")
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, "w") as f:
        json.dump(report, f, indent=2, default=str)
    print(f"\n  Report saved to {output_path}")

    return report


def main():
    """Run monitoring with default settings (latest gold table data as current)."""
    return run_monitoring()


if __name__ == "__main__":
    main()
