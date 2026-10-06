"""
Apache Airflow DAG for the Air Quality ETL Pipeline.

DAG: air_quality_etl_pipeline

Task sequence:
1. extract_openaq      — Fetch air quality data from OpenAQ API
2. extract_weather     — Fetch weather data from Open-Meteo API
3. validate_raw_data   — Validate raw data schema and completeness
4. transform_air_quality — Normalize and clean air quality records
5. transform_weather   — Normalize and clean weather records
6. write_staging       — Write normalized records to persistent staging files
7. quality_checks      — Run full data quality validation
8. load_postgresql     — Load validated data into PostgreSQL/Supabase
9. build_gold_tables   — Build analytical gold data mart
10. generate_pipeline_summary — Record pipeline run metrics

Dependencies:
  [extract_openaq, extract_weather] >> validate_raw_data
  validate_raw_data >> [transform_air_quality, transform_weather]
  [transform_air_quality, transform_weather] >> write_staging
  write_staging >> quality_checks
  quality_checks >> load_postgresql >> build_gold_tables >> generate_pipeline_summary

Note: Weather enrichment and referential integrity checks are performed
within the quality_checks and load_postgresql tasks respectively, mirroring
the local pipeline (pipeline/run_pipeline.py steps 7 and 8).

To run locally without Airflow:
    cd <project_root>
    python -m pipeline.run_pipeline

To run with Airflow:
    airflow dags trigger air_quality_etl_pipeline
"""
from datetime import datetime, timedelta
import os
import sys

# Add project root to Python path for imports
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

try:
    from airflow import DAG
    from airflow.operators.python import PythonOperator
    from airflow.operators.dummy import DummyOperator
    AIRFLOW_AVAILABLE = True
except ImportError:
    AIRFLOW_AVAILABLE = False


default_args = {
    "owner": "air_quality_team",
    "depends_on_past": False,
    "email_on_failure": False,
    "email_on_retry": False,
    "retries": 2,
    "retry_delay": timedelta(minutes=2),
}


def _extract_openaq():
    from ingestion.openaq_ingest import ingest_openaq
    result = ingest_openaq()
    return result["run_id"]


def _extract_weather():
    from ingestion.openmeteo_ingest import ingest_openmeteo
    result = ingest_openmeteo()
    return result["run_id"]


def _validate_raw_data(**context):
    from pipeline.extract import extract_openaq_raw, extract_openmeteo_raw
    openaq_run_id = context["ti"].xcom_pull(task_ids="extract_openaq")
    weather_run_id = context["ti"].xcom_pull(task_ids="extract_weather")

    aq_raw = extract_openaq_raw(openaq_run_id)
    weather_raw = extract_openmeteo_raw(weather_run_id)

    if not aq_raw:
        raise ValueError("No OpenAQ raw data found")
    if not weather_raw:
        raise ValueError("No weather raw data found")

    print(f"Validated raw data: {len(aq_raw)} AQ records, {len(weather_raw)} weather records")
    return {"aq_count": len(aq_raw), "weather_count": len(weather_raw)}


def _transform_air_quality(**context):
    from pipeline.extract import extract_openaq_raw
    from pipeline.transform import transform_air_quality
    openaq_run_id = context["ti"].xcom_pull(task_ids="extract_openaq")
    raw_aq = extract_openaq_raw(openaq_run_id)
    transformed = transform_air_quality(raw_aq, openaq_run_id)
    print(f"Transformed {len(transformed)} air quality records")
    return len(transformed)


def _transform_weather(**context):
    from pipeline.extract import extract_openmeteo_raw
    from pipeline.transform import transform_weather
    weather_run_id = context["ti"].xcom_pull(task_ids="extract_weather")
    raw_weather = extract_openmeteo_raw(weather_run_id)
    transformed = transform_weather(raw_weather, weather_run_id)
    print(f"Transformed {len(transformed)} weather records")
    return len(transformed)


def _write_staging(**context):
    from pipeline.extract import extract_openaq_raw, extract_openmeteo_raw
    from pipeline.transform import transform_air_quality, transform_weather
    from pipeline.staging import write_staging_openaq, write_staging_openmeteo

    openaq_run_id = context["ti"].xcom_pull(task_ids="extract_openaq")
    weather_run_id = context["ti"].xcom_pull(task_ids="extract_weather")

    raw_aq = extract_openaq_raw(openaq_run_id)
    raw_weather = extract_openmeteo_raw(weather_run_id)
    transformed_aq = transform_air_quality(raw_aq, openaq_run_id)
    transformed_weather = transform_weather(raw_weather, weather_run_id)

    aq_path = write_staging_openaq(transformed_aq, openaq_run_id)
    weather_path = write_staging_openmeteo(transformed_weather, weather_run_id)
    print(f"Staging files: {aq_path}, {weather_path}")
    return {"aq_staged": len(transformed_aq), "weather_staged": len(transformed_weather)}


