"""
Feature engineering for next-day AQI prediction.

Builds features from the gold_air_quality_daily table:
  - Air-quality features: PM2.5, PM10, NO2, SO2, CO, O3
  - Weather features: temperature, humidity, precipitation, wind speed
  - Temporal features: day, day_of_week, month
  - Lag features: AQI lag 1/2/3 days
  - Rolling features: 3-day and 7-day rolling means
  - Target: next_day_aqi (shifted -1), next_day_aqi_category

Data leakage prevention:
  - Features for date T use only data from T and earlier.
  - The target is T+1's AQI, so we shift AQI forward by 1 row per station.
  - Lag/rolling features are computed on the AQI series BEFORE the shift,
    so they never look at the target row.
"""
import json
import os
from datetime import datetime, timezone

import pandas as pd
import requests

from config import API_BASE, get_headers
from pipeline.aggregate import get_aqi_category


POLLUTANT_COLS = ["avg_pm25", "avg_pm10", "avg_no2", "avg_so2", "avg_co", "avg_o3"]
WEATHER_COLS = ["avg_temperature", "avg_humidity", "avg_rainfall", "avg_wind_speed"]
BASE_FEATURE_COLS = POLLUTANT_COLS + WEATHER_COLS

# Feature columns produced by engineering (order matters for inference)
FEATURE_COLUMNS = (
    POLLUTANT_COLS
    + WEATHER_COLS
    + ["day", "day_of_week", "month"]
    + ["aqi_lag_1", "aqi_lag_2", "aqi_lag_3"]
    + ["aqi_roll_mean_3", "aqi_roll_mean_7"]
    + ["pm25_lag_1", "pm10_lag_1", "no2_lag_1", "so2_lag_1", "co_lag_1", "o3_lag_1"]
)

CATEGORICAL_TARGETS = ["Good", "Satisfactory", "Moderate", "Poor", "Very Poor", "Severe"]


def fetch_gold_data():
    """Fetch all rows from gold_air_quality_daily via Supabase REST API."""
    try:
        resp = requests.get(
            f"{API_BASE}/gold_air_quality_daily?order=date.asc,station_id.asc",
            headers=get_headers(),
            timeout=30,
        )
        if resp.ok:
            return resp.json()
        print(f"[FEATURES] Error fetching gold data: {resp.status_code}")
        return []
    except Exception as e:
        print(f"[FEATURES] Error fetching gold data: {e}")
        return []


def build_feature_frame(rows):
    """
    Turn raw gold-table rows into a feature DataFrame with next-day targets.

    Steps:
      1. Sort by station + date so shifts are per-station.
      2. Compute lag/rolling features on current-day AQI (no future leakage).
      3. Shift AQI and category by -1 to create next_day targets.
      4. Drop rows where target is NaN (last day per station has no next day).

    Returns (features_df, feature_columns) where features_df includes the
    target columns next_day_aqi and next_day_aqi_category.
    """
    if not rows:
        return pd.DataFrame(), FEATURE_COLUMNS

    df = pd.DataFrame(rows)
    df["date"] = pd.to_datetime(df["date"])
    df = df.sort_values(["station_id", "date"]).reset_index(drop=True)

    # Ensure numeric columns
    for col in POLLUTANT_COLS + WEATHER_COLS + ["aqi"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    # Temporal features from the current date
    df["day"] = df["date"].dt.day
    df["day_of_week"] = df["date"].dt.dayofweek
    df["month"] = df["date"].dt.month

    # Lag features (per station, so we group)
    grouped = df.groupby("station_id", group_keys=False)

    # AQI lags
    df["aqi_lag_1"] = grouped["aqi"].shift(1)
    df["aqi_lag_2"] = grouped["aqi"].shift(2)
    df["aqi_lag_3"] = grouped["aqi"].shift(3)

    # Rolling means — use closed='left' so the current row's value is excluded
    # from the window when we want strictly-past data. But for daily features
    # we want the rolling mean *up to and including* the current day, which is
    # fine because the target is the *next* day. So we use the default (right).
    df["aqi_roll_mean_3"] = grouped["aqi"].rolling(3, min_periods=1).mean().reset_index(drop=True)
    df["aqi_roll_mean_7"] = grouped["aqi"].rolling(7, min_periods=1).mean().reset_index(drop=True)

    # Pollutant lag features (1-day lag for each pollutant)
    for col in POLLUTANT_COLS:
        lag_name = col.replace("avg_", "") + "_lag_1"
        df[lag_name] = grouped[col].shift(1)

    # Target: next-day AQI and category (shift -1 = future row)
    df["next_day_aqi"] = grouped["aqi"].shift(-1)
    # For category, we can derive it from next_day_aqi using get_aqi_category
    # to avoid relying on the category column being present.
    df["next_day_aqi_category"] = df["next_day_aqi"].apply(
        lambda x: get_aqi_category(int(round(x))) if pd.notna(x) else None
    )

    # Drop rows without a target (last day per station)
    df = df.dropna(subset=["next_day_aqi"]).reset_index(drop=True)

    return df, FEATURE_COLUMNS


def prepare_train_test(df, feature_cols, test_size=0.3):
    """
    Time-aware train/test split: the latest test_size fraction of dates
    is used as the test set. No shuffling.

    Returns (X_train, y_train_reg, y_train_clf, X_test, y_test_reg, y_test_clf).
    """
    if df.empty:
        return tuple(pd.DataFrame() for _ in range(6))

    # Sort by date so the split is chronological
    df = df.sort_values("date").reset_index(drop=True)

    unique_dates = sorted(df["date"].unique())
    split_idx = int(len(unique_dates) * (1 - test_size))
    split_date = unique_dates[max(split_idx - 1, 0)]

    train_df = df[df["date"] <= split_date]
    test_df = df[df["date"] > split_date]

    # If test set is empty (too few dates), use the last row as test
    if test_df.empty and len(df) > 1:
        train_df = df.iloc[:-1]
        test_df = df.iloc[-1:]

    X_train = train_df[feature_cols].copy()
    y_train_reg = train_df["next_day_aqi"].copy()
    y_train_clf = train_df["next_day_aqi_category"].copy()

    X_test = test_df[feature_cols].copy()
    y_test_reg = test_df["next_day_aqi"].copy()
    y_test_clf = test_df["next_day_aqi_category"].copy()

    return X_train, y_train_reg, y_train_clf, X_test, y_test_reg, y_test_clf


def save_feature_schema(feature_cols, path="models/feature_schema.json"):
    """Persist the feature column order so inference matches training."""
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as f:
        json.dump({"feature_columns": feature_cols, "saved_at": datetime.now(timezone.utc).isoformat()}, f, indent=2)
    print(f"[FEATURES] Feature schema saved to {path}")


def load_feature_schema(path="models/feature_schema.json"):
    """Load the saved feature column order."""
    with open(path) as f:
        data = json.load(f)
    return data["feature_columns"]
