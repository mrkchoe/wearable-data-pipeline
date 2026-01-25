import argparse
import json
import random
from datetime import datetime, timedelta, timezone
from typing import Dict
from uuid import UUID

import requests

EVENTS = [
    "page_view",
    "identify",
    "connect_device_started",
    "connect_device_succeeded",
    "connect_device_failed",
    "sync_requested",
    "sync_completed",
    "sync_failed",
    "metric_viewed",
    "goal_created",
    "export_clicked",
    "ui_error",
    "api_error",
    "perf_lcp",
    "perf_api_latency"
]

VENDORS = ["fitbit", "apple_health", "garmin", "oura", "whoop", "other"]
METRICS = ["steps", "sleep", "calories", "distance", "active_minutes"]
RANGES = ["day", "week", "month", "custom"]


def seeded_uuid(rng: random.Random) -> str:
    return str(UUID(int=rng.getrandbits(128)))


def build_payload(event_name: str, rng: random.Random) -> Dict[str, object]:
    vendor = rng.choice(VENDORS)
    metric = rng.choice(METRICS)
    date_range = rng.choice(RANGES)

    if event_name == "page_view":
        return {"page_title": "Dashboard", "entry_point": "direct"}
    if event_name == "identify":
        return {"user_status": "known"}
    if event_name == "connect_device_started":
        return {"vendor": vendor}
    if event_name == "connect_device_succeeded":
        return {"vendor": vendor, "device_model": "Wearable Pro X"}
    if event_name == "connect_device_failed":
        return {"vendor": vendor, "error_code": "DEVICE_CONNECT_FAILED", "error_message": "Timeout"}
    if event_name == "sync_requested":
        return {"vendor": vendor, "date_range": date_range, "sync_status": "requested"}
    if event_name == "sync_completed":
        return {
            "vendor": vendor,
            "date_range": date_range,
            "sync_status": "completed",
            "records_synced": rng.randint(10, 200)
        }
    if event_name == "sync_failed":
        return {
            "vendor": vendor,
            "date_range": date_range,
            "sync_status": "failed",
            "error_code": "SYNC_FAILED",
            "error_message": "Upstream API error"
        }
    if event_name == "metric_viewed":
        return {"metric_type": metric, "date_range": date_range, "vendor": vendor}
    if event_name == "goal_created":
        return {
            "metric_type": metric,
            "target_value": rng.randint(5000, 12000),
            "target_unit": "count" if metric != "sleep" else "minutes",
            "date_range": date_range
        }
    if event_name == "export_clicked":
        return {"export_format": "csv", "date_range": date_range, "vendor": vendor}
    if event_name == "ui_error":
        return {
            "component": "GoalCard",
            "error_code": "VALIDATION_FAILED",
            "error_message": "Goal target must be positive",
            "severity": "warning"
        }
    if event_name == "api_error":
        return {
            "endpoint": "/api/dashboard",
            "status_code": 500,
            "error_code": "DASHBOARD_FETCH_FAILED",
            "error_message": "Timeout"
        }
    if event_name == "perf_lcp":
        return {"lcp_ms": rng.uniform(900, 2000), "page_type": "dashboard"}
    if event_name == "perf_api_latency":
        return {"api_latency_ms": rng.uniform(120, 480), "endpoint": "/api/dashboard", "status_code": 200}

    return {}


def build_event(event_name: str, rng: random.Random, client_ts: str) -> Dict[str, object]:
    user_id = "user-123" if rng.random() > 0.2 else None
    anonymous_id = None if user_id else f"anon-{rng.randint(1000, 9999)}"
    event = {
        "schema_version": "1.0.0",
        "event_id": seeded_uuid(rng),
        "event_name": event_name,
        "device_id": "device-12345",
        "session_id": f"session-{rng.randint(1, 5)}",
        "client_ts": client_ts,
        "source": "web",
        "environment": "local",
        "app_version": "0.1.0",
        "page": "/dashboard",
        "referrer": None,
        "payload": build_payload(event_name, rng)
    }
    if user_id:
        event["user_id"] = user_id
    if anonymous_id:
        event["anonymous_id"] = anonymous_id
    return event


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate wearable events for demo.")
    parser.add_argument("--endpoint", default="http://localhost:8000/events")
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--count", type=int, default=50)
    args = parser.parse_args()

    rng = random.Random(args.seed)
    base_time = datetime(2024, 1, 1, tzinfo=timezone.utc)

    events = []
    for idx in range(args.count):
        event_name = EVENTS[idx % len(EVENTS)]
        timestamp = base_time + timedelta(seconds=idx * 30)
        events.append(build_event(event_name, rng, timestamp.isoformat()))

    response = requests.post(args.endpoint, json={"events": events}, timeout=10)
    response.raise_for_status()
    print(json.dumps(response.json(), indent=2))


if __name__ == "__main__":
    main()
