"""
Central configuration for the Air Quality Index Pipeline.
Reads from environment variables with sensible defaults.
Never hardcodes secrets.
"""
import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

# --- Supabase / PostgreSQL ---
SUPABASE_URL = os.getenv("VITE_SUPABASE_URL", os.getenv("SUPABASE_URL", ""))
SUPABASE_ANON_KEY = os.getenv("VITE_SUPABASE_ANON_KEY", os.getenv("SUPABASE_ANON_KEY", ""))
SUPABASE_SERVICE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "")

# REST API base
API_BASE = f"{SUPABASE_URL}/rest/v1"

# --- OpenAQ ---
OPENAQ_API_BASE = os.getenv("OPENAQ_API_BASE", "https://api.openaq.org/v3")
OPENAQ_API_KEY = os.getenv("OPENAQ_API_KEY", "")

# --- Open-Meteo ---
OPENMETEO_API_BASE = os.getenv("OPENMETEO_API_BASE", "https://archive-api.open-meteo.com/v1")
OPENMETEO_ARCHIVE_BASE = "https://archive-api.open-meteo.com/v1/archive"

# --- Pipeline ---
PROJECT_ROOT = Path(__file__).parent
DATA_DIR = PROJECT_ROOT / "data"
RAW_DIR = DATA_DIR / "raw"
STAGING_DIR = DATA_DIR / "staging"
PROCESSED_DIR = DATA_DIR / "processed"
REJECTED_DIR = DATA_DIR / "rejected"

# Cities to fetch data for (lat, lon)
CITIES = {
    "Delhi": {"lat": 28.6139, "lon": 77.2090, "country": "IN"},
    "Mumbai": {"lat": 19.0760, "lon": 72.8777, "country": "IN"},
    "Chennai": {"lat": 13.0827, "lon": 80.2707, "country": "IN"},
    "Kolkata": {"lat": 22.5726, "lon": 88.3639, "country": "IN"},
    "Bengaluru": {"lat": 12.9716, "lon": 77.5946, "country": "IN"},
}

# Pollutants we support
SUPPORTED_POLLUTANTS = ["pm25", "pm10", "co", "no2", "so2", "o3"]

# Unit normalization map
UNIT_NORMALIZATION = {
    "µg/m³": "ug/m3",
    "ug/m3": "ug/m3",
    "µg/m3": "ug/m3",
    "mg/m³": "mg/m3",
    "ppm": "ppm",
    "ppb": "ppb",
}

# Pollutant value ranges for validation (min, max) in standard units
POLLUTANT_RANGES = {
    "pm25": (0, 1000),
    "pm10": (0, 2000),
    "co": (0, 100),
    "no2": (0, 3000),
    "so2": (0, 2000),
    "o3": (0, 1000),
}

# Request settings
REQUEST_TIMEOUT = int(os.getenv("REQUEST_TIMEOUT", "30"))
REQUEST_RETRIES = int(os.getenv("REQUEST_RETRIES", "3"))

# Use sample data fallback if API fails
USE_SAMPLE_FALLBACK = os.getenv("USE_SAMPLE_FALLBACK", "true").lower() == "true"


def get_headers():
    """Return headers for Supabase REST API calls."""
    key = SUPABASE_SERVICE_KEY or SUPABASE_ANON_KEY
    return {
        "apikey": key,
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json",
        "Prefer": "return=representation",
    }
