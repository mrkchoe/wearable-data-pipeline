"""
End-to-end DAG: detect new/changed CSV drops → S3 (partitioned) → Postgres staging → dbt.

Requires PYTHONPATH at repo root (set in docker-compose) and DB/S3 env vars.
"""

from __future__ import annotations

from datetime import datetime, timedelta

from airflow import DAG
from airflow.operators.bash import BashOperator
from airflow.operators.python import PythonOperator

PROJECT_DIR = "/opt/airflow/project"


def detect_new_files(**context):
    from ingestion.config import data_drop_dir, get_logger
    from ingestion.detect import detect_files

    log = get_logger("airflow.detect_new_files")
    summary = detect_files(data_dir=data_drop_dir(), check_s3=True, check_pg=False)
    log.info("Detection summary: %s", summary)
    context["ti"].xcom_push(key="detect_summary", value=summary)
    return summary


default_args = {
    "owner": "data-engineering",
    "depends_on_past": False,
    "retries": 1,
    "retry_delay": timedelta(minutes=2),
}

with DAG(
    dag_id="wearable_pipeline",
    default_args=default_args,
    start_date=datetime(2026, 1, 1),
    schedule_interval=None,
    catchup=False,
    tags=["wearable", "lakehouse"],
) as dag:
    detect_op = PythonOperator(
        task_id="detect_new_files",
        python_callable=detect_new_files,
    )
    upload_op = BashOperator(
        task_id="upload_to_s3",
        bash_command=f"cd {PROJECT_DIR} && python -m ingestion.upload_to_s3",
    )
    load_op = BashOperator(
        task_id="load_staging_postgres",
        bash_command=f"cd {PROJECT_DIR} && python -m ingestion.load_s3_to_staging",
    )
    dbt_run_op = BashOperator(
        task_id="dbt_run",
        bash_command=(
            f"cd {PROJECT_DIR}/dbt && "
            "dbt run --project-dir . --profiles-dir . "
        ),
    )
    dbt_test_op = BashOperator(
        task_id="dbt_test",
        bash_command=(
            f"cd {PROJECT_DIR}/dbt && "
            "dbt test --project-dir . --profiles-dir . "
        ),
    )

    detect_op >> upload_op >> load_op >> dbt_run_op >> dbt_test_op
