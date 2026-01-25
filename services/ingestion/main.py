import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

from fastapi import FastAPI, HTTPException
from jsonschema import Draft7Validator, FormatChecker
from sqlalchemy import create_engine, text

logger = logging.getLogger("ingestion")
logging.basicConfig(level=logging.INFO)

SCHEMA_PATH = Path(__file__).resolve().parents[2] / "schemas" / "events" / "wearable_event.json"


def load_schema() -> Dict[str, Any]:
    if not SCHEMA_PATH.exists():
        raise FileNotFoundError(f"Schema not found at {SCHEMA_PATH}")
    return json.loads(SCHEMA_PATH.read_text())


def build_engine():
    import os

    host = os.getenv("DB_HOST", "localhost")
    port = os.getenv("DB_PORT", "5432")
    dbname = os.getenv("DB_NAME", "wearable")
    user = os.getenv("DB_USER", "wearable")
    password = os.getenv("DB_PASSWORD", "wearable")
    url = f"postgresql+psycopg2://{user}:{password}@{host}:{port}/{dbname}"
    return create_engine(url)


def ensure_raw_table(engine) -> None:
    ddl = """
    CREATE SCHEMA IF NOT EXISTS raw;
    CREATE TABLE IF NOT EXISTS raw.raw_events (
        event_id UUID PRIMARY KEY,
        schema_version TEXT NOT NULL,
        event_name TEXT NOT NULL,
        user_id TEXT,
        anonymous_id TEXT,
        device_id TEXT,
        session_id TEXT,
        client_ts TIMESTAMPTZ NOT NULL,
        server_ts TIMESTAMPTZ NOT NULL,
        source TEXT NOT NULL,
        environment TEXT NOT NULL,
        app_version TEXT,
        page TEXT,
        referrer TEXT,
        payload JSONB NOT NULL,
        received_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
    );
    """
    with engine.begin() as connection:
        for statement in ddl.strip().split(";"):
            stmt = statement.strip()
            if stmt:
                connection.execute(text(stmt))


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def log_event(message: str, payload: Dict[str, Any]) -> None:
    logger.info(json.dumps({"message": message, **payload}))


app = FastAPI(title="Wearable Ingestion API", version="0.1.0")


@app.on_event("startup")
def startup() -> None:
    schema = load_schema()
    app.state.validator = Draft7Validator(schema, format_checker=FormatChecker())
    app.state.engine = build_engine()
    ensure_raw_table(app.state.engine)
    app.state.metrics = {
        "received": 0,
        "accepted": 0,
        "rejected": 0,
        "deduped": 0
    }


@app.get("/health")
def health() -> Dict[str, str]:
    return {"status": "ok"}


@app.get("/metrics")
def metrics() -> Dict[str, int]:
    return app.state.metrics


@app.post("/events")
def ingest_events(payload: Dict[str, Any]) -> Dict[str, int]:
    if "events" not in payload or not isinstance(payload["events"], list):
        raise HTTPException(status_code=400, detail="Body must include list of events")

    events: List[Dict[str, Any]] = payload["events"]
    validator: Draft7Validator = app.state.validator
    engine = app.state.engine

    batch_received = len(events)
    batch_accepted = 0
    batch_rejected = 0
    batch_deduped = 0

    with engine.begin() as connection:
        for event in events:
            if "server_ts" not in event:
                event["server_ts"] = utc_now_iso()

            errors = sorted(validator.iter_errors(event), key=lambda e: e.path)
            if errors:
                batch_rejected += 1
                log_event(
                    "event_rejected",
                    {
                        "event_id": event.get("event_id"),
                        "event_name": event.get("event_name"),
                        "errors": [err.message for err in errors]
                    }
                )
                continue

            result = connection.execute(
                text(
                    """
                    INSERT INTO raw.raw_events (
                        event_id,
                        schema_version,
                        event_name,
                        user_id,
                        anonymous_id,
                        device_id,
                        session_id,
                        client_ts,
                        server_ts,
                        source,
                        environment,
                        app_version,
                        page,
                        referrer,
                        payload
                    )
                    VALUES (
                        :event_id,
                        :schema_version,
                        :event_name,
                        :user_id,
                        :anonymous_id,
                        :device_id,
                        :session_id,
                        :client_ts,
                        :server_ts,
                        :source,
                        :environment,
                        :app_version,
                        :page,
                        :referrer,
                        :payload
                    )
                    ON CONFLICT (event_id) DO NOTHING
                    """
                ),
                {
                    "event_id": event["event_id"],
                    "schema_version": event["schema_version"],
                    "event_name": event["event_name"],
                    "user_id": event.get("user_id"),
                    "anonymous_id": event.get("anonymous_id"),
                    "device_id": event.get("device_id"),
                    "session_id": event.get("session_id"),
                    "client_ts": event["client_ts"],
                    "server_ts": event["server_ts"],
                    "source": event["source"],
                    "environment": event["environment"],
                    "app_version": event.get("app_version"),
                    "page": event.get("page"),
                    "referrer": event.get("referrer"),
                    "payload": json.dumps(event["payload"])
                }
            )

            if result.rowcount == 0:
                batch_deduped += 1
            else:
                batch_accepted += 1

    app.state.metrics["received"] += batch_received
    app.state.metrics["accepted"] += batch_accepted
    app.state.metrics["rejected"] += batch_rejected
    app.state.metrics["deduped"] += batch_deduped

    log_event(
        "batch_ingested",
        {
            "received": batch_received,
            "accepted": batch_accepted,
            "rejected": batch_rejected,
            "deduped": batch_deduped
        }
    )

    return {
        "received": batch_received,
        "accepted": batch_accepted,
        "rejected": batch_rejected,
        "deduped": batch_deduped
    }
