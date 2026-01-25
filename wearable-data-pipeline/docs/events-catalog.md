## Events catalog

All events include the BaseEvent fields: `event_id`, `schema_version`, `client_ts`, `session_id`, `page`, `referrer`, `app_version`, `environment`, `source`, and `correlation_id`, plus either `user_id` or `anonymous_id`.

| event_name | description | required fields | sample payload |
| --- | --- | --- | --- |
| page_view | Page load for key screens. | `page_title`, `entry_point` | `{ "event_name": "page_view", "page_title": "Dashboard", "entry_point": "direct" }` |
| identify | User identity resolved. | `user_status` | `{ "event_name": "identify", "user_status": "known" }` |
| connect_device_started | User starts device connect. | `vendor` | `{ "event_name": "connect_device_started", "vendor": "fitbit" }` |
| connect_device_succeeded | Device connection success. | `vendor`, `device_model` | `{ "event_name": "connect_device_succeeded", "vendor": "fitbit", "device_model": "Wearable Pro X" }` |
| connect_device_failed | Device connection fails. | `vendor`, `error_code`, `error_message` | `{ "event_name": "connect_device_failed", "vendor": "fitbit", "error_code": "DEVICE_CONNECT_FAILED", "error_message": "Timeout" }` |
| sync_requested | User triggers sync. | `vendor`, `date_range`, `sync_status` | `{ "event_name": "sync_requested", "vendor": "fitbit", "date_range": "week", "sync_status": "requested" }` |
| sync_completed | Sync finished successfully. | `vendor`, `date_range`, `sync_status`, `records_synced` | `{ "event_name": "sync_completed", "vendor": "fitbit", "date_range": "week", "sync_status": "completed", "records_synced": 42 }` |
| sync_failed | Sync failed. | `vendor`, `date_range`, `sync_status`, `error_code`, `error_message` | `{ "event_name": "sync_failed", "vendor": "fitbit", "date_range": "week", "sync_status": "failed", "error_code": "SYNC_FAILED", "error_message": "API error" }` |
| metric_viewed | Metric chart viewed. | `metric_type`, `date_range`, `vendor` | `{ "event_name": "metric_viewed", "metric_type": "steps", "date_range": "week", "vendor": "fitbit" }` |
| goal_created | User saves a goal. | `metric_type`, `target_value`, `target_unit`, `date_range` | `{ "event_name": "goal_created", "metric_type": "steps", "target_value": 8000, "target_unit": "count", "date_range": "week" }` |
| export_clicked | User exports data. | `export_format`, `date_range`, `vendor` | `{ "event_name": "export_clicked", "export_format": "csv", "date_range": "week", "vendor": "fitbit" }` |
| ui_error | UI error captured. | `component`, `error_code`, `error_message`, `severity` | `{ "event_name": "ui_error", "component": "GoalCard", "error_code": "VALIDATION_FAILED", "error_message": "Goal target invalid", "severity": "warning" }` |
| api_error | API error captured. | `endpoint`, `status_code`, `error_code`, `error_message` | `{ "event_name": "api_error", "endpoint": "/api/dashboard", "status_code": 500, "error_code": "DASHBOARD_FETCH_FAILED", "error_message": "Timeout" }` |
| perf_lcp | Largest contentful paint. | `lcp_ms`, `page_type` | `{ "event_name": "perf_lcp", "lcp_ms": 1240, "page_type": "dashboard" }` |
| perf_api_latency | API latency for a call. | `api_latency_ms`, `endpoint`, `status_code` | `{ "event_name": "perf_api_latency", "api_latency_ms": 220, "endpoint": "/api/dashboard", "status_code": 200 }` |
