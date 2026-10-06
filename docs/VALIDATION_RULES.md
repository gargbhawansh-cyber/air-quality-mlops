# Validation Rules

## Required Fields

### Air Quality Measurements
| Field | Rule |
|-------|------|
| station_id | Must be present and non-empty |
| station_name | Must be present and non-empty |
| city | Must be present and non-empty |
| measurement_time | Must be present and a valid timestamp |
| pollutant | Must be present and in the allowed list |
| value | Must be present and numeric |
| unit | Must be present and in the allowed list for the pollutant |

### Weather Measurements
| Field | Rule |
|-------|------|
| location_name | Must be present and non-empty |
| latitude | Must be present and numeric (-90 to 90) |
| longitude | Must be present and numeric (-180 to 180) |
| measurement_time | Must be present and a valid timestamp |

## Allowed Pollutant Names

| Pollutant | Canonical Name |
|-----------|---------------|
| PM2.5 | pm25 |
| PM10 | pm10 |
| CO | co |
| NO2 | no2 |
| SO2 | so2 |
| O3 | o3 |

All pollutant names are normalized to lowercase before validation.

## Allowed Units

| Pollutant | Allowed Units |
|-----------|--------------|
| pm25 | ug/m3 |
| pm10 | ug/m3 |
| co | mg/m3, ug/m3 |
| no2 | ug/m3, ppb |
| so2 | ug/m3, ppb |
| o3 | ug/m3, ppb |

### Unit Normalization

| Input Unit | Normalized Unit |
|------------|----------------|
| µg/m³ | ug/m3 |
| ug/m3 | ug/m3 |
| µg/m3 | ug/m3 |
| mg/m³ | mg/m3 |
| ppm | ppm |
| ppb | ppb |

## Pollutant Value Ranges

| Pollutant | Min Value | Max Value | Unit |
|-----------|-----------|-----------|------|
| pm25 | 0 | 1000 | ug/m3 |
| pm10 | 0 | 2000 | ug/m3 |
| co | 0 | 100 | mg/m3 |
| no2 | 0 | 3000 | ug/m3 |
| so2 | 0 | 2000 | ug/m3 |
| o3 | 0 | 1000 | ug/m3 |

Values outside these ranges are rejected with the `pollutant_range` validation rule.

## Timestamp Rules

- All timestamps are normalized to ISO 8601 format with UTC timezone
- Input formats accepted: ISO 8601 with or without 'Z' suffix
- Invalid timestamps are rejected with the `timestamp_validity` validation rule
- Internal storage uses `timestamptz` in PostgreSQL

## Duplicate Detection

### Rule
Duplicate records are detected using the composite key:

```
station_id + pollutant + measurement_time
```

For weather data:

```
location_name + latitude + longitude + measurement_time
```

### Handling
- The first occurrence of a duplicate is kept
- Subsequent duplicates are silently skipped (not loaded)
- Duplicate counts are recorded in the pipeline run metrics
- A `UNIQUE` constraint on the database table enforces this at the storage level

## Missing Data Handling

### Policy
- Missing/null values are **not** blindly filled
- Records with null values in required fields are rejected
- Records with null values in optional fields (e.g., weather fields) are kept
- Three categories are distinguished:
  1. **Missing values**: Null where a value is expected (counted in `missing_value_count`)
  2. **Valid zero values**: Zero is a legitimate measurement (kept)
  3. **Unavailable measurements**: Null in optional fields (kept, not counted as missing)

### Statistics
Missing value counts are recorded per pipeline run and exposed in the data quality summary.

## Rejected Record Process

1. A record fails a validation check
2. The original record is serialized to JSON
3. A rejected record entry is created with:
   - `run_id`: The pipeline run identifier
   - `original_record`: The full original record as JSONB
   - `rejection_reason`: Human-readable description
   - `validation_rule`: The name of the rule that failed
   - `rejected_at`: Timestamp of rejection
4. The rejected record is stored in the `rejected_records` table
5. The record does NOT enter the analytical tables

### Validation Rules

| Rule Name | Description |
|-----------|-------------|
| required_fields | A required field is missing or null |
| pollutant_validity | Pollutant is not in the supported list |
| timestamp_validity | Timestamp is not a valid date |
| pollutant_range | Value is outside the valid range for the pollutant |
| unit_consistency | Unit is not allowed for the pollutant |
| null_value | Value field is null |

## AQI Calculation Methodology

### Standard
The AQI calculation follows the **Indian CPCB (Central Pollution Control Board)** sub-index methodology.

### Method
1. For each pollutant, calculate a **sub-index** using linear interpolation between concentration breakpoints
2. The overall AQI is the **maximum** of all pollutant sub-indices
3. The AQI category is determined from the AQI value

### Sub-Index Breakpoints

#### PM2.5 (ug/m3)
| Concentration Low | Concentration High | AQI Low | AQI High |
|-------------------|-------------------|---------|----------|
| 0 | 30 | 0 | 50 |
| 31 | 60 | 51 | 100 |
| 61 | 90 | 101 | 150 |
| 91 | 120 | 151 | 200 |
| 121 | 250 | 201 | 300 |
| 251 | 500 | 301 | 500 |

