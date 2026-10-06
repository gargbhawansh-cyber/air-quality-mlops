"""
Fast pipeline runner — does transform/validate in Python,
then uses execute_sql-compatible bulk INSERT for fast loading.
"""
import json
import sys
import os
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from ingestion.openaq_ingest import generate_sample_openaq, save_raw_data as save_aq_raw
from ingestion.openmeteo_ingest import generate_sample_openmeteo, save_raw_data as save_weather_raw
from ingestion.ingestion_logger import generate_run_id, log_ingestion_run
from pipeline.transform import transform_air_quality, transform_weather, enrich_with_weather
from quality.checks import validate_air_quality, validate_weather, check_referential_integrity
from pipeline.aggregate import calculate_aqi, get_aqi_category, calculate_sub_index
from config import CITIES


def generate_data():
    """Generate sample data for all cities."""
    openaq_run_id = generate_run_id("openaq")
    weather_run_id = generate_run_id("openmeteo")

    all_aq = []
    all_weather = []

    for city_name, city_info in CITIES.items():
        # 48 hours of data, 2 stations per city
        aq = generate_sample_openaq(city_name, city_info["lat"], city_info["lon"], hours_back=48)
        # Keep only 2 stations
        station_ids = list(set(r["locationId"] for r in aq))[:2]
        aq = [r for r in aq if r["locationId"] in station_ids]
        all_aq.extend(aq)

        weather = generate_sample_openmeteo(city_name, city_info["lat"], city_info["lon"], hours_back=48)
        # Normalize to records
        hourly = weather.get("hourly", {})
        times = hourly.get("time", [])
        for i, ts_str in enumerate(times):
            record = {
                "location_name": city_name,
                "latitude": weather.get("latitude", city_info["lat"]),
                "longitude": weather.get("longitude", city_info["lon"]),
                "measurement_time": ts_str,
                "temperature": hourly.get("temperature_2m", [None] * len(times))[i],
                "humidity": hourly.get("relative_humidity_2m", [None] * len(times))[i],
                "precipitation": hourly.get("precipitation", [None] * len(times))[i],
                "wind_speed": hourly.get("wind_speed_10m", [None] * len(times))[i],
                "wind_direction": hourly.get("wind_direction_10m", [None] * len(times))[i],
            }
            all_weather.append(record)

    # Save raw
    save_aq_raw(openaq_run_id, "openaq", all_aq)
    save_weather_raw(weather_run_id, "openmeteo", all_weather)

    log_ingestion_run(openaq_run_id, "openaq", "success", len(all_aq), "sample", data_source="sample")
    log_ingestion_run(weather_run_id, "openmeteo", "success", len(all_weather), "sample", data_source="sample")

    return all_aq, all_weather, openaq_run_id, weather_run_id


def transform_and_validate(all_aq, all_weather, openaq_run_id, weather_run_id):
    """Transform and validate data."""
    transformed_aq = transform_air_quality(all_aq, openaq_run_id)
    transformed_weather = transform_weather(all_weather, weather_run_id)

    pipeline_run_id = f"pipeline_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}"

    valid_aq, aq_result = validate_air_quality(transformed_aq, pipeline_run_id)
    valid_weather, weather_result = validate_weather(transformed_weather, pipeline_run_id)

    enriched_aq = enrich_with_weather(valid_aq, valid_weather)
    join_count, orphan_count = check_referential_integrity(valid_aq, valid_weather)

    print(f"AQ: {aq_result}")
    print(f"Weather: {weather_result}")
    print(f"Joins: {join_count}, Orphans: {orphan_count}")

    return enriched_aq, valid_weather, aq_result, weather_result, pipeline_run_id


