# Architecture

## Pipeline Diagram

```
┌─────────────────────────────────────────────────────────────────────┐
│                        SOURCE LAYER                                  │
│   ┌──────────────────┐          ┌──────────────────┐                │
│   │   OpenAQ API     │          │  Open-Meteo API  │                │
│   │  (Air Quality)   │          │    (Weather)     │                │
│   └────────┬─────────┘          └────────┬─────────┘                │
└────────────┼──────────────────────────────┼──────────────────────────┘
             │                              │
             ▼                              ▼
┌─────────────────────────────────────────────────────────────────────┐
│                      INGESTION LAYER                                 │
│   ┌──────────────────┐          ┌──────────────────┐                │
│   │ openaq_ingest.py │          │openmeteo_ingest.py│               │
│   │  (requests +     │          │  (requests +     │                │
│   │   retry + fallback)│        │   retry + fallback)│               │
│   └────────┬─────────┘          └────────┬─────────┘                │
│            │  ingestion_logger.py        │                          │
└────────────┼──────────────────────────────┼──────────────────────────┘
             │                              │
             ▼                              ▼
┌─────────────────────────────────────────────────────────────────────┐
│                        RAW LAYER                                     │
│   data/raw/openaq/              data/raw/openmeteo/                  │
│   (timestamped JSON files)      (timestamped JSON files)             │
│   data/raw/logs/ingestion_log.jsonl                                  │
│   Original API/sample responses — preserved, never edited            │
└─────────────────────────────────────────────────────────────────────┘
             │                              │
             ▼                              ▼
┌─────────────────────────────────────────────────────────────────────┐
│              TRANSFORMATION LAYER                                     │
│   pipeline/extract.py    →  Read raw data                             │
│   pipeline/transform.py  →  Normalize timestamps (UTC), stations,    │
│                              pollutants, units                        │
└─────────────────────────────────────────────────────────────────────┘
             │                              │
             ▼                              ▼
┌─────────────────────────────────────────────────────────────────────┐
│                    STAGING LAYER                                      │
│   data/staging/openaq/         data/staging/openmeteo/                │
│   openaq_YYYYMMDD_HHMMSS.csv   openmeteo_YYYYMMDD_HHMMSS.csv          │
│   Normalized column names, ISO 8601 UTC timestamps,                  │
│   consistent data types, source/run metadata                         │
│   pipeline/staging.py  →  write_staging_openaq/openmeteo             │
└─────────────────────────────────────────────────────────────────────┘
             │
             ▼
┌─────────────────────────────────────────────────────────────────────┐
│                     QUALITY LAYER                                     │
│   quality/checks.py  →  Schema, required fields, null values,        │
│                         duplicates, pollutant ranges, timestamps,     │
│                         unit consistency, referential integrity       │
│   quality/rules.py   →  Configurable validation rules                │
│   Weather enrichment    →  Join AQ + weather by city + hour         │
└──────────────┬──────────────────────────────────────────────────────┘
               │
       ┌───────┴───────┐
       ▼               ▼
┌──────────────┐  ┌──────────────────────────────────────────────────┐
│  REJECTED     │  │              STORAGE LAYER                        │
│  RECORDS      │  │   PostgreSQL / Supabase                           │
│  (table)      │  │   ┌────────────────────────────────┐             │
│  rejected_    │  │   │ air_quality_measurements         │             │
│  records      │  │   │ weather_measurements            │             │
└──────────────┘  │   │ ingestion_runs                  │             │
                  │   │ pipeline_runs                    │             │
                  │   │ data_quality_summary             │             │
                  │   └──────────────┬─────────────────┘             │
                  └──────────────────┼──────────────────────────────┘
                                     │
                                     ▼
┌─────────────────────────────────────────────────────────────────────┐
│                    ANALYTICS LAYER                                    │
│   pipeline/aggregate.py  →  Build gold_air_quality_daily             │
│   - Daily averages per station (PM2.5, PM10, NO2, SO2, CO, O3)      │
│   - Weather averages (temp, humidity, rainfall, wind)                │
│   - AQI calculation (CPCB sub-index methodology)                     │
│   - AQI category (Good → Severe)                                     │
└─────────────────────────────────────────────────────────────────────┘
                                     │
                                     ▼
┌─────────────────────────────────────────────────────────────────────┐
│                    DASHBOARD LAYER                                    │
│   React Web Dashboard (src/)          Streamlit Dashboard (dashboard/)│
│   - AQI Overview                      - AQI Overview                │
│   - AQI Trend                         - AQI Trend                   │
│   - Pollutant Analysis                - Pollutant Analysis           │
│   - City/Station Comparison           - City/Station Comparison     │
│   - Weather Impact                    - Weather Impact              │
│   - Pipeline Status                   - Pipeline Status             │
└─────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────┐
│                  ORCHESTRATION                                       │
│   Apache Airflow DAG: air_quality_etl_pipeline                      │
│   Schedule: @daily  |  Retries: 2  |  Retry delay: 2 min            │
│   Local fallback: python -m pipeline.run_pipeline                   │
└─────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────┐
│                   PART 2 (PLANNED — NOT IMPLEMENTED)                 │
│   MLOps / AQI Prediction                                             │
│   - Feature engineering (lag, rolling averages)                     │
│   - ML model training (forecasting, classification)                 │
│   - MLflow experiment tracking                                       │
│   - Model registry                                                   │
│   - FastAPI prediction service                                       │
│   - Docker containerization                                          │
│   - Model monitoring & drift detection                               │
└─────────────────────────────────────────────────────────────────────┘
```

## Data Flow Summary

1. **OpenAQ** and **Open-Meteo** APIs are queried by Python ingestion scripts
2. Raw API responses are saved to `data/raw/` as timestamped JSON files (preserved, never edited)
3. Ingestion metadata (run_id, source, status, row_count) is logged to `ingestion_runs` table and local JSONL file
4. Raw data is read from the landing zone and transformed (normalized timestamps, stations, pollutants, units)
5. Transformed records are written to the persistent staging layer at `data/staging/` as timestamped CSV files with normalized column names, ISO 8601 UTC timestamps, consistent data types, and source/run metadata
6. Staging data is validated through data quality checks (schema, required fields, nulls, duplicates, ranges, timestamps, units, referential integrity)
7. Weather data is joined to air quality data by city + nearest hour (weather enrichment)
8. Invalid records are sent to `rejected_records` table with rejection reason and validation rule
9. Valid records are loaded into `air_quality_measurements` and `weather_measurements` tables (cleaned PostgreSQL layer)
10. The gold analytical table `gold_air_quality_daily` is built with daily averages and AQI calculations
11. The dashboard reads from the gold table and other tables to display real-time analytics

### Layer Flow

```
Source → Raw → Staging → Cleaned (PostgreSQL) → Analytical/Gold → Dashboard
```
