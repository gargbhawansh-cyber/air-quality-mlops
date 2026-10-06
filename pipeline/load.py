"""
Load module — loads validated data into PostgreSQL/Supabase via REST API.
"""
import json
import time
import requests
from datetime import datetime, timezone

from config import API_BASE, get_headers


def _batch_insert(table, records, batch_size=500, upsert=False, on_conflict=None):
    """Insert records in batches via Supabase REST API.

    When upsert=True, uses the Prefer: resolution=merge-duplicates header
    with an on_conflict query parameter so re-runs update existing rows
    instead of producing 409 duplicate key errors.
    """
    if not records:
        return 0

    headers = get_headers()
    query_params = ""
    if upsert:
        headers["Prefer"] = "return=representation,resolution=merge-duplicates"
        if on_conflict:
            query_params = f"?on_conflict={on_conflict}"

    total_inserted = 0
    for i in range(0, len(records), batch_size):
        batch = records[i:i + batch_size]
        try:
            resp = requests.post(
                f"{API_BASE}/{table}{query_params}",
                headers=headers,
                json=batch,
                timeout=30,
            )
            if resp.ok:
                total_inserted += len(batch)
            else:
                print(f"[LOAD] Batch insert failed for {table}: {resp.status_code} - {resp.text[:200]}")
                # Try one-by-one for the failed batch
                for record in batch:
                    try:
                        r = requests.post(
                            f"{API_BASE}/{table}{query_params}",
                            headers=headers,
                            json=record,
                            timeout=15,
                        )
                        if r.ok:
                            total_inserted += 1
                    except Exception:
                        pass
        except Exception as e:
            print(f"[LOAD] Error inserting batch to {table}: {e}")
        time.sleep(0.1)

    return total_inserted


def load_air_quality(records):
    """Load air quality measurements into the database."""
    if not records:
        return 0
    return _batch_insert("air_quality_measurements", records)


def load_weather(records):
    """Load weather measurements into the database (upsert on re-runs)."""
    if not records:
        return 0
    return _batch_insert("weather_measurements", records, upsert=True,
                         on_conflict="location_name,latitude,longitude,measurement_time")


def load_rejected_records(records):
    """Load rejected records into the database."""
    if not records:
        return 0
    return _batch_insert("rejected_records", records)


def load_gold_records(records):
    """Load gold analytical records into the database (upsert on re-runs)."""
    if not records:
        return 0
    return _batch_insert("gold_air_quality_daily", records, upsert=True,
                         on_conflict="date,station_id")


def load_pipeline_run(run_id, started_at, status, **metrics):
    """Create or update a pipeline run record."""
    record = {
        "run_id": run_id,
        "started_at": started_at,
        "completed_at": datetime.now(timezone.utc).isoformat(),
        "status": status,
        **metrics,
    }
    try:
        resp = requests.post(
            f"{API_BASE}/pipeline_runs",
            headers=get_headers(),
            json=record,
            timeout=15,
        )
        if not resp.ok:
            print(f"[LOAD] Pipeline run insert failed: {resp.status_code}")
    except Exception as e:
        print(f"[LOAD] Pipeline run error: {e}")


def load_quality_summary(pipeline_run_id, source, summary):
    """Insert a data quality summary record."""
    record = {
        "pipeline_run_id": pipeline_run_id,
        "source": source,
        "total_records": summary.get("total", 0),
        "valid_records": summary.get("valid", 0),
        "rejected_records": summary.get("rejected", 0),
        "duplicate_records": summary.get("duplicates", 0),
        "missing_value_count": summary.get("missing_values", 0),
        "validation_failures": summary.get("validation_failures", 0),
        "schema_valid": summary.get("schema_valid", True),
        "checks_passed": summary.get("checks_passed", 0),
        "checks_failed": summary.get("checks_failed", 0),
    }
    try:
        resp = requests.post(
            f"{API_BASE}/data_quality_summary",
            headers=get_headers(),
            json=record,
            timeout=15,
        )
        if not resp.ok:
            print(f"[LOAD] Quality summary insert failed: {resp.status_code}")
    except Exception as e:
        print(f"[LOAD] Quality summary error: {e}")
