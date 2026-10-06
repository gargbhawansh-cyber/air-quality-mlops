"""
Transform module — normalizes and cleans raw air quality and weather data.
Handles timestamp normalization, station normalization, pollutant normalization,
unit normalization, and weather enrichment joins.
"""
import json
from datetime import datetime, timezone
from collections import defaultdict

from config import UNIT_NORMALIZATION, SUPPORTED_POLLUTANTS
from quality.rules import normalize_unit


def normalize_timestamp(ts_str):
    """Convert various timestamp formats to ISO 8601 UTC."""
    if not ts_str:
        return None
    try:
        ts = ts_str.replace("Z", "+00:00")
        dt = datetime.fromisoformat(ts)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.isoformat()
    except (ValueError, AttributeError):
        try:
            # Try common format: YYYY-MM-DDTHH:MM
            dt = datetime.strptime(ts_str[:16], "%Y-%m-%dT%H:%M")
            return dt.replace(tzinfo=timezone.utc).isoformat()
        except (ValueError, TypeError):
            return None


def normalize_station_name(name):
    """Standardize station names."""
    if not name:
        return "Unknown"
    return name.strip().title()


def transform_air_quality(raw_records, run_id):
    """
    Transform raw OpenAQ records into normalized staging records.
    Returns list of normalized dicts.
    """
    transformed = []

    for record in raw_records:
        # Handle OpenAQ v2/v3 format
        date_obj = record.get("date", {})
        ts_raw = date_obj.get("utc") if isinstance(date_obj, dict) else record.get("measurement_time")

        coords = record.get("coordinates", {})
        if isinstance(coords, dict):
            lat = coords.get("latitude")
            lon = coords.get("longitude")
        else:
            lat = lon = None

        normalized = {
            "station_id": str(record.get("locationId", record.get("station_id", ""))),
            "station_name": normalize_station_name(record.get("location", record.get("station_name", ""))),
            "city": record.get("city", "Unknown"),
            "country": record.get("country"),
            "latitude": lat,
            "longitude": lon,
            "measurement_time": normalize_timestamp(ts_raw),
            "pollutant": record.get("parameter", record.get("pollutant", "")).lower(),
            "value": record.get("value"),
            "unit": normalize_unit(record.get("unit", "")),
            "source": "openaq",
            "ingestion_run_id": run_id,
        }
        transformed.append(normalized)

    return transformed


def transform_weather(raw_records, run_id):
    """
    Transform raw Open-Meteo records into normalized staging records.
    """
    transformed = []

    for record in raw_records:
        normalized = {
            "location_name": record.get("location_name", "Unknown"),
            "latitude": record.get("latitude"),
            "longitude": record.get("longitude"),
            "measurement_time": normalize_timestamp(record.get("measurement_time")),
            "temperature": record.get("temperature"),
            "humidity": record.get("humidity"),
            "precipitation": record.get("precipitation"),
            "wind_speed": record.get("wind_speed"),
            "wind_direction": record.get("wind_direction"),
            "source": "openmeteo",
            "ingestion_run_id": run_id,
        }
        transformed.append(normalized)

    return transformed


def enrich_with_weather(aq_records, weather_records):
    """
    Join air quality data with weather data.
    Strategy: match by city == location_name and nearest hour.
    Weather data is hourly, so we align by truncating AQ timestamp to the hour.
    """
    # Build a lookup: (city, hour) -> weather record
    weather_lookup = {}
    for w in weather_records:
        ts = w.get("measurement_time", "")
        if ts:
            hour_key = ts[:13]  # YYYY-MM-DDTHH
            city = w.get("location_name", "")
            weather_lookup[(city, hour_key)] = w

    enriched = []
    matched = 0
    unmatched = 0

    for aq in aq_records:
        ts = aq.get("measurement_time", "")
        city = aq.get("city", "")
        hour_key = ts[:13] if ts else ""

        weather = weather_lookup.get((city, hour_key))
        if weather:
            aq["weather_temperature"] = weather.get("temperature")
            aq["weather_humidity"] = weather.get("humidity")
            aq["weather_precipitation"] = weather.get("precipitation")
            aq["weather_wind_speed"] = weather.get("wind_speed")
            matched += 1
        else:
            aq["weather_temperature"] = None
            aq["weather_humidity"] = None
            aq["weather_precipitation"] = None
            aq["weather_wind_speed"] = None
            unmatched += 1

        enriched.append(aq)

    print(f"[TRANSFORM] Weather enrichment: {matched} matched, {unmatched} unmatched")
    return enriched
