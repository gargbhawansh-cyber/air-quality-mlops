# Data Dictionary

## Table: ingestion_runs

| Field | Data Type | Description | Source | Nullable | Validation |
|-------|-----------|-------------|--------|----------|------------|
| run_id | text (PK) | Unique identifier for each ingestion run | System-generated | NOT NULL | Format: `{source}_{timestamp}_{uuid8}` |
| source | text | Data source name | Ingestion script | NOT NULL | One of: openaq, openmeteo |
| extraction_time | timestamptz | When extraction was performed | System clock | NOT NULL | Valid timestamp |
| status | text | Run status | Pipeline | NOT NULL | One of: success, failed, running |
| row_count | integer | Number of records extracted | Ingestion script | NOT NULL | >= 0 |
| endpoint | text | API endpoint called | Ingestion script | NULL | Valid URL |
| error_message | text | Error details if failed | Ingestion script | NULL | — |
| data_source | text | Whether data is live or sample | Ingestion script | NOT NULL | One of: live, sample |
| created_at | timestamptz | Record creation time | Database default | NOT NULL | Default: now() |

## Table: air_quality_measurements

| Field | Data Type | Description | Source | Nullable | Validation |
|-------|-----------|-------------|--------|----------|------------|
| measurement_id | bigint (PK) | Auto-increment primary key | Database | NOT NULL | Generated |
| station_id | text | Monitoring station identifier | OpenAQ | NOT NULL | Non-empty string |
| station_name | text | Station display name | OpenAQ (normalized) | NOT NULL | Title-case normalized |
| city | text | City where station is located | OpenAQ | NOT NULL | Non-empty |
| country | text | Country code | OpenAQ | NULL | ISO code |
| latitude | double precision | Station latitude | OpenAQ | NULL | -90 to 90 |
| longitude | double precision | Station longitude | OpenAQ | NULL | -180 to 180 |
| measurement_time | timestamptz | When measurement was taken | OpenAQ | NOT NULL | Valid ISO 8601 UTC |
| pollutant | text | Pollutant name | OpenAQ (normalized) | NOT NULL | One of: pm25, pm10, co, no2, so2, o3 |
| value | double precision | Measured concentration value | OpenAQ | NOT NULL | Within pollutant range |
| unit | text | Measurement unit | OpenAQ (normalized) | NOT NULL | Canonical: ug/m3, mg/m3, ppm, ppb |
| source | text | Data source | Pipeline | NOT NULL | Default: openaq |
| ingestion_run_id | text | FK to ingestion_runs | Pipeline | NOT NULL | Must exist in ingestion_runs |
| weather_temperature | double precision | Enriched temperature (°C) from weather data | Weather join | NULL | -50 to 60 |
| weather_humidity | double precision | Enriched relative humidity (%) | Weather join | NULL | 0 to 100 |
| weather_precipitation | double precision | Enriched precipitation (mm) | Weather join | NULL | >= 0 |
| weather_wind_speed | double precision | Enriched wind speed (km/h) | Weather join | NULL | >= 0 |
| created_at | timestamptz | Record creation time | Database | NOT NULL | Default: now() |

**Unique constraint**: (station_id, pollutant, measurement_time)

## Table: weather_measurements

| Field | Data Type | Description | Source | Nullable | Validation |
|-------|-----------|-------------|--------|----------|------------|
| weather_id | bigint (PK) | Auto-increment primary key | Database | NOT NULL | Generated |
| location_name | text | Location/city name | Open-Meteo | NOT NULL | Non-empty |
| latitude | double precision | Location latitude | Open-Meteo | NOT NULL | -90 to 90 |
| longitude | double precision | Location longitude | Open-Meteo | NOT NULL | -180 to 180 |
| measurement_time | timestamptz | Hourly timestamp | Open-Meteo | NOT NULL | Valid ISO 8601 UTC |
| temperature | double precision | Temperature in °C | Open-Meteo | NULL | -50 to 60 |
| humidity | double precision | Relative humidity % | Open-Meteo | NULL | 0 to 100 |
| precipitation | double precision | Precipitation in mm | Open-Meteo | NULL | >= 0 |
| wind_speed | double precision | Wind speed in km/h | Open-Meteo | NULL | >= 0 |
| wind_direction | double precision | Wind direction in degrees | Open-Meteo | NULL | 0 to 359 |
| source | text | Data source | Pipeline | NOT NULL | Default: openmeteo |
| ingestion_run_id | text | FK to ingestion_runs | Pipeline | NOT NULL | Must exist |
| created_at | timestamptz | Record creation time | Database | NOT NULL | Default: now() |

