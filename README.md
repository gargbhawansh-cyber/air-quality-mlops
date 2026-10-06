# Air Quality Index Analysis and Prediction

## Part 1: Data Engineering Pipeline

A complete data engineering pipeline that collects air quality measurements from **OpenAQ** and weather data from **Open-Meteo**, processes them through a multi-layer ETL pipeline with data quality validation, stores them in **PostgreSQL (Supabase)**, builds an analytical gold data mart with AQI calculations, and presents the results in an interactive dashboard.

---

## Project Overview

Air pollution is a critical public health concern, particularly in urban areas. This project builds an end-to-end data pipeline that:

- **Ingests** real-time air quality data from the OpenAQ API and weather data from the Open-Meteo API
- **Preserves** raw API responses in a landing zone for auditability
- **Transforms** and normalizes data (timestamps, station names, pollutant units)
- **Validates** data quality with configurable rules (schema, ranges, duplicates, missing values)
- **Rejects** invalid records to a separate error log with rejection reasons
- **Stores** cleaned data in a normalized PostgreSQL schema
- **Builds** a gold analytical data mart with daily aggregations and AQI calculations
- **Visualizes** the results in an interactive dashboard with 5+ views

The pipeline is orchestrated via an Apache Airflow DAG and also supports local execution via a Python script.

---

## Architecture

```
OpenAQ API          Open-Meteo API
    |                    |
    v                    v
Python Collectors (requests)
    |                    |
    v                    v
Raw Landing Zone (data/raw/) — original API responses, preserved
    |                    |
    v                    v
Transformation (pipeline/transform.py) — normalize timestamps, stations, pollutants, units
    |                    |
    v                    v
Staging Layer (data/staging/) — normalized CSV files with consistent types
    |                    |
    v                    v
Data Quality Checks (quality/) — schema, ranges, duplicates, missing, units
    |                    |
    +--> Rejected Records (rejected_records table)
    |
    v
Cleaned Data (PostgreSQL) — air_quality_measurements, weather_measurements
    |
    v
Gold Analytical Data Mart (gold_air_quality_daily) — daily averages + AQI
    |
    v
Dashboard (React + Streamlit)

Orchestrated by: Apache Airflow (airflow/air_quality_etl_dag.py)
```

### Layer Descriptions

| Layer | Description |
|-------|-------------|
| Source Layer | OpenAQ (air quality) + Open-Meteo (weather) public APIs |
| Ingestion Layer | Python scripts using `requests` with retry logic and error handling |
| Raw Layer | Timestamped JSON files preserving original API responses — never edited |
| Transformation Layer | Timestamp, station, pollutant, and unit normalization (transform.py) |
| Staging Layer | Persistent CSV files with normalized column names, ISO 8601 UTC timestamps, consistent data types, and source/run metadata |
| Quality Layer | Schema, range, duplicate, missing, timestamp, unit, referential checks |
| Storage Layer | PostgreSQL/Supabase with normalized tables and indexes (cleaned data) |
| Analytics Layer | Gold data mart with daily aggregations and AQI |
| Dashboard Layer | React web dashboard + Streamlit dashboard |

---

## Data Sources

