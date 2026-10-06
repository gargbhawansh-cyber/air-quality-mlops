"""
Open-Meteo weather data ingestion module.
Fetches historical weather data from the Open-Meteo Archive API with fallback to sample data.
Preserves raw API responses in the raw landing layer.
"""
import json
import random
import time
from datetime import datetime, timezone, timedelta
from pathlib import Path
import requests

from config import (
    OPENMETEO_ARCHIVE_BASE, CITIES, RAW_DIR,
    REQUEST_TIMEOUT, REQUEST_RETRIES, USE_SAMPLE_FALLBACK,
)
from ingestion.ingestion_logger import generate_run_id, log_ingestion_run


def fetch_openmeteo_live(city_name, lat, lon, hours_back=72):
    """Fetch hourly historical weather from Open-Meteo Archive API."""
    end = datetime.now(timezone.utc)
    start = end - timedelta(hours=hours_back)

    url = OPENMETEO_ARCHIVE_BASE
    params = {
        "latitude": lat,
        "longitude": lon,
        "start_date": start.strftime("%Y-%m-%d"),
        "end_date": end.strftime("%Y-%m-%d"),
        "hourly": "temperature_2m,relative_humidity_2m,precipitation,wind_speed_10m,wind_direction_10m",
        "timezone": "UTC",
    }

    for attempt in range(REQUEST_RETRIES):
        try:
            resp = requests.get(url, params=params, timeout=REQUEST_TIMEOUT)
            if resp.ok:
                data = resp.json()
                return data, "live"
            else:
                print(f"[OPENMETEO] API returned {resp.status_code}")
                break
        except requests.exceptions.Timeout:
            print(f"[OPENMETEO] Timeout on attempt {attempt+1}")
            time.sleep(3)
        except Exception as e:
            print(f"[OPENMETEO] Error: {e}")
            time.sleep(3)

    return {}, "sample"


def generate_sample_openmeteo(city_name, lat, lon, hours_back=72):
    """Generate realistic sample weather data based on Open-Meteo API structure."""
    end = datetime.now(timezone.utc)
    start = end - timedelta(hours=hours_back)

    times = []
    current = start.replace(minute=0, second=0, microsecond=0)
    while current <= end:
        times.append(current.strftime("%Y-%m-%dT%H:00"))
        current += timedelta(hours=1)

    base_temp = 25 + random.uniform(-5, 5)
    hourly_data = {
        "time": times,
        "temperature_2m": [round(base_temp + random.gauss(0, 3) + 5 * (i % 24 - 12) / 12, 1) for i in range(len(times))],
        "relative_humidity_2m": [round(random.uniform(30, 90), 1) for _ in range(len(times))],
        "precipitation": [round(random.choice([0, 0, 0, 0, random.uniform(0, 10)]), 1) for _ in range(len(times))],
        "wind_speed_10m": [round(random.uniform(2, 25), 1) for _ in range(len(times))],
        "wind_direction_10m": [random.randint(0, 359) for _ in range(len(times))],
    }

    return {
        "latitude": lat,
        "longitude": lon,
        "timezone": "UTC",
        "hourly": hourly_data,
    }


def save_raw_data(run_id, source, data):
    """Save raw API response to timestamped file."""
    raw_dir = RAW_DIR / "openmeteo" / run_id
    raw_dir.mkdir(parents=True, exist_ok=True)
    filename = f"{source}_{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}.json"
    filepath = raw_dir / filename
    with open(filepath, "w") as f:
        json.dump(data, f, indent=2)
    return filepath


def ingest_openmeteo():
    """Main ingestion entry point for Open-Meteo weather data."""
    run_id = generate_run_id("openmeteo")
    print(f"[OPENMETEO] Starting ingestion run: {run_id}")

    all_records = []
    data_source = "live"
    total_errors = 0

    for city_name, city_info in CITIES.items():
        print(f"[OPENMETEO] Fetching weather for {city_name}...")
        data, src = fetch_openmeteo_live(city_name, city_info["lat"], city_info["lon"])

        if not data and USE_SAMPLE_FALLBACK:
            print(f"[OPENMETEO] No live data for {city_name}, using sample fallback")
            data = generate_sample_openmeteo(city_name, city_info["lat"], city_info["lon"])
            data_source = "sample"

        if not data:
            total_errors += 1
            print(f"[OPENMETEO] No data available for {city_name}")
            continue

        # Normalize the hourly data into records
        hourly = data.get("hourly", {})
        times = hourly.get("time", [])
        for i, ts_str in enumerate(times):
            record = {
                "location_name": city_name,
                "latitude": data.get("latitude", city_info["lat"]),
                "longitude": data.get("longitude", city_info["lon"]),
                "measurement_time": ts_str,
                "temperature": hourly.get("temperature_2m", [None] * len(times))[i],
                "humidity": hourly.get("relative_humidity_2m", [None] * len(times))[i],
                "precipitation": hourly.get("precipitation", [None] * len(times))[i],
                "wind_speed": hourly.get("wind_speed_10m", [None] * len(times))[i],
                "wind_direction": hourly.get("wind_direction_10m", [None] * len(times))[i],
            }
            all_records.append(record)

        print(f"[OPENMETEO] {city_name}: {len(times)} hourly records ({src})")

    # Save raw data
    if all_records:
        save_raw_data(run_id, "openmeteo", all_records)

    status = "success" if all_records else "failed"
    error_msg = "" if all_records else "No data retrieved from any source"

    log_ingestion_run(
        run_id=run_id,
        source="openmeteo",
        status=status,
        row_count=len(all_records),
        endpoint=OPENMETEO_ARCHIVE_BASE,
        error_message=error_msg,
        data_source=data_source,
    )

    print(f"[OPENMETEO] Ingestion complete: {len(all_records)} records, source={data_source}")
    return {
        "run_id": run_id,
        "source": "openmeteo",
        "records": all_records,
        "row_count": len(all_records),
        "data_source": data_source,
        "status": status,
    }


if __name__ == "__main__":
    result = ingest_openmeteo()
    print(f"Done: {result['row_count']} records")