**Unique constraint**: (location_name, latitude, longitude, measurement_time)

## Table: rejected_records

| Field | Data Type | Description | Source | Nullable | Validation |
|-------|-----------|-------------|--------|----------|------------|
| rejected_id | bigint (PK) | Auto-increment primary key | Database | NOT NULL | Generated |
| run_id | text | Pipeline run that rejected the record | Pipeline | NOT NULL | Must exist in pipeline_runs |
| original_record | jsonb | Full original record as JSON | Pipeline | NOT NULL | Valid JSON |
| rejection_reason | text | Human-readable rejection reason | Quality checks | NOT NULL | Non-empty |
| validation_rule | text | Name of the rule that failed | Quality checks | NULL | One of: required_fields, pollutant_validity, timestamp_validity, pollutant_range, unit_consistency, null_value |
| rejected_at | timestamptz | When record was rejected | Pipeline | NOT NULL | Default: now() |

## Table: gold_air_quality_daily

| Field | Data Type | Description | Source | Nullable | Validation |
|-------|-----------|-------------|--------|----------|------------|
| id | bigint (PK) | Auto-increment primary key | Database | NOT NULL | Generated |
| date | date | Aggregation date | Pipeline | NOT NULL | Valid date |
| city | text | City name | Pipeline | NOT NULL | Non-empty |
| station_id | text | Station identifier | Pipeline | NOT NULL | Non-empty |
| station_name | text | Station display name | Pipeline | NOT NULL | Non-empty |
| avg_pm25 | double precision | Daily average PM2.5 (ug/m3) | Computed | NULL | 0-1000 |
| avg_pm10 | double precision | Daily average PM10 (ug/m3) | Computed | NULL | 0-2000 |
| avg_no2 | double precision | Daily average NO2 (ug/m3) | Computed | NULL | 0-3000 |
| avg_so2 | double precision | Daily average SO2 (ug/m3) | Computed | NULL | 0-2000 |
| avg_co | double precision | Daily average CO (mg/m3) | Computed | NULL | 0-100 |
| avg_o3 | double precision | Daily average O3 (ug/m3) | Computed | NULL | 0-1000 |
| avg_temperature | double precision | Daily average temperature (°C) | Weather join | NULL | -50 to 60 |
| avg_humidity | double precision | Daily average humidity (%) | Weather join | NULL | 0-100 |
| avg_rainfall | double precision | Daily average precipitation (mm) | Weather join | NULL | >= 0 |
| avg_wind_speed | double precision | Daily average wind speed (km/h) | Weather join | NULL | >= 0 |
| aqi | double precision | Calculated Air Quality Index | AQI calculation | NULL | 0-500 |
| aqi_category | text | AQI category label | AQI calculation | NULL | One of: Good, Satisfactory, Moderate, Poor, Very Poor, Severe |
| observation_count | integer | Number of measurements aggregated | Pipeline | NOT NULL | > 0 |
| pipeline_run_id | text | Pipeline run that created this record | Pipeline | NULL | — |
| created_at | timestamptz | Record creation time | Database | NOT NULL | Default: now() |

**Unique constraint**: (date, station_id)

## Table: pipeline_runs

| Field | Data Type | Description | Source | Nullable | Validation |
|-------|-----------|-------------|--------|----------|------------|
| run_id | text (PK) | Unique pipeline run identifier | Pipeline | NOT NULL | Format: pipeline_{timestamp} |
| started_at | timestamptz | Pipeline start time | Pipeline | NOT NULL | Valid timestamp |
| completed_at | timestamptz | Pipeline completion time | Pipeline | NULL | > started_at |
| status | text | Run status | Pipeline | NOT NULL | One of: success, failed, running |
| total_records | integer | Total records processed | Pipeline | NOT NULL | >= 0 |
| valid_records | integer | Records that passed validation | Pipeline | NOT NULL | >= 0 |
| rejected_records | integer | Records rejected | Pipeline | NOT NULL | >= 0 |
| duplicate_records | integer | Duplicate records found | Pipeline | NOT NULL | >= 0 |
| missing_value_count | integer | Missing/null values detected | Pipeline | NOT NULL | >= 0 |
| validation_failures | integer | Total validation failures | Pipeline | NOT NULL | >= 0 |
| gold_records | integer | Gold analytical records created | Pipeline | NOT NULL | >= 0 |
| error_message | text | Error details if failed | Pipeline | NULL | — |
| created_at | timestamptz | Record creation time | Database | NOT NULL | Default: now() |

## Table: data_quality_summary

