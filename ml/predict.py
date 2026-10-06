"""
Prediction module — loads saved models and provides inference functions.

Used by the FastAPI service and the Streamlit dashboard.
"""
import json
import os
from datetime import datetime, timezone

import joblib
import numpy as np
import pandas as pd

from config import PROJECT_ROOT
from pipeline.aggregate import get_aqi_category

MODELS_DIR = PROJECT_ROOT / "models"
REG_MODEL_PATH = MODELS_DIR / "regression" / "model.joblib"
CLF_MODEL_PATH = MODELS_DIR / "classification" / "model.joblib"
SCHEMA_PATH = MODELS_DIR / "feature_schema.json"
METADATA_PATH = MODELS_DIR / "model_metadata.json"


def load_models():
    """Load the saved regression and classification models + feature schema."""
    if not REG_MODEL_PATH.exists() or not CLF_MODEL_PATH.exists():
        raise FileNotFoundError(
            "Models not found. Run 'python -m ml.train' to train models first."
        )

    reg_model = joblib.load(str(REG_MODEL_PATH))
    clf_model = joblib.load(str(CLF_MODEL_PATH))

    with open(str(SCHEMA_PATH)) as f:
        schema = json.load(f)
    feature_cols = schema["feature_columns"]

    with open(str(METADATA_PATH)) as f:
        metadata = json.load(f)

    return reg_model, clf_model, feature_cols, metadata


def predict(input_data, reg_model=None, clf_model=None, feature_cols=None, metadata=None):
    """
    Make a prediction from a feature dictionary or DataFrame row.

    input_data must contain all feature columns. Missing keys are filled with NaN.

    Returns dict with:
      - predicted_aqi
      - predicted_aqi_category
      - regression_model
      - classification_model
      - trained_at
    """
    if reg_model is None or clf_model is None or feature_cols is None:
        reg_model, clf_model, feature_cols, metadata = load_models()

    # Build feature vector in the correct order
    row = {}
    for col in feature_cols:
        row[col] = input_data.get(col, np.nan)

    X = pd.DataFrame([row], columns=feature_cols)

    predicted_aqi = float(reg_model.predict(X)[0])
    predicted_aqi = max(0, min(500, round(predicted_aqi)))

    predicted_category = clf_model.predict(X)[0]

    # Fallback: derive category from AQI if classifier gives unexpected result
    if predicted_category not in ["Good", "Satisfactory", "Moderate", "Poor", "Very Poor", "Severe"]:
        predicted_category = get_aqi_category(predicted_aqi)

    return {
        "predicted_aqi": predicted_aqi,
        "predicted_aqi_category": predicted_category,
        "regression_model": metadata.get("regression_model", "unknown"),
        "classification_model": metadata.get("classification_model", "unknown"),
        "trained_at": metadata.get("trained_at", "unknown"),
    }


def predict_batch(df, feature_cols, reg_model, clf_model, metadata=None):
    """
    Make predictions for a DataFrame of features.
    Returns a DataFrame with predicted_aqi and predicted_aqi_category columns.
    """
    X = df[feature_cols].copy()

    aqi_preds = reg_model.predict(X)
    aqi_preds = np.clip(aqi_preds, 0, 500).round().astype(int)

    cat_preds = clf_model.predict(X)

    results = pd.DataFrame({
        "predicted_aqi": aqi_preds,
        "predicted_aqi_category": cat_preds,
    })

    return results


def get_feature_importance(model, feature_cols):
    """
    Extract feature importance from a tree-based model (Random Forest).
    Returns a list of (feature, importance) sorted descending.
    """
    # The model is a Pipeline: imputer -> scaler -> model
    try:
        rf = model.named_steps["model"]
        if hasattr(rf, "feature_importances_"):
            importances = rf.feature_importances_
            pairs = sorted(zip(feature_cols, importances), key=lambda x: x[1], reverse=True)
            return [{"feature": f, "importance": round(float(i), 4)} for f, i in pairs]
    except (AttributeError, KeyError):
        pass
    return []


def get_model_info():
    """Return metadata about the currently saved models."""
    if not METADATA_PATH.exists():
        return None
    with open(str(METADATA_PATH)) as f:
        return json.load(f)
