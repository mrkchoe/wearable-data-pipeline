with source as (
    select *
    from {{ source('raw', 'raw_events') }}
),

parsed as (
    select
        event_id::text as event_id,
        event_name,
        schema_version,
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
        payload,
        payload ->> 'vendor' as vendor,
        payload ->> 'metric_type' as metric_type,
        payload ->> 'date_range' as date_range,
        payload ->> 'sync_status' as sync_status,
        (payload ->> 'records_synced')::integer as records_synced,
        (payload ->> 'target_value')::numeric as target_value,
        payload ->> 'target_unit' as target_unit,
        payload ->> 'export_format' as export_format,
        payload ->> 'error_code' as error_code,
        payload ->> 'error_message' as error_message,
        (payload ->> 'lcp_ms')::numeric as lcp_ms,
        (payload ->> 'api_latency_ms')::numeric as api_latency_ms,
        payload ->> 'endpoint' as endpoint,
        (payload ->> 'status_code')::integer as status_code
    from source
)

select *
from parsed
