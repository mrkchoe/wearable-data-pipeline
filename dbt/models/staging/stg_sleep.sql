with source as (
    select *
    from {{ source('raw', 'sleep') }}
),

renamed as (
    select
        cast("Id" as bigint) as user_id,
        to_timestamp("SleepDay", 'MM/DD/YYYY HH12:MI:SS AM')::date as sleep_date,
        cast("TotalSleepRecords" as integer) as total_sleep_records,
        cast("TotalMinutesAsleep" as integer) as total_minutes_asleep,
        cast("TotalTimeInBed" as integer) as total_time_in_bed
    from source
)

select *
from renamed
