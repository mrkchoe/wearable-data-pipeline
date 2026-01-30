#!/usr/bin/env bash
# Run tests on Linux (same steps as CI). From repo root:
#   ./scripts/test-linux.sh
# Or with Docker (no local Python/Postgres):
#   docker run --rm -v "$(pwd):/app" -w /app --network host python:3.11-slim bash /app/scripts/test-linux.sh
set -e
cd "$(dirname "$0")/.."
pip install -q -r requirements.txt
export DB_HOST=${DB_HOST:-localhost}
export DB_PORT=${DB_PORT:-5432}
export DB_NAME=${DB_NAME:-wearable}
export DB_USER=${DB_USER:-wearable}
export DB_PASSWORD=${DB_PASSWORD:-wearable}
echo "--- Ingest sample data ---"
python -m ingestion.ingest --data-dir sample_data
echo "--- pytest ---"
pytest tests/ -v
