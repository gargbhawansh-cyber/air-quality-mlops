-- Add weather enrichment columns to air_quality_measurements
-- These columns are populated by transform.py's enrich_with_weather() function
-- but were missing from the original schema, causing PGRST204 errors on insert.

ALTER TABLE air_quality_measurements
  ADD COLUMN IF NOT EXISTS weather_temperature  double precision,
  ADD COLUMN IF NOT EXISTS weather_humidity     double precision,
  ADD COLUMN IF NOT EXISTS weather_precipitation double precision,
  ADD COLUMN IF NOT EXISTS weather_wind_speed    double precision;
