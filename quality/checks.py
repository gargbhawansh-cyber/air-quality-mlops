"""
Data quality checks module.
Performs schema, required field, null, duplicate, range, timestamp,
unit consistency, and referential checks on pipeline data.
"""
import json
from datetime import datetime, timezone
from collections import defaultdict

from quality.rules import (
    AQ_REQUIRED_FIELDS, WEATHER_REQUIRED_FIELDS,
    AQ_SCHEMA, WEATHER_SCHEMA,
    is_valid_pollutant, is_valid_unit, normalize_unit, is_valid_timestamp,
    is_in_range, get_pollutant_range,
)


class QualityResult:
    """Holds the result of a quality check run."""
    def __init__(self):
        self.total = 0
        self.valid = 0
        self.rejected = 0
        self.duplicates = 0
        self.missing_values = 0
        self.validation_failures = 0
        self.rejected_records = []
        self.checks_passed = 0
        self.checks_failed = 0
        self.schema_valid = True

    def to_dict(self):
        return {
            "total": self.total,
            "valid": self.valid,
            "rejected": self.rejected,
            "duplicates": self.duplicates,
            "missing_values": self.missing_values,
            "validation_failures": self.validation_failures,
            "checks_passed": self.checks_passed,
            "checks_failed": self.checks_failed,
            "schema_valid": self.schema_valid,
        }

    def __repr__(self):
        return f"QualityResult(total={self.total}, valid={self.valid}, rejected={self.rejected}, duplicates={self.duplicates})"


def _reject(result, record, reason, rule, run_id):
    """Add a record to the rejected list."""
    result.rejected_records.append({
        "run_id": run_id,
        "original_record": json.dumps(record, default=str),
        "rejection_reason": reason,
        "validation_rule": rule,
        "rejected_at": datetime.now(timezone.utc).isoformat(),
    })


def check_schema(record, schema):
    """Check if a record matches the expected schema (field types)."""
    for field, expected_type in schema.items():
        if field in record and record[field] is not None:
            val = record[field]
            if not isinstance(val, expected_type):
                # Allow int for float fields and vice versa
                if expected_type == (int, float) and isinstance(val, (int, float)):
                    continue
                if expected_type == str and isinstance(val, str):
                    continue
                return False, f"Field '{field}' has wrong type"
    return True, ""


def validate_air_quality(records, run_id):
    """
    Run all data quality checks on air quality measurements.
    Returns (valid_records, result) where result is a QualityResult.
    """
    result = QualityResult()
    result.total = len(records)
    seen_keys = set()

    # Schema check (check first record as representative)
    if records:
        schema_ok, schema_msg = check_schema(records[0], AQ_SCHEMA)
        if not schema_ok:
            result.schema_valid = False
            result.checks_failed += 1
        else:
            result.checks_passed += 1
    else:
        result.checks_passed += 1

    valid_records = []

    for record in records:
        rejected = False

        # 1. Required fields check
        for field in AQ_REQUIRED_FIELDS:
            if field not in record or record[field] is None or record[field] == "":
                result.missing_values += 1
                if not rejected:
                    _reject(result, record, f"Missing required field: {field}", "required_fields", run_id)
                    rejected = True
                    result.validation_failures += 1
                break

        if rejected:
            result.rejected += 1
            continue

        # 2. Pollutant validity
        pollutant = record["pollutant"].lower()
        if not is_valid_pollutant(pollutant):
            _reject(result, record, f"Unsupported pollutant: {pollutant}", "pollutant_validity", run_id)
            result.rejected += 1
            result.validation_failures += 1
            continue
        result.checks_passed += 1

        # 3. Timestamp validity
        if not is_valid_timestamp(record["measurement_time"]):
            _reject(result, record, "Invalid timestamp format", "timestamp_validity", run_id)
            result.rejected += 1
            result.validation_failures += 1
            continue
        result.checks_passed += 1

        # 4. Value range check
        value = record["value"]
        if not is_in_range(pollutant, value):
            _reject(result, record,
                    f"Value {value} out of range for {pollutant}",
                    "pollutant_range", run_id)
            result.rejected += 1
            result.validation_failures += 1
            continue
        result.checks_passed += 1

        # 5. Unit consistency
        unit = record.get("unit", "")
        normalized_unit = normalize_unit(unit)
        if not is_valid_unit(pollutant, unit):
            _reject(result, record,
                    f"Invalid unit '{unit}' for {pollutant}",
                    "unit_consistency", run_id)
            result.rejected += 1
            result.validation_failures += 1
            continue
        record["unit"] = normalized_unit
        result.checks_passed += 1

        # 6. Duplicate detection (station_id + pollutant + timestamp)
        dup_key = f"{record['station_id']}|{pollutant}|{record['measurement_time']}"
        if dup_key in seen_keys:
            result.duplicates += 1
            continue
        seen_keys.add(dup_key)

        # 7. Null value check (value field specifically)
        if value is None:
            result.missing_values += 1
            _reject(result, record, "Null value for measurement", "null_value", run_id)
            result.rejected += 1
            result.validation_failures += 1
            continue

        # Record passed all checks
        record["pollutant"] = pollutant
        valid_records.append(record)
        result.valid += 1

    return valid_records, result


def validate_weather(records, run_id):
    """
    Run data quality checks on weather measurements.
    Returns (valid_records, result).
    """
    result = QualityResult()
    result.total = len(records)
    seen_keys = set()

    if records:
        schema_ok, _ = check_schema(records[0], WEATHER_SCHEMA)
        if not schema_ok:
            result.schema_valid = False
            result.checks_failed += 1
        else:
            result.checks_passed += 1
    else:
        result.checks_passed += 1

    valid_records = []

    for record in records:
        rejected = False

        # Required fields
        for field in WEATHER_REQUIRED_FIELDS:
            if field not in record or record[field] is None or record[field] == "":
                result.missing_values += 1
                if not rejected:
                    _reject(result, record, f"Missing required field: {field}", "required_fields", run_id)
                    rejected = True
                    result.validation_failures += 1
                break

        if rejected:
            result.rejected += 1
            continue

        # Timestamp validity
        if not is_valid_timestamp(record["measurement_time"]):
            _reject(result, record, "Invalid timestamp format", "timestamp_validity", run_id)
            result.rejected += 1
            result.validation_failures += 1
            continue
        result.checks_passed += 1

        # Duplicate detection
        dup_key = f"{record['location_name']}|{record['latitude']}|{record['longitude']}|{record['measurement_time']}"
        if dup_key in seen_keys:
            result.duplicates += 1
            continue
        seen_keys.add(dup_key)

        # Check for missing weather values (not all fields are required, but track them)
        for field in ["temperature", "humidity", "precipitation", "wind_speed"]:
            if field in record and record[field] is None:
                result.missing_values += 1

        valid_records.append(record)
        result.valid += 1

    return valid_records, result


def check_referential_integrity(aq_records, weather_records):
    """
    Check that air quality records can be joined with weather records
    by city/location and timestamp.
    Returns (join_count, orphan_count).
    """
    weather_keys = set()
    for w in weather_records:
        key = (w.get("location_name", ""), w.get("measurement_time", "")[:13])
        weather_keys.add(key)

    join_count = 0
    orphan_count = 0
    for aq in aq_records:
        key = (aq.get("city", ""), aq.get("measurement_time", "")[:13])
        if key in weather_keys:
            join_count += 1
        else:
            orphan_count += 1

    return join_count, orphan_count
