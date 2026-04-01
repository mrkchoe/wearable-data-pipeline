# Airflow image with pipeline + dbt dependencies (matches docker-compose build context from repo root).
FROM apache/airflow:2.8.1-python3.11

USER root
RUN apt-get update \
    && apt-get install -y --no-install-recommends gcc libpq-dev \
    && rm -rf /var/lib/apt/lists/*

USER airflow
RUN pip install --no-cache-dir \
    boto3 \
    pandas \
    sqlalchemy \
    psycopg2-binary \
    python-dotenv \
    dbt-core==1.7.14 \
    dbt-postgres==1.7.14

ENV PYTHONPATH=/opt/airflow/project
