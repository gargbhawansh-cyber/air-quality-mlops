"""
Main pipeline orchestrator — runs the complete ETL pipeline end-to-end.
"""
import json
import sys
import os
from datetime import datetime, timezone
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from ingestion.openaq_ingest import ingest_openaq
from ingestion.openmeteo_ingest import ingest_openmeteo
from pipeline.extract import extract_openaq_raw, extract_openmeteo_raw
from pipeline.transform import transform_air_quality, transform_weather, enrich_with_weather
from pipeline.staging import write_staging_openaq, write_staging_openmeteo
from quality.checks import validate_air_quality, validate_weather, check_referential_integrity
from pipeline.load import (
    load_air_quality, load_weather, load_rejected_records,
    load_gold_records, load_pipeline_run, load_quality_summary,
)
from pipeline.aggregate import build_gold_table


def run_pipeline():
    """Run the complete end-to-end ETL pipeline."""
    pipeline_run_id = f"pipeline_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}"
    started_at = datetime.now(timezone.utc).isoformat()
    print(f"\n{'='*60}")
    print(f"  AIR QUALITY ETL PIPELINE — RUN: {pipeline_run_id}")
    print(f"{'='*60}\n")

    metrics = {
        "total_records": 0,
        "valid_records": 0,
        "rejected_records": 0,
        "duplicate_records": 0,
        "missing_value_count": 0,
        "validation_failures": 0,
        "gold_records": 0,
    }

    all_rejected = []
    data_source = "live"

    try:
        # === STEP 1: Extract OpenAQ ===
        print("\n--- STEP 1: Extract OpenAQ ---")
        openaq_result = ingest_openaq()
        if openaq_result["data_source"] == "sample":
            data_source = "sample"

        # === STEP 2: Extract Open-Meteo ===
        print("\n--- STEP 2: Extract Open-Meteo ---")
        weather_result = ingest_openmeteo()
        if weather_result["data_source"] == "sample":
            data_source = "sample"

        # === STEP 3: Read raw data and transform ===
        print("\n--- STEP 3: Transform Air Quality ---")
        raw_aq = extract_openaq_raw(openaq_result["run_id"])
        transformed_aq = transform_air_quality(raw_aq, openaq_result["run_id"])
        print(f"Transformed {len(transformed_aq)} air quality records")

        print("\n--- STEP 4: Transform Weather ---")
        raw_weather = extract_openmeteo_raw(weather_result["run_id"])
        transformed_weather = transform_weather(raw_weather, weather_result["run_id"])
        print(f"Transformed {len(transformed_weather)} weather records")

        # === STEP 4.5: Write to staging layer ===
        print("\n--- STEP 4.5: Write Staging Layer ---")
        write_staging_openaq(transformed_aq, openaq_result["run_id"])
        write_staging_openmeteo(transformed_weather, weather_result["run_id"])

        # === STEP 5: Validate ===
        print("\n--- STEP 5: Quality Validation — Air Quality ---")
        valid_aq, aq_result = validate_air_quality(transformed_aq, pipeline_run_id)
        print(f"AQ Quality: {aq_result}")

        print("\n--- STEP 6: Quality Validation — Weather ---")
        valid_weather, weather_q_result = validate_weather(transformed_weather, pipeline_run_id)
        print(f"Weather Quality: {weather_q_result}")

        # Collect rejected records
        all_rejected.extend(aq_result.rejected_records)
        all_rejected.extend(weather_q_result.rejected_records)

        # === STEP 7: Referential integrity check ===
        print("\n--- STEP 7: Referential Integrity Check ---")
        join_count, orphan_count = check_referential_integrity(valid_aq, valid_weather)
        print(f"Joinable: {join_count}, Orphans: {orphan_count}")

        # === STEP 8: Weather enrichment ===
        print("\n--- STEP 8: Weather Enrichment ---")
        enriched_aq = enrich_with_weather(valid_aq, valid_weather)

        # === STEP 9: Load to database ===
        print("\n--- STEP 9: Load to Database ---")
        aq_loaded = load_air_quality(valid_aq)
        print(f"Loaded {aq_loaded} air quality records")

        weather_loaded = load_weather(valid_weather)
        print(f"Loaded {weather_loaded} weather records")

        rejected_loaded = load_rejected_records(all_rejected)
        print(f"Loaded {rejected_loaded} rejected records")

        # === STEP 10: Build gold analytical table ===
        print("\n--- STEP 10: Build Gold Analytical Table ---")
        gold_records = build_gold_table(pipeline_run_id)

        # Clear existing gold data for this run (upsert-like behavior)
        # Insert new gold records
        gold_loaded = load_gold_records(gold_records)
        print(f"Loaded {gold_loaded} gold analytical records")

        # === STEP 11: Quality summaries ===
        print("\n--- STEP 11: Generate Quality Summaries ---")
        load_quality_summary(pipeline_run_id, "openaq", aq_result.to_dict())
        load_quality_summary(pipeline_run_id, "openmeteo", weather_q_result.to_dict())

        # Update metrics
        metrics["total_records"] = len(transformed_aq) + len(transformed_weather)
        metrics["valid_records"] = len(valid_aq) + len(valid_weather)
        metrics["rejected_records"] = len(all_rejected)
        metrics["duplicate_records"] = aq_result.duplicates + weather_q_result.duplicates
        metrics["missing_value_count"] = aq_result.missing_values + weather_q_result.missing_values
        metrics["validation_failures"] = aq_result.validation_failures + weather_q_result.validation_failures
        metrics["gold_records"] = gold_loaded

        status = "success"
        print(f"\n{'='*60}")
        print(f"  PIPELINE COMPLETE — Status: {status}")
        print(f"  Total: {metrics['total_records']} | Valid: {metrics['valid_records']}")
        print(f"  Rejected: {metrics['rejected_records']} | Duplicates: {metrics['duplicate_records']}")
        print(f"  Gold records: {metrics['gold_records']} | Data source: {data_source}")
        print(f"{'='*60}\n")

    except Exception as e:
        status = "failed"
        metrics["error_message"] = str(e)
        print(f"\n[ERROR] Pipeline failed: {e}")
        import traceback
        traceback.print_exc()

    # Record pipeline run
    load_pipeline_run(pipeline_run_id, started_at, status, **metrics)

    return {
        "run_id": pipeline_run_id,
        "status": status,
        "metrics": metrics,
        "data_source": data_source,
    }


if __name__ == "__main__":
    result = run_pipeline()
    print(f"\nPipeline finished: {result['status']}")
    print(f"Metrics: {json.dumps(result['metrics'], indent=2)}")
