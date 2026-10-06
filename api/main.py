"""
FastAPI inference service for next-day AQI prediction.

Endpoints:
  GET  /health       — health check
  GET  /model-info    — model metadata, metrics, feature schema
  POST /predict       — predict next-day AQI from features

Usage:
    uvicorn api.main:app --host 0.0.0.0 --port 8000
"""
import os
import sys
from typing import Optional

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

# Ensure project root is on the path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from ml.predict import load_models, predict, get_feature_importance, get_model_info
from ml.features import FEATURE_COLUMNS

app = FastAPI(
    title="Air Quality AQI Prediction API",
    description="Next-day AQI prediction service (Part 2 MLOps)",
    version="1.0.0",
)


# ---- Models ----

class PredictionRequest(BaseModel):
    """Request body for the /predict endpoint."""
    avg_pm25: float = Field(..., description="Daily average PM2.5 (ug/m3)")
    avg_pm10: float = Field(..., description="Daily average PM10 (ug/m3)")
    avg_no2: float = Field(..., description="Daily average NO2 (ug/m3)")
    avg_so2: float = Field(..., description="Daily average SO2 (ug/m3)")
    avg_co: float = Field(..., description="Daily average CO (mg/m3)")
    avg_o3: float = Field(..., description="Daily average O3 (ug/m3)")
    avg_temperature: Optional[float] = Field(None, description="Daily average temperature (C)")
    avg_humidity: Optional[float] = Field(None, description="Daily average humidity (%)")
    avg_rainfall: Optional[float] = Field(None, description="Daily average precipitation (mm)")
    avg_wind_speed: Optional[float] = Field(None, description="Daily average wind speed (km/h)")
    day: int = Field(..., ge=1, le=31, description="Day of month")
    day_of_week: int = Field(..., ge=0, le=6, description="Day of week (0=Monday)")
    month: int = Field(..., ge=1, le=12, description="Month number")
    aqi_lag_1: Optional[float] = Field(None, description="AQI from 1 day ago")
    aqi_lag_2: Optional[float] = Field(None, description="AQI from 2 days ago")
    aqi_lag_3: Optional[float] = Field(None, description="AQI from 3 days ago")
    aqi_roll_mean_3: Optional[float] = Field(None, description="3-day rolling mean AQI")
    aqi_roll_mean_7: Optional[float] = Field(None, description="7-day rolling mean AQI")
    pm25_lag_1: Optional[float] = Field(None, description="PM2.5 from 1 day ago")
    pm10_lag_1: Optional[float] = Field(None, description="PM10 from 1 day ago")
    no2_lag_1: Optional[float] = Field(None, description="NO2 from 1 day ago")
    so2_lag_1: Optional[float] = Field(None, description="SO2 from 1 day ago")
    co_lag_1: Optional[float] = Field(None, description="CO from 1 day ago")
    o3_lag_1: Optional[float] = Field(None, description="O3 from 1 day ago")


class PredictionResponse(BaseModel):
    """Response from the /predict endpoint."""
    predicted_aqi: int
    predicted_aqi_category: str
    regression_model: str
    classification_model: str
    trained_at: str


# ---- Endpoints ----

@app.get("/health")
def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "service": "air-quality-prediction"}


@app.get("/model-info")
def model_info():
    """Return metadata about the loaded models."""
    import math
    info = get_model_info()
    if info is None:
        raise HTTPException(status_code=503, detail="Models not trained. Run 'python -m ml.train' first.")

    def _sanitize(obj):
        if isinstance(obj, float) and (math.isnan(obj) or math.isinf(obj)):
            return 0.0
        if isinstance(obj, dict):
            return {k: _sanitize(v) for k, v in obj.items()}
        if isinstance(obj, list):
            return [_sanitize(v) for v in obj]
        return obj

    return _sanitize(info)


@app.get("/feature-importance")
def feature_importance():
    """Return feature importance from the tree-based classification model."""
    try:
        reg_model, clf_model, feature_cols, metadata = load_models()
    except FileNotFoundError as e:
        raise HTTPException(status_code=503, detail=str(e))

    importance = get_feature_importance(clf_model, feature_cols)
    return {"feature_importance": importance, "model": metadata.get("classification_model", "unknown")}


@app.post("/predict", response_model=PredictionResponse)
def predict_aqi(request: PredictionRequest):
    """Predict next-day AQI and AQI category from input features."""
    try:
        reg_model, clf_model, feature_cols, metadata = load_models()
    except FileNotFoundError as e:
        raise HTTPException(status_code=503, detail=str(e))

    # Convert request to dict
    input_data = request.model_dump()

    result = predict(
        input_data=input_data,
        reg_model=reg_model,
        clf_model=clf_model,
        feature_cols=feature_cols,
        metadata=metadata,
    )

    return PredictionResponse(
        predicted_aqi=result["predicted_aqi"],
        predicted_aqi_category=result["predicted_aqi_category"],
        regression_model=result["regression_model"],
        classification_model=result["classification_model"],
        trained_at=result["trained_at"],
    )
