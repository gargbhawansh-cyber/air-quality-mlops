"""Bulk load processed JSON data into Supabase via REST API in batches."""
import json
import os
import time
import requests
from pathlib import Path

# Load env
from dotenv import load_dotenv
load_dotenv()

SUPABASE_URL = os.getenv("VITE_SUPABASE_URL", os.getenv("SUPABASE_URL", ""))
ANON_KEY = os.getenv("VITE_SUPABASE_ANON_KEY", os.getenv("SUPABASE_ANON_KEY", ""))
SERVICE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "")

API_BASE = f"{SUPABASE_URL}/rest/v1"
KEY = SERVICE_KEY or ANON_KEY
HEADERS = {
    "apikey": KEY,
    "Authorization": f"Bearer {KEY}",
    "Content-Type": "application/json",
    "Prefer": "return=minimal",
}

def batch_insert(table, records, batch_size=200):
    total = 0
    for i in range(0, len(records), batch_size):
        batch = records[i:i+batch_size]
        try:
            resp = requests.post(f"{API_BASE}/{table}", headers=HEADERS, json=batch, timeout=30)
            if resp.ok:
                total += len(batch)
            else:
                print(f"  Batch {i//batch_size} failed: {resp.status_code} {resp.text[:200]}")
                # Try smaller batches
                for r in batch:
                    try:
                        r2 = requests.post(f"{API_BASE}/{table}", headers=HEADERS, json=r, timeout=15)
                        if r2.ok:
                            total += 1
                    except:
                        pass
        except Exception as e:
            print(f"  Error: {e}")
        time.sleep(0.05)
    return total

def main():
    base = Path(__file__).parent.parent / "data" / "processed"

    # Load gold records
    with open(base / "gold_records.json") as f:
        gold = json.load(f)
    print(f"Loading {len(gold)} gold records...")
    n = batch_insert("gold_air_quality_daily", gold)
    print(f"  Loaded: {n}")

    # Load rejected records
    with open(base / "rejected.json") as f:
        rejected = json.load(f)
    print(f"Loading {len(rejected)} rejected records...")
    n = batch_insert("rejected_records", rejected)
    print(f"  Loaded: {n}")

    # Load weather records
    with open(base / "valid_weather.json") as f:
        weather = json.load(f)
    print(f"Loading {len(weather)} weather records...")
    n = batch_insert("weather_measurements", weather)
    print(f"  Loaded: {n}")

    # Load AQ records (large - use bigger batches)
    with open(base / "valid_aq.json") as f:
        aq = json.load(f)
    print(f"Loading {len(aq)} air quality records...")
    n = batch_insert("air_quality_measurements", aq, batch_size=500)
    print(f"  Loaded: {n}")

    print("Done!")

if __name__ == "__main__":
    main()
