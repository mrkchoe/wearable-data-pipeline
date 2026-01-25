## Analytics data contract

### Schema versioning
- `schema_version` is required on every event and follows semantic versioning (`MAJOR.MINOR.PATCH`).
- `PATCH` is for documentation-only or non-functional updates.
- `MINOR` adds new optional fields or new event types.
- `MAJOR` is reserved for breaking changes (field removals, type changes, or required field additions).

### Compatibility rules
- The client must only emit events that conform to the latest published schema.
- The backend/warehouse must accept `schema_version` within the same major version.
- New optional fields must be safe to ignore by downstream consumers.
- Breaking changes require a new major version and a coordinated backfill strategy.

### Deprecation policy
- Deprecated events/fields remain readable for at least one minor release.
- Emitters should stop sending deprecated fields after two minor releases.
