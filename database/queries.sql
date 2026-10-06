-- =============================================================================
-- Air Quality Index Pipeline — Analytical Queries
-- =============================================================================
-- Common queries used by the dashboard and for ad-hoc analysis.
-- =============================================================================

-- 1. Latest AQI by station
SELECT date, city, station_id, station_name, aqi, aqi_category, observation_count
FROM gold_air_quality_daily
WHERE date = (SELECT max(date) FROM gold_air_quality_daily)
ORDER BY aqi DESC;

-- 2. Average AQI by city
SELECT city, round(avg(aqi)) as avg_aqi, max(aqi) as max_aqi, count(*) as records
FROM gold_air_quality_daily
WHERE aqi IS NOT NULL
GROUP BY city
ORDER BY avg_aqi DESC;

-- 3. Average pollutant values by city
SELECT city,
    round(avg(avg_pm25)) as avg_pm25,
    round(avg(avg_pm10)) as avg_pm10,
    round(avg(avg_no2)) as avg_no2,
    round(avg(avg_so2)) as avg_so2,
    round(avg(avg_co)) as avg_co,
    round(avg(avg_o3)) as avg_o3
FROM gold_air_quality_daily
GROUP BY city
ORDER BY city;

-- 4. Weather correlation with AQI
SELECT city,
    round(avg(aqi)) as avg_aqi,
    round(avg(avg_temperature)) as avg_temp,
    round(avg(avg_humidity)) as avg_humidity,
    round(avg(avg_rainfall)) as avg_rain,
    round(avg(avg_wind_speed)) as avg_wind
FROM gold_air_quality_daily
WHERE aqi IS NOT NULL
GROUP BY city;

-- 5. AQI trend over time
SELECT date, city, station_name, aqi, aqi_category
FROM gold_air_quality_daily
ORDER BY date ASC, city, station_name;

-- 6. Data quality summary for latest run
SELECT source, total_records, valid_records, rejected_records,
       duplicate_records, missing_value_count, validation_failures,
       schema_valid, checks_passed, checks_failed
FROM data_quality_summary
WHERE pipeline_run_id = (SELECT run_id FROM pipeline_runs ORDER BY started_at DESC LIMIT 1);

-- 7. Rejected records for latest run
SELECT rejected_id, rejection_reason, validation_rule, rejected_at
FROM rejected_records
WHERE run_id = (SELECT run_id FROM pipeline_runs ORDER BY started_at DESC LIMIT 1)
ORDER BY rejected_at DESC;

-- 8. Ingestion run history
SELECT run_id, source, extraction_time, status, row_count, data_source
FROM ingestion_runs
ORDER BY extraction_time DESC
LIMIT 20;

-- 9. Pollutant distribution
SELECT pollutant, city, round(avg(value), 2) as avg_value, count(*) as count
FROM air_quality_measurements
GROUP BY pollutant, city
ORDER BY pollutant, avg_value DESC;

-- 10. Pipeline run summary
SELECT run_id, started_at, completed_at, status,
       total_records, valid_records, rejected_records, gold_records
FROM pipeline_runs
ORDER BY started_at DESC;