#### PM10 (ug/m3)
| Concentration Low | Concentration High | AQI Low | AQI High |
|-------------------|-------------------|---------|----------|
| 0 | 50 | 0 | 50 |
| 51 | 100 | 51 | 100 |
| 101 | 250 | 101 | 150 |
| 251 | 350 | 151 | 200 |
| 351 | 430 | 201 | 300 |
| 431 | 560 | 301 | 500 |

#### NO2 (ug/m3)
| Concentration Low | Concentration High | AQI Low | AQI High |
|-------------------|-------------------|---------|----------|
| 0 | 40 | 0 | 50 |
| 41 | 80 | 51 | 100 |
| 81 | 180 | 101 | 150 |
| 181 | 280 | 151 | 200 |
| 281 | 400 | 201 | 300 |
| 401 | 600 | 301 | 500 |

#### SO2 (ug/m3)
| Concentration Low | Concentration High | AQI Low | AQI High |
|-------------------|-------------------|---------|----------|
| 0 | 40 | 0 | 50 |
| 41 | 80 | 51 | 100 |
| 81 | 380 | 101 | 150 |
| 381 | 800 | 151 | 200 |
| 801 | 1600 | 201 | 300 |
| 1601 | 2400 | 301 | 500 |

#### CO (mg/m3)
| Concentration Low | Concentration High | AQI Low | AQI High |
|-------------------|-------------------|---------|----------|
| 0 | 1.0 | 0 | 50 |
| 1.1 | 2.0 | 51 | 100 |
| 2.1 | 10 | 101 | 150 |
| 11 | 17 | 151 | 200 |
| 18 | 34 | 201 | 300 |
| 35 | 50 | 301 | 500 |

#### O3 (ug/m3)
| Concentration Low | Concentration High | AQI Low | AQI High |
|-------------------|-------------------|---------|----------|
| 0 | 50 | 0 | 50 |
| 51 | 100 | 51 | 100 |
| 101 | 168 | 101 | 150 |
| 169 | 208 | 151 | 200 |
| 209 | 748 | 201 | 300 |
| 749 | 1000 | 301 | 500 |

### AQI Categories

| AQI Range | Category | Color |
|-----------|----------|-------|
| 0-50 | Good | Green |
| 51-100 | Satisfactory | Lime |
| 101-150 | Moderate | Yellow |
| 151-200 | Poor | Orange |
| 201-300 | Very Poor | Red |
| 301-500 | Severe | Dark Red |

### Formula
```
Sub-Index = ((AQI_High - AQI_Low) / (Conc_High - Conc_Low)) * (Concentration - Conc_Low) + AQI_Low

AQI = max(all sub-indices)
```

## Weather Enrichment Join Strategy

### Join Key
Air quality data is joined with weather data using:
- **City name** matches weather **location_name**
- **Hourly alignment**: AQ timestamp truncated to the hour matches weather hourly timestamp

### Time Alignment
- Weather data is hourly
- AQ data may have sub-hourly timestamps
- Join key: `(city, hour)` where hour = `timestamp[:13]` (YYYY-MM-DDTHH)
- If no exact hour match, the AQ record has null weather fields (no interpolation)

## Referential Integrity Check

After validation, the pipeline checks that air quality records can be joined with weather records by city + hour. The join count and orphan count are reported in pipeline logs.

## Staging Layer

### Purpose

The staging layer is a persistent intermediate store between raw ingestion and final validation/loading. It contains standardized data with:
- Normalized column names (lowercase, consistent naming)
- Normalized timestamps (ISO 8601 UTC)
- Normalized pollutant names and units
- Consistent data types
- Source and run metadata for traceability

### Files

| File | Location | Written By |
|------|----------|------------|
| Air quality staging | `data/staging/openaq/openaq_YYYYMMDD_HHMMSS.csv` | `pipeline/staging.py:write_staging_openaq()` |
| Weather staging | `data/staging/openmeteo/openmeteo_YYYYMMDD_HHMMSS.csv` | `pipeline/staging.py:write_staging_openmeteo()` |

### Timing

Staging files are written after transformation (Step 4.5) and before quality validation (Step 5). This ensures the staging layer contains normalized data that has not yet been filtered by quality checks, preserving the full transformed dataset for reproducibility.

### Air Quality Staging Fields

| Field | Type | Description |
|-------|------|-------------|
| station_id | text | Monitoring station identifier |
| station_name | text | Station display name |
| city | text | City where station is located |
| country | text | Country code |
| latitude | double | Station latitude |
| longitude | double | Station longitude |
| measurement_time | text (ISO 8601) | Measurement timestamp in UTC |
| pollutant | text | Normalized pollutant name (lowercase) |
| value | double | Measured concentration value |
| unit | text | Canonical measurement unit |
| source | text | Data source identifier (openaq) |
| ingestion_run_id | text | FK to ingestion_runs |

### Weather Staging Fields

| Field | Type | Description |
|-------|------|-------------|
| location_name | text | Location/city name |
| latitude | double | Location latitude |
| longitude | double | Location longitude |
| measurement_time | text (ISO 8601) | Hourly timestamp in UTC |
| temperature | double | Temperature in °C |
| humidity | double | Relative humidity % |
| precipitation | double | Precipitation in mm |
| wind_speed | double | Wind speed in km/h |
| wind_direction | double | Wind direction in degrees |
| source | text | Data source identifier (openmeteo) |
| ingestion_run_id | text | FK to ingestion_runs |
