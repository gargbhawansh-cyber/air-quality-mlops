"""
Extract module — reads raw data from the raw landing layer
and prepares it for transformation.
"""
import json
from pathlib import Path
from config import RAW_DIR


def extract_openaq_raw(run_id=None):
    """Extract OpenAQ raw data from the raw landing layer."""
    raw_path = RAW_DIR / "openaq"
    if not raw_path.exists():
        return []

    all_records = []
    run_dirs = sorted(raw_path.iterdir()) if raw_path.exists() else []

    if run_id:
        target = raw_path / run_id
        run_dirs = [target] if target.exists() else []

    for run_dir in run_dirs:
        if not run_dir.is_dir():
            continue
        for f in run_dir.glob("*.json"):
            with open(f) as fh:
                data = json.load(fh)
                if isinstance(data, list):
                    all_records.extend(data)
                elif isinstance(data, dict) and "results" in data:
                    all_records.extend(data["results"])

    return all_records


def extract_openmeteo_raw(run_id=None):
    """Extract Open-Meteo raw data from the raw landing layer."""
    raw_path = RAW_DIR / "openmeteo"
    if not raw_path.exists():
        return []

    all_records = []
    run_dirs = sorted(raw_path.iterdir()) if raw_path.exists() else []

    if run_id:
        target = raw_path / run_id
        run_dirs = [target] if target.exists() else []

    for run_dir in run_dirs:
        if not run_dir.is_dir():
            continue
        for f in run_dir.glob("*.json"):
            with open(f) as fh:
                data = json.load(fh)
                if isinstance(data, list):
                    all_records.extend(data)

    return all_records


def extract_latest_raw():
    """Extract the most recent raw data from both sources."""
    openaq_records = extract_openaq_raw()
    weather_records = extract_openmeteo_raw()
    return openaq_records, weather_records
