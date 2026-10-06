"""
Backfill 30 days of realistic historical air quality + weather data
into the database so the ML pipeline has enough data to train on.

This generates sample data using the same structure as the ingestion
sample fallback, but covers 30 days instead of 3.

Usage:
    python -m pipeline.backfill_historical
"""
import json
import random
from datetime import datetime, timezone, timedelta

import requests

from config import API_BASE, get_headers, CITIES


POLLUTANTS = [
    ("pm25", "ug/m3", 20, 120),
    ("pm10", "ug/m3", 40, 200),
    ("co", "mg/m3", 0.2, 3.0),
    ("no2", "ug/m3", 10, 120),
    ("so2", "ug/m3", 2, 80),
    ("o3", "ug/m3", 10, 180),
]

STATIONS_PER_CITY = [
    {"id": "DEL-001", "name": "Delhi Central"},
    {"id": "DEL-002", "name": "Delhi Industrial"},
    {"id": "MUM-001", "name": "Mumbai Central"},
    {"id": "MUM-002", "name": "Mumbai Residential"},
    {"id": "CHE-001", "name": "Chennai Central"},
    {"id": "KOL-001", "name": "Kolkata Central"},
    {"id": "KOL-002", "name": "Kolkata Industrial"},
    {"id": "BEN-001", "name": "Bengaluru Central"},
    {"id": "BEN-002", "name": "Bengaluru Residential"},
    {"id": "CHE-002", "name": "Chennai Industrial"},
]

CITY_STATION_MAP = {
    "Delhi": ["DEL-001", "DEL-002"],
    "Mumbai": ["MUM-001", "MUM-002"],
    "Chennai": ["CHE-001", "CHE-002"],
    "Kolkata": ["KOL-001", "KOL-002"],
    "Bengaluru": ["BEN-001", "BEN-002"],
}

STATION_INFO = {s["id"]: s for s in STATIONS_PER_CITY}


def generate_historical_aq(days=30):
    """Generate realistic air quality records for the past N days."""
    records = []
    end = datetime.now(timezone.utc).replace(hour=12, minute=0, second=0, microsecond=0)

    for city_name, city_info in CITIES.items():
        station_ids = CITY_STATION_MAP.get(city_name, [])
        for day_offset in range(days, 0, -1):
            date = end - timedelta(days=day_offset)
            for station_id in station_ids:
                station = STATION_INFO.get(station_id, {"name": f"{city_name} Station"})
                for pollutant, unit, base_min, base_max in POLLUTANTS:
                    val = round(random.uniform(base_min, base_max) + random.gauss(0, 5), 2)
                    val = max(0, val)
                    records.append({
                        "station_id": station_id,
                        "station_name": station["name"],
                        "city": city_name,
                        "country": "IN",
                        "latitude": city_info["lat"],
                        "longitude": city_info["lon"],
                        "measurement_time": date.strftime("%Y-%m-%dT%H:00:00Z"),
                        "pollutant": pollutant,
                        "value": val,
                        "unit": unit,
                        "source": "backfill",
                        "ingestion_run_id": "backfill_historical",
                    })
    return records


def generate_historical_weather(days=30):
    """Generate realistic weather records for the past N days."""
    records = []
    end = datetime.now(timezone.utc).replace(hour=12, minute=0, second=0, microsecond=0)

    for city_name, city_info in CITIES.items():
        base_temp = 25 + random.uniform(-5, 5)
        for day_offset in range(days, 0, -1):
            date = end - timedelta(days=day_offset)
            for hour in range(0, 24, 3):
                ts = date.replace(hour=hour)
                records.append({
                    "location_name": city_name,
                    "latitude": city_info["lat"],
                    "longitude": city_info["lon"],
                    "measurement_time": ts.strftime("%Y-%m-%dT%H:00:00Z"),
                    "temperature": round(base_temp + random.gauss(0, 3) + 5 * (hour - 12) / 12, 1),
                    "humidity": round(random.uniform(30, 90), 1),
                    "precipitation": round(random.choice([0, 0, 0, 0, random.uniform(0, 10)]), 1),
                    "wind_speed": round(random.uniform(2, 25), 1),
                    "wind_direction": random.randint(0, 359),
                    "source": "backfill",
                    "ingestion_run_id": "backfill_historical",
                })
    return records


def insert_in_batches(table_name, records, batch_size=500):
    """Insert records into a Supabase table in batches."""
    headers = get_headers()
    total_inserted = 0

    for i in range(0, len(records), batch_size):
        batch = records[i:i + batch_size]
        resp = requests.post(
            f"{API_BASE}/{table_name}",
            headers=headers,
            json=batch,
            timeout=60,
        )
        if resp.ok:
            total_inserted += len(batch)
            print(f"  Inserted batch {i // batch_size + 1}: {len(batch)} records")
        else:
            print(f"  ERROR inserting batch {i // batch_size + 1}: {resp.status_code} {resp.text[:200]}")
        if len(records) > batch_size and i % (batch_size * 4) == 0 and i > 0:
            print(f"  Progress: {total_inserted}/{len(records)}")

    return total_inserted


def main():
    print("=" * 60)
    print("  HISTORICAL DATA BACKFILL — 30 days")
    print("=" * 60)

    random.seed(42)

    # Generate air quality data
    print("\n--- Generating air quality data ---")
    aq_records = generate_historical_aq(days=30)
    print(f"  Generated {len(aq_records)} AQ records")

    # Generate weather data
    print("\n--- Generating weather data ---")
    weather_records = generate_historical_weather(days=30)
    print(f"  Generated {len(weather_records)} weather records")

    # Insert air quality data
    print("\n--- Inserting air quality data ---")
    aq_inserted = insert_in_batches("air_quality_measurements", aq_records)
    print(f"  Total AQ inserted: {aq_inserted}")

    # Insert weather data (upsert to avoid duplicate key errors)
    print("\n--- Inserting weather data ---")
    headers = get_headers()
    headers["Prefer"] = "return=representation,resolution=merge-duplicates"
    w_inserted = 0
    for i in range(0, len(weather_records), 500):
        batch = weather_records[i:i + 500]
        resp = requests.post(
            f"{API_BASE}/weather_measurements?on_conflict=location_name,latitude,longitude,measurement_time",
            headers=headers,
            json=batch,
            timeout=60,
        )
        if resp.ok:
            w_inserted += len(batch)
        else:
            print(f"  ERROR weather batch {i//500+1}: {resp.status_code} {resp.text[:200]}")
    print(f"  Total weather inserted: {w_inserted}")

    # Rebuild gold table
    print("\n--- Rebuilding gold analytical table ---")
    from pipeline.aggregate import build_gold_table
    from pipeline.load import load_gold_records

    gold_records = build_gold_table(pipeline_run_id="backfill_historical")
    print(f"  Built {len(gold_records)} gold records")

    if gold_records:
        loaded = load_gold_records(gold_records)
        print(f"  Loaded {loaded} gold records to database")

    print("\n" + "=" * 60)
    print("  BACKFILL COMPLETE")
    print("=" * 60)


if __name__ == "__main__":
    main()
