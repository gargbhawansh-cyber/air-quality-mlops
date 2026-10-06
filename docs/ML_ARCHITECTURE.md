# ML Architecture (Part 2)

## Overview

Part 2 extends the Part 1 data pipeline with Machine Learning for next-day AQI prediction. It adds feature engineering, model training, MLflow tracking, a FastAPI inference service, Docker containerization, monitoring/drift detection, and a retraining workflow.

## ML Pipeline Diagram

```
Part 1 Gold Table (gold_air_quality_daily)
         |
         v
    Feature Engineering (ml/features.py)
    - Air-quality features: PM2.5, PM10, NO2, SO2, CO, O3
    - Weather features: temperature, humidity, precipitation, wind speed
    - Temporal features: day, day_of_week, month
    - Lag features: AQI lag 1/2/3 days, pollutant lag 1 day
    - Rolling features: 3-day and 7-day rolling means
    - Target: next_day_aqi, next_day_aqi_category
         |
         v
    Time-aware Train/Test Split (ml/features.py)
    - Chronological split (no shuffling)
    - Latest 30% of dates = test set
         |
         +--------+--------+
         |                 |
         v                 v
  Regression Models    Classification Models
  (ml/train.py)        (ml/train.py)
  - Linear Regression  - Logistic Regression
  - Random Forest      - Random Forest Classifier
         |                 |
         v                 v
  Evaluation           Evaluation
  (ml/evaluate.py)     (ml/evaluate.py)
  - MAE, RMSE, R2       - Accuracy, Precision, Recall, F1
         |                 |
         v                 v
  MLflow Logging       MLflow Logging
  (air-quality-        (air-quality-
   regression)           classification)
         |                 |
         v                 v
  Best Model Saved      Best Model Saved
  models/regression/    models/classification/
  model.joblib          model.joblib
  + metrics.json        + metrics.json
  + feature_schema.json
  + model_metadata.json
  + reference_features.csv
         |
         v
  FastAPI Inference (api/main.py)
  GET /health, GET /model-info, POST /predict
         |
         v
  Monitoring (ml/monitor.py)
  - PSI drift detection
  - Missing value checks
  - Drift report → monitoring/drift_report.json
         |
         v
  Retraining (ml/retrain.py)
  - Triggered when drift detected
  - Retrains, evaluates, compares
  - Promotes only if new model >= current model
```

## Data Leakage Prevention

- Features for date T use only data from T and earlier.
- The target (next_day_aqi) is T+1's AQI, created by shifting AQI forward by 1 row per station.
- Lag features (aqi_lag_1, aqi_lag_2, aqi_lag_3) are computed on the AQI series BEFORE the target shift, so they never reference the target row.
- Rolling means use a window of past days up to and including the current day — never the future target day.
- Train/test split is chronological: the latest 30% of dates form the test set. No random shuffling.

## AQI Calculation

The AQI calculation reuses Part 1's CPCB sub-index methodology from `pipeline/aggregate.py`. The `get_aqi_category()` function maps AQI values to categories:

| AQI Range | Category |
|-----------|----------|
| 0-50 | Good |
| 51-100 | Satisfactory |
| 101-150 | Moderate |
| 151-200 | Poor |
| 201-250 | Very Poor |
| 251-500 | Severe |

The classification target (`next_day_aqi_category`) is derived from the regression target (`next_day_aqi`) using this same function, ensuring consistency.

## Model Comparison

### Regression
| Model | MAE | RMSE | R2 |
|-------|-----|------|----|
| Linear Regression | Computed at train time | Computed at train time | Computed at train time |
| Random Forest Regressor | Computed at train time | Computed at train time | Computed at train time |

Best model selected by highest R2.

### Classification
| Model | Accuracy | Precision | Recall | F1 |
|-------|----------|-----------|--------|----|
| Logistic Regression | Computed at train time | Computed at train time | Computed at train time | Computed at train time |
| Random Forest Classifier | Computed at train time | Computed at train time | Computed at train time | Computed at train time |

Best model selected by highest F1 (macro).

Metrics are logged to MLflow and saved to `models/regression/metrics.json` and `models/classification/metrics.json`.

## MLflow Tracking

Two experiments:
- `air-quality-regression` — logs MAE, RMSE, R2 for each model
- `air-quality-classification` — logs Accuracy, Precision, Recall, F1 for each model

Each run logs:
- Model name and hyperparameters
- Training/test dataset sizes
- Feature list
- All evaluation metrics
- The model itself as an MLflow artifact

Start MLflow UI:
```bash
mlflow ui --host 0.0.0.0 --port 5000
```

## FastAPI Inference

The API loads saved models at startup and serves predictions without retraining.

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/health` | GET | Health check |
| `/model-info` | GET | Model metadata, metrics, feature schema |
| `/feature-importance` | GET | Feature importance from tree-based model |
| `/predict` | POST | Predict next-day AQI from features |

Request validation is handled by Pydantic models.

## Docker

The Dockerfile builds an image that:
1. Installs Python dependencies
2. Copies the project code and saved models
3. Starts the FastAPI service on port 8000

```bash
docker build -t air-quality-api .
docker run -p 8000:8000 air-quality-api
```

## Monitoring / Drift Detection

The monitoring module (`ml/monitor.py`) uses Population Stability Index (PSI) to detect drift:

| PSI Value | Status |
|-----------|--------|
| < 0.1 | No drift |
| 0.1 - 0.25 | Moderate drift — monitor |
| >= 0.25 | Significant drift — RETRAINING RECOMMENDED |

The report includes:
- Per-feature PSI score and drift status
- Missing value percentages for reference and current data
- Overall status (HEALTHY / MODERATE DRIFT / RETRAINING RECOMMENDED)

Reports are saved to `monitoring/drift_report.json`.

## Retraining Workflow

The retraining script (`ml/retrain.py`):
1. Fetches the latest gold table data
2. Rebuilds features
3. Retrains all models
4. Evaluates against the test set
5. Logs to MLflow
6. Compares new metrics with current production model metrics
7. Promotes the new model only if it meets or exceeds the current model's performance

This ensures a worse model never replaces a better production model.