def _quality_checks(**context):
    from pipeline.extract import extract_openaq_raw, extract_openmeteo_raw
    from pipeline.transform import transform_air_quality, transform_weather
    from quality.checks import validate_air_quality, validate_weather

    openaq_run_id = context["ti"].xcom_pull(task_ids="extract_openaq")
    weather_run_id = context["ti"].xcom_pull(task_ids="extract_weather")

    raw_aq = extract_openaq_raw(openaq_run_id)
    raw_weather = extract_openmeteo_raw(weather_run_id)
    transformed_aq = transform_air_quality(raw_aq, openaq_run_id)
    transformed_weather = transform_weather(raw_weather, weather_run_id)

    valid_aq, aq_result = validate_air_quality(transformed_aq, "airflow_run")
    valid_weather, weather_result = validate_weather(transformed_weather, "airflow_run")

    print(f"AQ: {aq_result}")
    print(f"Weather: {weather_result}")
    return {"aq_valid": len(valid_aq), "weather_valid": len(valid_weather)}


def _load_postgresql(**context):
    from pipeline.extract import extract_openaq_raw, extract_openmeteo_raw
    from pipeline.transform import transform_air_quality, transform_weather, enrich_with_weather
    from quality.checks import validate_air_quality, validate_weather
    from pipeline.load import load_air_quality, load_weather, load_rejected_records

    openaq_run_id = context["ti"].xcom_pull(task_ids="extract_openaq")
    weather_run_id = context["ti"].xcom_pull(task_ids="extract_weather")

    raw_aq = extract_openaq_raw(openaq_run_id)
    raw_weather = extract_openmeteo_raw(weather_run_id)
    transformed_aq = transform_air_quality(raw_aq, openaq_run_id)
    transformed_weather = transform_weather(raw_weather, weather_run_id)
    valid_aq, aq_result = validate_air_quality(transformed_aq, "airflow_run")
    valid_weather, weather_result = validate_weather(transformed_weather, "airflow_run")

    enriched_aq = enrich_with_weather(valid_aq, valid_weather)

    aq_loaded = load_air_quality(enriched_aq)
    weather_loaded = load_weather(valid_weather)
    rejected_loaded = load_rejected_records(aq_result.rejected_records + weather_result.rejected_records)

    print(f"Loaded: {aq_loaded} AQ, {weather_loaded} weather, {rejected_loaded} rejected")
    return {"aq_loaded": aq_loaded, "weather_loaded": weather_loaded}


def _build_gold_tables(**context):
    from pipeline.aggregate import build_gold_table
    from pipeline.load import load_gold_records
    gold_records = build_gold_table("airflow_run")
    gold_loaded = load_gold_records(gold_records)
    print(f"Loaded {gold_loaded} gold records")
    return gold_loaded


def _generate_pipeline_summary(**context):
    from datetime import datetime, timezone
    from pipeline.load import load_pipeline_run
    metrics = {
        "total_records": context["ti"].xcom_pull(task_ids="load_postgresql") or {},
    }
    load_pipeline_run(
        f"airflow_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}",
        datetime.now(timezone.utc).isoformat(),
        "success",
        **{k: v for k, v in metrics.items() if isinstance(v, (int, float, str))},
    )
    print("Pipeline summary generated")


# Build DAG only if Airflow is available
if AIRFLOW_AVAILABLE:
    dag = DAG(
        "air_quality_etl_pipeline",
        default_args=default_args,
        description="Air Quality Index ETL Pipeline: OpenAQ + Open-Meteo -> Raw -> Staging -> ETL -> Quality -> PostgreSQL -> Gold -> Dashboard",
        schedule_interval="@daily",
        start_date=datetime(2025, 1, 1),
        catchup=False,
        tags=["air_quality", "etl", "data_engineering"],
    )

    with dag:
        start = DummyOperator(task_id="start")

        extract_openaq_task = PythonOperator(
            task_id="extract_openaq",
            python_callable=_extract_openaq,
        )

        extract_weather_task = PythonOperator(
            task_id="extract_weather",
            python_callable=_extract_weather,
        )

        validate_raw_task = PythonOperator(
            task_id="validate_raw_data",
            python_callable=_validate_raw_data,
            provide_context=True,
        )

        transform_aq_task = PythonOperator(
            task_id="transform_air_quality",
            python_callable=_transform_air_quality,
            provide_context=True,
        )

        transform_weather_task = PythonOperator(
            task_id="transform_weather",
            python_callable=_transform_weather,
            provide_context=True,
        )

        write_staging_task = PythonOperator(
            task_id="write_staging",
            python_callable=_write_staging,
            provide_context=True,
        )

        quality_task = PythonOperator(
            task_id="quality_checks",
            python_callable=_quality_checks,
            provide_context=True,
        )

        load_task = PythonOperator(
            task_id="load_postgresql",
            python_callable=_load_postgresql,
            provide_context=True,
        )

        gold_task = PythonOperator(
            task_id="build_gold_tables",
            python_callable=_build_gold_tables,
            provide_context=True,
        )

        summary_task = PythonOperator(
            task_id="generate_pipeline_summary",
            python_callable=_generate_pipeline_summary,
            provide_context=True,
        )

        end = DummyOperator(task_id="end")

        start >> [extract_openaq_task, extract_weather_task]
        [extract_openaq_task, extract_weather_task] >> validate_raw_task
        validate_raw_task >> [transform_aq_task, transform_weather_task]
        [transform_aq_task, transform_weather_task] >> write_staging_task
        write_staging_task >> quality_task
        quality_task >> load_task >> gold_task >> summary_task >> end
else:
    print("[INFO] Airflow not installed. DAG definition skipped.")
    print("[INFO] Use 'python -m pipeline.run_pipeline' to run the pipeline locally.")