| Field | Data Type | Description | Source | Nullable | Validation |
|-------|-----------|-------------|--------|----------|------------|
| summary_id | bigint (PK) | Auto-increment primary key | Database | NOT NULL | Generated |
| pipeline_run_id | text | FK to pipeline_runs | Pipeline | NOT NULL | Must exist |
| source | text | Data source name | Pipeline | NOT NULL | One of: openaq, openmeteo |
| total_records | integer | Total records from this source | Pipeline | NOT NULL | >= 0 |
| valid_records | integer | Valid records from this source | Pipeline | NOT NULL | >= 0 |
| rejected_records | integer | Rejected records | Pipeline | NOT NULL | >= 0 |
| duplicate_records | integer | Duplicates found | Pipeline | NOT NULL | >= 0 |
| missing_value_count | integer | Missing values | Pipeline | NOT NULL | >= 0 |
| validation_failures | integer | Validation failures | Pipeline | NOT NULL | >= 0 |
| schema_valid | boolean | Schema check passed | Quality checks | NOT NULL | true/false |
| checks_passed | integer | Number of checks passed | Quality checks | NOT NULL | >= 0 |
| checks_failed | integer | Number of checks failed | Quality checks | NOT NULL | >= 0 |
| created_at | timestamptz | Record creation time | Database | NOT NULL | Default: now() |

---

## Staging Layer Files

The staging layer is a persistent intermediate store between raw ingestion and final validation/loading. It contains normalized data with consistent column names, ISO 8601 UTC timestamps, normalized pollutant names/units, and source/run metadata. Files are written as timestamped CSVs so every pipeline run is reproducible.

### File: data/staging/openaq/openaq_YYYYMMDD_HHMMSS.csv

Written by `pipeline/staging.py:write_staging_openaq()` after transformation, before validation.

| Field | Data Type | Description | Source | Nullable | Validation |
|-------|-----------|-------------|--------|----------|------------|
| station_id | text | Monitoring station identifier | OpenAQ (normalized) | NOT NULL | Non-empty |
| station_name | text | Station display name | OpenAQ (normalized, title-case) | NOT NULL | Non-empty |
| city | text | City where station is located | OpenAQ | NOT NULL | Non-empty |
| country | text | Country code | OpenAQ | NULL | ISO code |
| latitude | double precision | Station latitude | OpenAQ | NULL | -90 to 90 |
| longitude | double precision | Station longitude | OpenAQ | NULL | -180 to 180 |
| measurement_time | text (ISO 8601) | Measurement timestamp in UTC | OpenAQ (normalized) | NOT NULL | Valid ISO 8601 |
| pollutant | text | Pollutant name (lowercase) | OpenAQ (normalized) | NOT NULL | One of: pm25, pm10, co, no2, so2, o3 |
| value | double precision | Measured concentration value | OpenAQ | NOT NULL | Numeric |
| unit | text | Measurement unit (canonical) | OpenAQ (normalized) | NOT NULL | Canonical: ug/m3, mg/m3, ppm, ppb |
| source | text | Data source identifier | Pipeline | NOT NULL | Always: openaq |
| ingestion_run_id | text | FK to ingestion_runs | Pipeline | NOT NULL | Must exist |

### File: data/staging/openmeteo/openmeteo_YYYYMMDD_HHMMSS.csv

Written by `pipeline/staging.py:write_staging_openmeteo()` after transformation, before validation.

| Field | Data Type | Description | Source | Nullable | Validation |
|-------|-----------|-------------|--------|----------|------------|
| location_name | text | Location/city name | Open-Meteo | NOT NULL | Non-empty |
| latitude | double precision | Location latitude | Open-Meteo | NOT NULL | -90 to 90 |
| longitude | double precision | Location longitude | Open-Meteo | NOT NULL | -180 to 180 |
| measurement_time | text (ISO 8601) | Hourly timestamp in UTC | Open-Meteo (normalized) | NOT NULL | Valid ISO 8601 |
| temperature | double precision | Temperature in °C | Open-Meteo | NULL | -50 to 60 |
| humidity | double precision | Relative humidity % | Open-Meteo | NULL | 0 to 100 |
| precipitation | double precision | Precipitation in mm | Open-Meteo | NULL | >= 0 |
| wind_speed | double precision | Wind speed in km/h | Open-Meteo | NULL | >= 0 |
| wind_direction | double precision | Wind direction in degrees | Open-Meteo | NULL | 0 to 359 |
| source | text | Data source identifier | Pipeline | NOT NULL | Always: openmeteo |
| ingestion_run_id | text | FK to ingestion_runs | Pipeline | NOT NULL | Must exist |
