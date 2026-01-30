# Run the pipeline (ingest + dbt) in a container. Set DATABASE_URL or DB_* and optionally PIPELINE_DATA_DIR.
FROM python:3.11-slim

WORKDIR /app

# Install deps (includes dbt-postgres)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy project (exclude local data and caches via .dockerignore if present)
COPY . .

# dbt profile: use env vars (DB_HOST, DB_USER, etc. or DATABASE_URL for ingestion only; dbt uses DB_*)
RUN mkdir -p /root/.dbt && cp dbt/profiles.yml /root/.dbt/profiles.yml

ENV PIPELINE_DATA_DIR=/app/data_lake
ENV PIPELINE_USE_MANIFEST=1

ENTRYPOINT ["python", "-m", "ingestion.runner"]