def build_gold_from_memory(aq_records, weather_records, pipeline_run_id):
    """Build gold table from in-memory data."""
    from collections import defaultdict

    grouped = defaultdict(lambda: {"station_name": "", "city": "", "pollutants": defaultdict(list)})
    for rec in aq_records:
        ts = rec.get("measurement_time", "")
        if not ts:
            continue
        date_str = ts[:10]
        station_id = rec.get("station_id", "")
        key = (date_str, station_id)
        grouped[key]["station_name"] = rec.get("station_name", "")
        grouped[key]["city"] = rec.get("city", "")
        pollutant = rec.get("pollutant", "").lower()
        value = rec.get("value")
        if value is not None:
            grouped[key]["pollutants"][pollutant].append(float(value))

    weather_by_city_date = defaultdict(lambda: {"temp": [], "hum": [], "rain": [], "wind": []})
    for w in weather_records:
        ts = w.get("measurement_time", "")
        if not ts:
            continue
        date_str = ts[:10]
        city = w.get("location_name", "")
        if w.get("temperature") is not None:
            weather_by_city_date[(city, date_str)]["temp"].append(float(w["temperature"]))
        if w.get("humidity") is not None:
            weather_by_city_date[(city, date_str)]["hum"].append(float(w["humidity"]))
        if w.get("precipitation") is not None:
            weather_by_city_date[(city, date_str)]["rain"].append(float(w["precipitation"]))
        if w.get("wind_speed") is not None:
            weather_by_city_date[(city, date_str)]["wind"].append(float(w["wind_speed"]))

    gold_records = []
    for (date_str, station_id), data in grouped.items():
        pollutant_avgs = {}
        for pollutant in ["pm25", "pm10", "no2", "so2", "co", "o3"]:
            values = data["pollutants"].get(pollutant, [])
            pollutant_avgs[pollutant] = round(sum(values) / len(values), 2) if values else None

        weather = weather_by_city_date.get((data["city"], date_str), {})
        avg_temp = round(sum(weather["temp"]) / len(weather["temp"]), 2) if weather["temp"] else None
        avg_hum = round(sum(weather["hum"]) / len(weather["hum"]), 2) if weather["hum"] else None
        avg_rain = round(sum(weather["rain"]) / len(weather["rain"]), 2) if weather["rain"] else None
        avg_wind = round(sum(weather["wind"]) / len(weather["wind"]), 2) if weather["wind"] else None

        aqi, aqi_category = calculate_aqi(pollutant_avgs)
        total_obs = sum(len(v) for v in data["pollutants"].values())

        gold_records.append({
            "date": date_str,
            "city": data["city"],
            "station_id": station_id,
            "station_name": data["station_name"],
            "avg_pm25": pollutant_avgs.get("pm25"),
            "avg_pm10": pollutant_avgs.get("pm10"),
            "avg_no2": pollutant_avgs.get("no2"),
            "avg_so2": pollutant_avgs.get("so2"),
            "avg_co": pollutant_avgs.get("co"),
            "avg_o3": pollutant_avgs.get("o3"),
            "avg_temperature": avg_temp,
            "avg_humidity": avg_hum,
            "avg_rainfall": avg_rain,
            "avg_wind_speed": avg_wind,
            "aqi": aqi,
            "aqi_category": aqi_category,
            "observation_count": total_obs,
            "pipeline_run_id": pipeline_run_id,
        })

    return gold_records


def save_to_json(data, filepath):
    """Save data to a JSON file."""
    Path(filepath).parent.mkdir(parents=True, exist_ok=True)
    with open(filepath, "w") as f:
        json.dump(data, f, default=str, indent=2)


def main():
    print("=== Generating sample data ===")
    all_aq, all_weather, openaq_run_id, weather_run_id = generate_data()
    print(f"AQ: {len(all_aq)}, Weather: {len(all_weather)}")

    print("\n=== Transforming and validating ===")
    valid_aq, valid_weather, aq_result, weather_result, pipeline_run_id = transform_and_validate(
        all_aq, all_weather, openaq_run_id, weather_run_id
    )
    print(f"Valid AQ: {len(valid_aq)}, Valid Weather: {len(valid_weather)}")
    print(f"Pipeline run ID: {pipeline_run_id}")

    print("\n=== Building gold table ===")
    gold_records = build_gold_from_memory(valid_aq, valid_weather, pipeline_run_id)
    print(f"Gold records: {len(gold_records)}")

    # Save all data to JSON for bulk loading
    save_to_json(valid_aq, "data/processed/valid_aq.json")
    save_to_json(valid_weather, "data/processed/valid_weather.json")
    save_to_json(gold_records, "data/processed/gold_records.json")
    save_to_json(aq_result.rejected_records + weather_result.rejected_records, "data/processed/rejected.json")

    # Save pipeline summary
    summary = {
        "run_id": pipeline_run_id,
        "started_at": datetime.now(timezone.utc).isoformat(),
        "status": "success",
        "total_records": len(all_aq) + len(all_weather),
        "valid_records": len(valid_aq) + len(valid_weather),
        "rejected_records": len(aq_result.rejected_records) + len(weather_result.rejected_records),
        "duplicate_records": aq_result.duplicates + weather_result.duplicates,
        "missing_value_count": aq_result.missing_values + weather_result.missing_values,
        "validation_failures": aq_result.validation_failures + weather_result.validation_failures,
        "gold_records": len(gold_records),
        "data_source": "sample",
    }
    save_to_json(summary, "data/processed/pipeline_summary.json")
    save_to_json({
        "pipeline_run_id": pipeline_run_id,
        "aq_summary": aq_result.to_dict(),
        "weather_summary": weather_result.to_dict(),
    }, "data/processed/quality_summary.json")

    print(f"\n=== Done! ===")
    print(f"Pipeline: {pipeline_run_id}")
    print(f"Total: {summary['total_records']}, Valid: {summary['valid_records']}")
    print(f"Rejected: {summary['rejected_records']}, Gold: {summary['gold_records']}")
    print(f"Data saved to data/processed/")

    return summary


if __name__ == "__main__":
    main()
