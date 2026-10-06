"""
OpenAQ data ingestion module.
Fetches air quality measurements from the OpenAQ API with fallback to sample data.
Preserves raw API responses in the raw landing layer.
"""
import json
import os
import time
from datetime import datetime, timezone, timedelta
from pathlib import Path
import requests

from config import (
    OPENAQ_API_BASE, OPENAQ_API_KEY, CITIES, RAW_DIR,
    REQUEST_TIMEOUT, REQUEST_RETRIES, USE_SAMPLE_FALLBACK,
)
from ingestion.ingestion_logger import generate_run_id, log_ingestion_run, update_ingestion_run


def fetch_openaq_live(city_name, lat, lon, hours_back=72):
    """Fetch recent measurements from OpenAQ v3 API for a city."""
    end = datetime.now(timezone.utc)
    start = end - timedelta(hours=hours_back)

    url = f"{OPENAQ_API_BASE}/measurements"
    headers = {"Accept": "application/json"}
    if OPENAQ_API_KEY:
        headers["X-API-Key"] = OPENAQ_API_KEY

    params = {
        "coordinates": f"{lat},{lon}",
        "radius": 25000,
        "date_from": start.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "date_to": end.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "parameter": "pm25,pm10,co,no2,so2,o3",
        "limit": 200,
        "order_by": "date",
        "sort": "asc",
    }

    for attempt in range(REQUEST_RETRIES):
        try:
            resp = requests.get(url, headers=headers, params=params, timeout=REQUEST_TIMEOUT)
            if resp.ok:
                data = resp.json()
                results = data.get("results", data.get("data", []))
                return results, "live"
            elif resp.status_code == 429:
                time.sleep(5 * (attempt + 1))
                continue
            else:
                print(f"[OPENAQ] API returned {resp.status_code}")
                break
        except requests.exceptions.Timeout:
            print(f"[OPENAQ] Timeout on attempt {attempt+1}")
            time.sleep(3)
        except Exception as e:
            print(f"[OPENAQ] Error: {e}")
            time.sleep(3)

    return [], "sample"


def generate_sample_openaq(city_name, lat, lon, hours_back=72):
    """Generate realistic sample data based on public-source structure for OpenAQ v3."""
    import random
    results = []
    end = datetime.now(timezone.utc)
    stations = [
        {"id": f"{city_name[:3].upper()}-001", "name": f"{city_name} Central"},
        {"id": f"{city_name[:3].upper()}-002", "name": f"{city_name} Industrial"},
        {"id": f"{city_name[:3].upper()}-003", "name": f"{city_name} Residential"},
    ]
    pollutants = [
        ("pm25", "ug/m3", 20, 120),
        ("pm10", "ug/m3", 40, 200),
        ("co", "mg/m3", 0.2, 3.0),
        ("no2", "ug/m3", 10, 120),
        ("so2", "ug/m3", 2, 80),
        ("o3", "ug/m3", 10, 180),
    ]

    for h in range(hours_back):
        ts = end - timedelta(hours=h)
        for station in stations:
            for pollutant, unit, base_min, base_max in pollutants:
                val = round(random.uniform(base_min, base_max) + random.gauss(0, 5), 2)
                val = max(0, val)
                results.append({
                    "parameter": pollutant,
                    "value": val,
                    "unit": unit,
                    "date": {"utc": ts.strftime("%Y-%m-%dT%H:%M:%SZ")},
                    "locationId": station["id"],
                    "location": station["name"],
                    "city": city_name,
                    "country": "IN",
                    "coordinates": {"latitude": lat, "longitude": lon},
                })
    return results


def save_raw_data(run_id, source, data):
    """Save raw API response to timestamped file."""
    raw_dir = RAW_DIR / "openaq" / run_id
    raw_dir.mkdir(parents=True, exist_ok=True)
    filename = f"{source}_{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}.json"
    filepath = raw_dir / filename
    with open(filepath, "w") as f:
        json.dump(data, f, indent=2)
    return filepath


def ingest_openaq():
    """Main ingestion entry point for OpenAQ data."""
    run_id = generate_run_id("openaq")
    print(f"[OPENAQ] Starting ingestion run: {run_id}")

    all_records = []
    data_source = "live"
    total_errors = 0

    for city_name, city_info in CITIES.items():
        print(f"[OPENAQ] Fetching data for {city_name}...")
        records, src = fetch_openaq_live(city_name, city_info["lat"], city_info["lon"])

        if not records and USE_SAMPLE_FALLBACK:
            print(f"[OPENAQ] No live data for {city_name}, using sample fallback")
            records = generate_sample_openaq(city_name, city_info["lat"], city_info["lon"])
            data_source = "sample"

        if not records:
            total_errors += 1
            print(f"[OPENAQ] No data available for {city_name}")
            continue

        # Tag city if not present
        for r in records:
            if "city" not in r or not r["city"]:
                r["city"] = city_name
            if "coordinates" not in r or not r.get("coordinates"):
                r["coordinates"] = {"latitude": city_info["lat"], "longitude": city_info["lon"]}

        all_records.extend(records)
        print(f"[OPENAQ] {city_name}: {len(records)} records ({src})")

    # Save raw data
    if all_records:
        save_raw_data(run_id, "openaq", all_records)

    status = "success" if all_records else "failed"
    error_msg = "" if all_records else "No data retrieved from any source"

    log_ingestion_run(
        run_id=run_id,
        source="openaq",
        status=status,
        row_count=len(all_records),
        endpoint=f"{OPENAQ_API_BASE}/measurements",
        error_message=error_msg,
        data_source=data_source,
    )

    print(f"[OPENAQ] Ingestion complete: {len(all_records)} records, source={data_source}")
    return {
        "run_id": run_id,
        "source": "openaq",
        "records": all_records,
        "row_count": len(all_records),
        "data_source": data_source,
        "status": status,
    }


if __name__ == "__main__":
    result = ingest_openaq()
    print(f"Done: {result['row_count']} records")
