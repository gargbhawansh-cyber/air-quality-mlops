"""
Staging module — writes normalized records to persistent staging files.

The staging layer sits between raw ingestion and final validation/loading.
It contains standardized data with:
  - normalized column names
  - normalized timestamps (ISO 8601 UTC)
  - normalized pollutant names and units
  - consistent data types
  - source and run metadata

Files are timestamped so every pipeline run is reproducible.
"""
import csv
from datetime import datetime, timezone
from pathlib import Path

from config import STAGING_DIR


def _ensure_dirs():
    """Create staging subdirectories if they don't exist."""
    (STAGING_DIR / "openaq").mkdir(parents=True, exist_ok=True)
    (STAGING_DIR / "openmeteo").mkdir(parents=True, exist_ok=True)


def _timestamp():
    return datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")


def write_staging_openaq(records, run_id):
    """
    Write normalized air quality records to a timestamped CSV staging file.

    Returns the path to the staging file.
    """
    _ensure_dirs()
    ts = _timestamp()
    path = STAGING_DIR / "openaq" / f"openaq_{ts}.csv"

    if not records:
        return None

    fieldnames = [
        "station_id", "station_name", "city", "country",
        "latitude", "longitude", "measurement_time",
        "pollutant", "value", "unit",
        "source", "ingestion_run_id",
    ]

    with open(path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        for r in records:
            writer.writerow(r)

    print(f"[STAGING] Wrote {len(records)} air quality records to {path}")
    return path


def write_staging_openmeteo(records, run_id):
    """
    Write normalized weather records to a timestamped CSV staging file.

    Returns the path to the staging file.
    """
    _ensure_dirs()
    ts = _timestamp()
    path = STAGING_DIR / "openmeteo" / f"openmeteo_{ts}.csv"

    if not records:
        return None

    fieldnames = [
        "location_name", "latitude", "longitude", "measurement_time",
        "temperature", "humidity", "precipitation",
        "wind_speed", "wind_direction",
        "source", "ingestion_run_id",
    ]

    with open(path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        for r in records:
            writer.writerow(r)

    print(f"[STAGING] Wrote {len(records)} weather records to {path}")
    return path


def read_staging_openaq(filepath=None):
    """
    Read air quality records from a staging CSV file.
    If no filepath given, reads the most recent staging file.
    """
    staging_path = STAGING_DIR / "openaq"
    if filepath:
        path = Path(filepath)
    elif staging_path.exists():
        files = sorted(staging_path.glob("openaq_*.csv"))
        if not files:
            return []
        path = files[-1]
    else:
        return []

    records = []
    with open(path) as f:
        reader = csv.DictReader(f)
        for row in reader:
            # Convert numeric fields
            for num_field in ["latitude", "longitude", "value"]:
                val = row.get(num_field)
                if val and val != "None" and val != "":
                    try:
                        row[num_field] = float(val)
                    except (ValueError, TypeError):
                        row[num_field] = None
                else:
                    row[num_field] = None
            records.append(row)

    return records


def read_staging_openmeteo(filepath=None):
    """
    Read weather records from a staging CSV file.
    If no filepath given, reads the most recent staging file.
    """
    staging_path = STAGING_DIR / "openmeteo"
    if filepath:
        path = Path(filepath)
    elif staging_path.exists():
        files = sorted(staging_path.glob("openmeteo_*.csv"))
        if not files:
            return []
        path = files[-1]
    else:
        return []

    records = []
    with open(path) as f:
        reader = csv.DictReader(f)
        for row in reader:
            for num_field in ["latitude", "longitude", "temperature", "humidity",
                              "precipitation", "wind_speed", "wind_direction"]:
                val = row.get(num_field)
                if val and val != "None" and val != "":
                    try:
                        row[num_field] = float(val)
                    except (ValueError, TypeError):
                        row[num_field] = None
                else:
                    row[num_field] = None
            records.append(row)

    return records
