"""
Data quality validation rules for the Air Quality Pipeline.
Configurable rules for schema, ranges, timestamps, units, and duplicates.
"""
from config import SUPPORTED_POLLUTANTS, POLLUTANT_RANGES, UNIT_NORMALIZATION

# Required fields for air quality measurements
AQ_REQUIRED_FIELDS = [
    "station_id", "station_name", "city", "measurement_time",
    "pollutant", "value", "unit",
]

# Required fields for weather measurements
WEATHER_REQUIRED_FIELDS = [
    "location_name", "latitude", "longitude", "measurement_time",
]

# Allowed units per pollutant
ALLOWED_UNITS = {
    "pm25": ["ug/m3"],
    "pm10": ["ug/m3"],
    "co": ["mg/m3", "ug/m3"],
    "no2": ["ug/m3", "ppb"],
    "so2": ["ug/m3", "ppb"],
    "o3": ["ug/m3", "ppb"],
}

# Schema definition for air quality records
AQ_SCHEMA = {
    "station_id": str,
    "station_name": str,
    "city": str,
    "measurement_time": str,
    "pollutant": str,
    "value": (int, float),
    "unit": str,
}

WEATHER_SCHEMA = {
    "location_name": str,
    "latitude": (int, float),
    "longitude": (int, float),
    "measurement_time": str,
}


def get_pollutant_range(pollutant):
    """Get the valid value range for a pollutant."""
    return POLLUTANT_RANGES.get(pollutant, (0, float("inf")))


def is_valid_pollutant(pollutant):
    """Check if pollutant is in the supported list."""
    return pollutant.lower() in SUPPORT_POLLUTANTS if False else pollutant.lower() in SUPPORTED_POLLUTANTS


def is_valid_unit(pollutant, unit):
    """Check if the unit is allowed for the given pollutant."""
    normalized = UNIT_NORMALIZATION.get(unit, unit)
    allowed = ALLOWED_UNITS.get(pollutant.lower(), [])
    return normalized in allowed


def normalize_unit(unit):
    """Normalize a unit string to canonical form."""
    return UNIT_NORMALIZATION.get(unit, unit)


def is_valid_timestamp(ts_str):
    """Check if a timestamp string is parseable."""
    if not ts_str:
        return False
    try:
        from datetime import datetime
        # Try ISO format
        ts = ts_str.replace("Z", "+00:00")
        datetime.fromisoformat(ts)
        return True
    except (ValueError, AttributeError):
        return False


def is_in_range(pollutant, value):
    """Check if a pollutant value is within the valid range."""
    min_val, max_val = get_pollutant_range(pollutant)
    if value is None:
        return False
    try:
        v = float(value)
        return min_val <= v <= max_val
    except (ValueError, TypeError):
        return False
