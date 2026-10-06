"""
Ingestion logger — records metadata for every extraction run.
Writes to both local files and the Supabase ingestion_runs table.
"""
import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
import requests
from config import RAW_DIR, API_BASE, get_headers, SUPABASE_URL


def generate_run_id(source: str) -> str:
    """Generate a unique run ID."""
    ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    short_uuid = uuid.uuid4().hex[:8]
    return f"{source}_{ts}_{short_uuid}"


def log_ingestion_run(
    run_id: str,
    source: str,
    status: str,
    row_count: int,
    endpoint: str = "",
    error_message: str = "",
    data_source: str = "live",
):
    """Log an ingestion run to both local file and Supabase."""
    record = {
        "run_id": run_id,
        "source": source,
        "extraction_time": datetime.now(timezone.utc).isoformat(),
        "status": status,
        "row_count": row_count,
        "endpoint": endpoint,
        "error_message": error_message,
        "data_source": data_source,
    }

    # Local file log
    log_dir = RAW_DIR / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    log_file = log_dir / f"ingestion_log.jsonl"
    with open(log_file, "a") as f:
        f.write(json.dumps(record) + "\n")

    # Supabase log
    try:
        if SUPABASE_URL:
            resp = requests.post(
                f"{API_BASE}/ingestion_runs",
                headers=get_headers(),
                json=record,
                timeout=15,
            )
            if not resp.ok:
                print(f"[WARNING] Failed to log ingestion run to Supabase: {resp.status_code}")
    except Exception as e:
        print(f"[WARNING] Supabase ingestion log failed: {e}")

    print(f"[INGESTION LOG] {source} | {status} | rows={row_count} | source={data_source}")
    return record


def update_ingestion_run(run_id: str, **fields):
    """Update an existing ingestion run record in Supabase."""
    try:
        if not SUPABASE_URL:
            return
        resp = requests.patch(
            f"{API_BASE}/ingestion_runs?run_id=eq.{run_id}",
            headers=get_headers(),
            json=fields,
            timeout=15,
        )
        if not resp.ok:
            print(f"[WARNING] Failed to update ingestion run: {resp.status_code}")
    except Exception as e:
        print(f"[WARNING] Update ingestion run failed: {e}")
