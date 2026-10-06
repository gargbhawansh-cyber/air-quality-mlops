-- =============================================================================
-- Air Quality Index Pipeline — Database Schema
-- =============================================================================
-- This schema is managed via Supabase migrations. The canonical version lives
-- in supabase/migrations/. This file is provided for reference and for setting
-- up a standalone PostgreSQL instance.
--
-- Tables:
--   1. ingestion_runs          — Metadata log for every ingestion execution
--   2. air_quality_measurements — Cleaned, validated air quality readings
--   3. weather_measurements     — Cleaned weather readings
--   4. rejected_records         — Records that failed validation
--   5. gold_air_quality_daily   — Daily analytical aggregation with AQI
--   6. pipeline_runs             — End-to-end pipeline execution log
--   7. data_quality_summary      — Per-run data quality metrics
-- =============================================================================

CREATE TABLE IF NOT EXISTS ingestion_runs (
    run_id           text PRIMARY KEY,
    source           text NOT NULL,
    extraction_time  timestamptz NOT NULL DEFAULT now(),
    status           text NOT NULL DEFAULT 'running',
    row_count        integer NOT NULL DEFAULT 0,
    endpoint         text,
    error_message     text,
    data_source      text NOT NULL DEFAULT 'live',
    created_at       timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS air_quality_measurements (
    measurement_id    bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    station_id        text NOT NULL,
    station_name      text NOT NULL,
    city              text NOT NULL,
    country           text,
    latitude          double precision,
    longitude         double precision,
    measurement_time  timestamptz NOT NULL,
    pollutant         text NOT NULL,
    value             double precision NOT NULL,
    unit              text NOT NULL,
    source            text NOT NULL DEFAULT 'openaq',
    ingestion_run_id  text NOT NULL,
    weather_temperature  double precision,
    weather_humidity     double precision,
    weather_precipitation double precision,
    weather_wind_speed    double precision,
    created_at        timestamptz NOT NULL DEFAULT now(),
    UNIQUE(station_id, pollutant, measurement_time)
);

CREATE INDEX IF NOT EXISTS idx_aq_measurements_time ON air_quality_measurements (measurement_time);
CREATE INDEX IF NOT EXISTS idx_aq_measurements_city ON air_quality_measurements (city);
CREATE INDEX IF NOT EXISTS idx_aq_measurements_station ON air_quality_measurements (station_id);
CREATE INDEX IF NOT EXISTS idx_aq_measurements_pollutant ON air_quality_measurements (pollutant);

CREATE TABLE IF NOT EXISTS weather_measurements (
    weather_id        bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    location_name     text NOT NULL,
    latitude          double precision NOT NULL,
    longitude         double precision NOT NULL,
    measurement_time timestamptz NOT NULL,
    temperature       double precision,
    humidity          double precision,
    precipitation    double precision,
    wind_speed        double precision,
    wind_direction    double precision,
    source            text NOT NULL DEFAULT 'openmeteo',
    ingestion_run_id  text NOT NULL,
    created_at        timestamptz NOT NULL DEFAULT now(),
    UNIQUE(location_name, latitude, longitude, measurement_time)
);

CREATE INDEX IF NOT EXISTS idx_weather_time ON weather_measurements (measurement_time);
CREATE INDEX IF NOT EXISTS idx_weather_location ON weather_measurements (location_name);

CREATE TABLE IF NOT EXISTS rejected_records (
    rejected_id       bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    run_id            text NOT NULL,
    original_record   jsonb NOT NULL,
    rejection_reason  text NOT NULL,
    validation_rule   text,
    rejected_at       timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_rejected_run ON rejected_records (run_id);

CREATE TABLE IF NOT EXISTS gold_air_quality_daily (
    id              bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    date            date NOT NULL,
    city            text NOT NULL,
    station_id      text NOT NULL,
    station_name    text NOT NULL,
    avg_pm25        double precision,
    avg_pm10        double precision,
    avg_no2         double precision,
    avg_so2         double precision,
    avg_co          double precision,
    avg_o3          double precision,
    avg_temperature double precision,
    avg_humidity    double precision,
    avg_rainfall    double precision,
    avg_wind_speed  double precision,
    aqi             double precision,
    aqi_category    text,
    observation_count integer NOT NULL DEFAULT 0,
    pipeline_run_id text,
    created_at      timestamptz NOT NULL DEFAULT now(),
    UNIQUE(date, station_id)
);

CREATE INDEX IF NOT EXISTS idx_gold_date ON gold_air_quality_daily (date);
CREATE INDEX IF NOT EXISTS idx_gold_city ON gold_air_quality_daily (city);
CREATE INDEX IF NOT EXISTS idx_gold_station ON gold_air_quality_daily (station_id);
CREATE INDEX IF NOT EXISTS idx_gold_aqi ON gold_air_quality_daily (aqi DESC);

CREATE TABLE IF NOT EXISTS pipeline_runs (
    run_id              text PRIMARY KEY,
    started_at          timestamptz NOT NULL DEFAULT now(),
    completed_at       timestamptz,
    status              text NOT NULL DEFAULT 'running',
    total_records       integer NOT NULL DEFAULT 0,
    valid_records       integer NOT NULL DEFAULT 0,
    rejected_records   integer NOT NULL DEFAULT 0,
    duplicate_records   integer NOT NULL DEFAULT 0,
    missing_value_count integer NOT NULL DEFAULT 0,
    validation_failures integer NOT NULL DEFAULT 0,
    gold_records        integer NOT NULL DEFAULT 0,
    error_message       text,
    created_at          timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS data_quality_summary (
    summary_id          bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    pipeline_run_id     text NOT NULL,
    source              text NOT NULL,
    total_records       integer NOT NULL DEFAULT 0,
    valid_records       integer NOT NULL DEFAULT 0,
    rejected_records    integer NOT NULL DEFAULT 0,
    duplicate_records   integer NOT NULL DEFAULT 0,
    missing_value_count integer NOT NULL DEFAULT 0,
    validation_failures integer NOT NULL DEFAULT 0,
    schema_valid        boolean NOT NULL DEFAULT true,
    checks_passed       integer NOT NULL DEFAULT 0,
    checks_failed       integer NOT NULL DEFAULT 0,
    created_at          timestamptz NOT NULL DEFAULT now()
);

-- Enable Row Level Security (for Supabase; skip for standalone PostgreSQL)
ALTER TABLE ingestion_runs ENABLE ROW LEVEL SECURITY;
ALTER TABLE air_quality_measurements ENABLE ROW LEVEL SECURITY;
ALTER TABLE weather_measurements ENABLE ROW LEVEL SECURITY;
ALTER TABLE rejected_records ENABLE ROW LEVEL SECURITY;
ALTER TABLE gold_air_quality_daily ENABLE ROW LEVEL SECURITY;
ALTER TABLE pipeline_runs ENABLE ROW LEVEL SECURITY;
ALTER TABLE data_quality_summary ENABLE ROW LEVEL SECURITY;