### OpenAQ
- **URL**: https://api.openaq.org/v3
- **Data**: Air quality measurements (PM2.5, PM10, CO, NO2, SO2, O3)
- **Access**: Free API key required (https://docs.openaq.org/)
- **Fallback**: Sample data generated from public-source structure when API is unavailable

### Open-Meteo
- **URL**: https://archive-api.open-meteo.com/v1/archive
- **Data**: Historical weather (temperature, humidity, precipitation, wind speed/direction)
- **Access**: Free, no API key required
- **Fallback**: Sample data generated when API is unavailable

---

## Technology Stack

| Component | Technology |
|-----------|-----------|
| Language | Python 3.13 |
| HTTP Client | requests |
| Data Processing | pandas |
| Database | PostgreSQL (Supabase) |
| Orchestration | Apache Airflow |
| Dashboard (Web) | React + TypeScript + Tailwind CSS |
| Dashboard (Local) | Streamlit + Plotly |
| Query Language | SQL |

---

## Project Structure

```
air-quality-pipeline/
├── config.py                 # Central configuration (env vars, cities, pollutants)
├── ingestion/
│   ├── openaq_ingest.py      # OpenAQ API ingestion with fallback
│   ├── openmeteo_ingest.py   # Open-Meteo API ingestion with fallback
│   └── ingestion_logger.py   # Ingestion metadata logging
├── pipeline/
│   ├── extract.py            # Read raw data from landing zone
│   ├── transform.py          # Normalize timestamps, stations, pollutants, units
│   ├── staging.py            # Write normalized records to persistent staging CSV files
│   ├── load.py               # Load validated data into PostgreSQL
│   ├── aggregate.py          # Build gold analytical table with AQI
│   ├── run_pipeline.py       # End-to-end pipeline orchestrator
│   ├── fast_load.py          # Fast local pipeline (sample data)
│   └── bulk_load.py          # Bulk REST API loader
├── quality/
│   ├── checks.py             # Data quality validation (schema, ranges, duplicates)
│   └── rules.py              # Configurable validation rules
├── airflow/
│   └── air_quality_etl_dag.py # Airflow DAG definition
├── database/
│   ├── schema.sql            # PostgreSQL schema (reference)
│   └── queries.sql           # Analytical queries
├── dashboard/
│   └── app.py                # Streamlit dashboard
├── data/
│   ├── raw/                  # Raw API responses (preserved)
│   │   ├── openaq/
│   │   ├── openmeteo/
│   │   └── logs/
│   ├── staging/              # Persistent staging layer (normalized CSV files)
│   │   ├── openaq/            #   openaq_YYYYMMDD_HHMMSS.csv
│   │   └── openmeteo/         #   openmeteo_YYYYMMDD_HHMMSS.csv
│   ├── processed/            # Processed/cleaned data
│   └── rejected/             # Rejected records
├── docs/
│   ├── architecture.md       # Architecture diagram and documentation
│   ├── DATA_DICTIONARY.md     # Complete field documentation
│   └── VALIDATION_RULES.md    # Validation rule documentation
├── src/                      # React dashboard (web)
│   ├── App.tsx
│   ├── lib/supabase.ts
│   └── components/
│       ├── OverviewView.tsx
│       ├── TrendView.tsx
│       ├── PollutantView.tsx
│       ├── ComparisonView.tsx
│       ├── WeatherView.tsx
│       └── PipelineView.tsx
├── .env.example
├── requirements.txt
└── README.md
```

---

## Environment Variables

Copy `.env.example` to `.env` and fill in your credentials:

```bash
cp .env.example .env
```

| Variable | Description | Required |
|----------|-------------|----------|
| `VITE_SUPABASE_URL` | Supabase project URL | Yes |
| `VITE_SUPABASE_ANON_KEY` | Supabase anon key | Yes |
| `SUPABASE_SERVICE_ROLE_KEY` | Supabase service role key (for server-side writes) | Optional |
| `OPENAQ_API_KEY` | OpenAQ API key | For live data |
| `OPENAQ_API_BASE` | OpenAQ API base URL | No (has default) |
| `OPENMETEO_API_BASE` | Open-Meteo API base URL | No (has default) |
| `REQUEST_TIMEOUT` | HTTP request timeout in seconds | No (default: 30) |
| `REQUEST_RETRIES` | Number of retry attempts | No (default: 3) |
| `USE_SAMPLE_FALLBACK` | Use sample data if API fails | No (default: true) |

---

## Installation

```bash
# Clone the project
cd air-quality-pipeline

# Install Python dependencies
pip install -r requirements.txt

# Copy environment file
cp .env.example .env
# Edit .env with your credentials

# Install Node.js dependencies (for web dashboard)
npm install
```

---

## Database Setup

The database schema is managed via Supabase migrations. The schema is already applied in this environment.

For a standalone PostgreSQL instance:

```bash
# Create database
createdb airquality

# Apply schema
psql -d airquality -f database/schema.sql
```

---

## Pipeline Execution

### Run the full pipeline (local)

```bash
# Full pipeline with API calls + fallback
python -m pipeline.run_pipeline

# Fast pipeline (sample data, for demo)
python -m pipeline.fast_load

# Bulk load processed data into Supabase
python -m pipeline.urllib_load
```

### Run individual stages

```bash
# Ingestion only
python -m ingestion.openaq_ingest
python -m ingestion.openmeteo_ingest

# Transformation only
python -c "from pipeline.transform import transform_air_quality; ..."

# Aggregation only
python -c "from pipeline.aggregate import build_gold_table; ..."
```

---

## Airflow

### Start Airflow

```bash
# Initialize Airflow
export AIRFLOW_HOME=~/airflow
airflow db init

# Copy DAG
cp airflow/air_quality_etl_dag.py $AIRFLOW_HOME/dags/

# Start scheduler
airflow scheduler

# Start web server (in another terminal)
airflow webserver --port 8080
```

### Trigger the DAG

```bash
# Trigger via CLI
airflow dags trigger air_quality_etl_pipeline

# Or via the Airflow UI at http://localhost:8080
```

### DAG Task Sequence

1. `extract_openaq` — Fetch air quality data from OpenAQ
2. `extract_weather` — Fetch weather data from Open-Meteo
3. `validate_raw_data` — Validate raw data exists and is non-empty
4. `transform_air_quality` — Normalize air quality records
5. `transform_weather` — Normalize weather records
6. `write_staging` — Write normalized records to persistent staging CSV files
7. `quality_checks` — Run full data quality validation
8. `load_postgresql` — Load validated data into PostgreSQL
9. `build_gold_tables` — Build analytical gold data mart
10. `generate_pipeline_summary` — Record pipeline run metrics

---

## Dashboard

### Web Dashboard (React)

The web dashboard runs automatically in the Bolt environment.

```bash
npm run dev
```

### Streamlit Dashboard

```bash
streamlit run dashboard/app.py
```

The Streamlit dashboard provides 6 views:
1. **AQI Overview** — KPI cards, latest AQI, pipeline status
2. **AQI Trend** — Interactive time-series with city/station filters
3. **Pollutant Analysis** — Per-pollutant breakdown with city comparisons
4. **City / Station Comparison** — Bar charts and tables
5. **Weather Impact** — Correlation analysis with scatter plots
6. **Pipeline Status** — Data quality, ingestion logs, rejected records

---

## End-to-End Execution

```bash
# 1. Set up environment
cp .env.example .env
# Edit .env with credentials

# 2. Install dependencies
pip install -r requirements.txt
npm install

# 3. Run the pipeline
python -m pipeline.run_pipeline
# OR for fast demo: python -m pipeline.fast_load && python -m pipeline.urllib_load

# 4. Verify data in database
# Check the dashboard for populated data

# 5. Start the dashboard
# Web: npm run dev (automatic in Bolt)
# Streamlit: streamlit run dashboard/app.py
```

---

## Part 2: MLOps — Next-Day AQI Prediction

Part 2 extends the data pipeline with Machine Learning to predict next-day AQI and AQI category. It uses the existing Part 1 gold table data and adds feature engineering, model training, MLflow tracking, a FastAPI inference service, Docker containerization, monitoring/drift detection, and a retraining workflow.

### Part 2 Architecture

```
Part 1 Gold Table (gold_air_quality_daily)
         |
         v
    Feature Engineering (ml/features.py)
    - AQ, weather, temporal, lag, rolling features
    - Target: next_day_aqi, next_day_aqi_category
         |
         v
    Time-aware Train/Test Split (no shuffling)
         |
    +----+----+
    |         |
    v         v
 Regression  Classification
 (Linear,    (Logistic,
  RF)        RF)
    |         |
    v         v
 Evaluation  Evaluation
 (MAE,RMSE,  (Acc,Prec,
  R2)         Rec,F1,CM)
    |         |
    v         v
 MLflow Logging (air-quality-regression / air-quality-classification)
    |         |
    v         v
 Best Model  Best Model
 saved to    saved to
 models/     models/
    |
    v
 FastAPI Inference (api/main.py)
    |
    v
 Monitoring (ml/monitor.py) — PSI drift detection
    |
    v
 Retraining (ml/retrain.py) — triggered when drift detected
```

### Feature Engineering

Features are derived from `gold_air_quality_daily` per station:

| Category | Features |
|----------|----------|
| Air quality | avg_pm25, avg_pm10, avg_no2, avg_so2, avg_co, avg_o3 |
| Weather | avg_temperature, avg_humidity, avg_rainfall, avg_wind_speed |
| Temporal | day, day_of_week, month |
| Lag | aqi_lag_1, aqi_lag_2, aqi_lag_3, pm25_lag_1, pm10_lag_1, no2_lag_1, so2_lag_1, co_lag_1, o3_lag_1 |
| Rolling | aqi_roll_mean_3, aqi_roll_mean_7 |
| Target | next_day_aqi, next_day_aqi_category |

**Data leakage prevention:** Features for date T use only data from T and earlier. The target is T+1's AQI (shifted forward). Lag/rolling features are computed before the target shift.

### Model Training

Two regression models (Linear Regression, Random Forest Regressor) and two classification models (Logistic Regression, Random Forest Classifier) are trained. Best models are selected by R2 (regression) and F1-macro (classification).

### MLflow Tracking

```bash
# Start MLflow UI
mlflow ui --host 0.0.0.0 --port 5000
```

Experiments: `air-quality-regression` and `air-quality-classification`

### FastAPI Inference

```bash
# Start the API
uvicorn api.main:app --host 0.0.0.0 --port 8000

# Health check
curl http://localhost:8000/health

# Model info
curl http://localhost:8000/model-info

# Predict
curl -X POST http://localhost:8000/predict \
  -H "Content-Type: application/json" \
  -d '{"avg_pm25": 70, "avg_pm10": 120, "avg_no2": 50, "avg_so2": 40,
       "avg_co": 2, "avg_o3": 75, "avg_temperature": 25, "avg_humidity": 60,
       "avg_rainfall": 1, "avg_wind_speed": 10, "day": 6, "day_of_week": 5,
       "month": 9, "aqi_lag_1": 120, "aqi_lag_2": 115, "aqi_lag_3": 110,
       "aqi_roll_mean_3": 115, "aqi_roll_mean_7": 112,
       "pm25_lag_1": 68, "pm10_lag_1": 118, "no2_lag_1": 48,
       "so2_lag_1": 38, "co_lag_1": 1.9, "o3_lag_1": 73}'
```

### Docker

```bash
# Build and run the API container
docker build -t air-quality-api .
docker run -p 8000:8000 air-quality-api
```

### Monitoring / Drift Detection

Uses Population Stability Index (PSI) to compare training/reference data with current data:

| PSI | Status |
|-----|--------|
| < 0.1 | No drift |
| 0.1 - 0.25 | Moderate drift — monitor |
| >= 0.25 | Significant drift — RETRAINING RECOMMENDED |

### Retraining

The retraining script fetches latest data, retrains models, and promotes only if the new model performs at least as well as the current production model.

### Part 2 Project Structure

```
ml/
    features.py      — feature engineering + time-aware split
    train.py          — train regression + classification models
    evaluate.py       — evaluation metrics
    predict.py        — load models and make predictions
    monitor.py        — PSI drift detection
    retrain.py        — retraining workflow
models/
    regression/       — best regression model + metrics
    classification/   — best classification model + metrics
    feature_schema.json
    model_metadata.json
    reference_features.csv
api/
    main.py           — FastAPI inference service
monitoring/
    drift_report.json — generated drift reports
Dockerfile            — Docker support for FastAPI
docs/
    ML_ARCHITECTURE.md
    ML_DATA_DICTIONARY.md
```

---

## Part 2 Commands

```bash
# Install ML dependencies
pip install -r requirements.txt

# Train models
python -m ml.train

# Start MLflow UI
mlflow ui --host 0.0.0.0 --port 5000

# Start FastAPI
uvicorn api.main:app --host 0.0.0.0 --port 8000

# Run monitoring
python -m ml.monitor

# Run retraining
python -m ml.retrain

# Complete Part 1 + Part 2 workflow
python -m pipeline.run_pipeline    # Part 1: ETL pipeline
python -m ml.train                 # Part 2: Train models
python -m ml.monitor               # Part 2: Check for drift
streamlit run dashboard/app.py     # Dashboard (Part 1 + Part 2)
```
