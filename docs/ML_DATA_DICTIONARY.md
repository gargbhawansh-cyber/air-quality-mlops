# ML Data Dictionary (Part 2)

## Feature Engineering

Features are derived from the `gold_air_quality_daily` table. Each row represents one day's data for one monitoring station.

### Air Quality Features

| Feature | Source Column | Type | Description |
|---------|---------------|------|-------------|
| avg_pm25 | gold_air_quality_daily.avg_pm25 | float | Daily average PM2.5 concentration (ug/m3) |
| avg_pm10 | gold_air_quality_daily.avg_pm10 | float | Daily average PM10 concentration (ug/m3) |
| avg_no2 | gold_air_quality_daily.avg_no2 | float | Daily average NO2 concentration (ug/m3) |
| avg_so2 | gold_air_quality_daily.avg_so2 | float | Daily average SO2 concentration (ug/m3) |
| avg_co | gold_air_quality_daily.avg_co | float | Daily average CO concentration (mg/m3) |
| avg_o3 | gold_air_quality_daily.avg_o3 | float | Daily average O3 concentration (ug/m3) |

### Weather Features

| Feature | Source Column | Type | Description |
|---------|---------------|------|-------------|
| avg_temperature | gold_air_quality_daily.avg_temperature | float | Daily average temperature (C) |
| avg_humidity | gold_air_quality_daily.avg_humidity | float | Daily average relative humidity (%) |
| avg_rainfall | gold_air_quality_daily.avg_rainfall | float | Daily average precipitation (mm) |
| avg_wind_speed | gold_air_quality_daily.avg_wind_speed | float | Daily average wind speed (km/h) |

### Temporal Features

| Feature | Type | Description |
|---------|------|-------------|
| day | int | Day of month (1-31) |
| day_of_week | int | Day of week (0=Monday, 6=Sunday) |
| month | int | Month number (1-12) |

### Lag Features

Lag features are computed per station (grouped by station_id) to avoid cross-station contamination.

| Feature | Type | Description |
|---------|------|-------------|
| aqi_lag_1 | float | AQI value from 1 day before the current date |
| aqi_lag_2 | float | AQI value from 2 days before the current date |
| aqi_lag_3 | float | AQI value from 3 days before the current date |
| pm25_lag_1 | float | PM2.5 from 1 day before |
| pm10_lag_1 | float | PM10 from 1 day before |
| no2_lag_1 | float | NO2 from 1 day before |
| so2_lag_1 | float | SO2 from 1 day before |
| co_lag_1 | float | CO from 1 day before |
| o3_lag_1 | float | O3 from 1 day before |

### Rolling Features

Rolling features are computed per station using a rolling window with min_periods=1.

| Feature | Type | Description |
|---------|------|-------------|
| aqi_roll_mean_3 | float | 3-day rolling mean of AQI (up to and including current day) |
| aqi_roll_mean_7 | float | 7-day rolling mean of AQI (up to and including current day) |

## Target Variables

| Target | Type | Description |
|--------|------|-------------|
| next_day_aqi | float | AQI value for the next day (T+1). Created by shifting AQI forward by 1 row per station. |
| next_day_aqi_category | string | AQI category for the next day, derived from next_day_aqi using CPCB breakpoints. |

## Feature Order

The feature schema is saved to `models/feature_schema.json` at training time and must match at inference time:

```
avg_pm25, avg_pm10, avg_no2, avg_so2, avg_co, avg_o3,
avg_temperature, avg_humidity, avg_rainfall, avg_wind_speed,
day, day_of_week, month,
aqi_lag_1, aqi_lag_2, aqi_lag_3,
aqi_roll_mean_3, aqi_roll_mean_7,
pm25_lag_1, pm10_lag_1, no2_lag_1, so2_lag_1, co_lag_1, o3_lag_1
```

## Model Artifacts

| File | Location | Description |
|------|----------|-------------|
| model.joblib | models/regression/ | Best regression model (joblib serialized) |
| model.joblib | models/classification/ | Best classification model (joblib serialized) |
| metrics.json | models/regression/ | Regression evaluation metrics (MAE, RMSE, R2) |
| metrics.json | models/classification/ | Classification evaluation metrics (Accuracy, Precision, Recall, F1, confusion matrix) |
| feature_schema.json | models/ | Feature column order for inference |
| model_metadata.json | models/ | Model metadata (trained_at, model names, metrics, labels) |
| reference_features.csv | models/ | Training feature data used as reference for drift detection |

## Monitoring Report

| Field | Type | Description |
|-------|------|-------------|
| generated_at | string | ISO timestamp of report generation |
| reference_rows | int | Number of rows in reference (training) data |
| current_rows | int | Number of rows in current data |
| features_checked | int | Number of features checked for drift |
| overall_status | string | HEALTHY / MODERATE DRIFT / RETRAINING RECOMMENDED |
| feature_reports | array | Per-feature PSI scores and drift status |
| thresholds | object | PSI thresholds for drift classification |
