## Wearable analytics data contract

### Scope
- Schemas live in `schemas/events/` and represent the canonical event contract for ingestion.
- `wearable_event.json` is the primary schema for event validation.

### Versioning
- `schema_version` follows semantic versioning (`MAJOR.MINOR.PATCH`).
- `PATCH` is documentation-only or non-functional changes.
- `MINOR` adds new optional fields or new event types.
- `MAJOR` is breaking changes (field removals, type changes, required field additions).

### Compatibility rules
- Ingestion accepts any `schema_version` within the same major version.
- New optional fields must be safe to ignore downstream.
- Breaking changes require a new major version and a planned backfill strategy.
- Event producers should always emit the latest non-breaking schema version.
- Optional fields should be omitted when unknown rather than sent as `null`.

### Idempotency + dedupe
- `event_id` is required and used as the dedupe key.
- Ingestion must treat duplicate `event_id`s as safe no-ops.
