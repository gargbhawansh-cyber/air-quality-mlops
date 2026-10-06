"""Fast bulk insert using REST API with small batches and connection reuse."""
import json
import os
import time
import requests
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

SUPABASE_URL = os.getenv("VITE_SUPABASE_URL", os.getenv("SUPABASE_URL", ""))
ANON_KEY = os.getenv("VITE_SUPABASE_ANON_KEY", os.getenv("SUPABASE_ANON_KEY", ""))
SERVICE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "")

API_BASE = f"{SUPABASE_URL}/rest/v1"
KEY = SERVICE_KEY or ANON_KEY

session = requests.Session()
session.headers.update({
    "apikey": KEY,
    "Authorization": f"Bearer {KEY}",
    "Content-Type": "application/json",
    "Prefer": "return=minimal",
})

base = Path(__file__).parent.parent / "data" / "processed"

with open(base / "valid_aq.json") as f:
    aq = json.load(f)

print(f"Loading {len(aq)} AQ records in batches of 50...")
total = 0
batch_size = 50
for i in range(0, len(aq), batch_size):
    batch = aq[i:i+batch_size]
    try:
        resp = session.post(f"{API_BASE}/air_quality_measurements", json=batch, timeout=30)
        if resp.ok:
            total += len(batch)
        else:
            print(f"  Batch {i//batch_size} failed: {resp.status_code}")
            # Try individual
            for r in batch:
                try:
                    r2 = session.post(f"{API_BASE}/air_quality_measurements", json=r, timeout=10)
                    if r2.ok:
                        total += 1
                except:
                    pass
    except Exception as e:
        print(f"  Error at batch {i//batch_size}: {e}")
    if (i // batch_size) % 10 == 0:
        print(f"  Progress: {total}/{len(aq)}")
    time.sleep(0.02)

print(f"Total loaded: {total}")
