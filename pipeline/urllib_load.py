"""Insert AQ data using urllib — strips enrichment fields not in the table."""
import json
import os
import time
import urllib.request
import urllib.error
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(Path(__file__).parent.parent / ".env")

SUPABASE_URL = os.getenv("VITE_SUPABASE_URL", os.getenv("SUPABASE_URL", ""))
ANON_KEY = os.getenv("VITE_SUPABASE_ANON_KEY", os.getenv("SUPABASE_ANON_KEY", ""))
SERVICE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "")

API_BASE = f"{SUPABASE_URL}/rest/v1"
KEY = SERVICE_KEY or ANON_KEY

base = Path(__file__).parent.parent / "data" / "processed"

with open(base / "valid_aq.json") as f:
    aq = json.load(f)

# Strip weather enrichment fields that aren't in the table
ALLOWED_FIELDS = {"station_id", "station_name", "city", "country", "latitude",
                   "longitude", "measurement_time", "pollutant", "value", "unit",
                   "source", "ingestion_run_id"}

clean_aq = []
for r in aq:
    clean_r = {k: v for k, v in r.items() if k in ALLOWED_FIELDS}
    clean_aq.append(clean_r)

print(f"Loading {len(clean_aq)} AQ records...")

batch_size = 50
total = 0
for i in range(0, len(clean_aq), batch_size):
    batch = clean_aq[i:i+batch_size]
    body = json.dumps(batch).encode('utf-8')
    req = urllib.request.Request(
        f"{API_BASE}/air_quality_measurements",
        data=body,
        headers={
            "apikey": KEY,
            "Authorization": f"Bearer {KEY}",
            "Content-Type": "application/json",
            "Prefer": "return=minimal",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            if resp.status in (200, 201):
                total += len(batch)
    except urllib.error.HTTPError as e:
        err_msg = e.read().decode()[:200]
        if "duplicate" in err_msg.lower() or "23505" in err_msg:
            total += len(batch)  # Already loaded
        else:
            print(f"  Batch {i//batch_size} HTTP error: {e.code} {err_msg}")
    except Exception as e:
        print(f"  Batch {i//batch_size} error: {e}")
    
    if (i // batch_size) % 10 == 0:
        print(f"  Progress: {total}/{len(clean_aq)}")
    time.sleep(0.01)

print(f"Total loaded: {total}")
