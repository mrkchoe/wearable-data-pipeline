with source as (
    select *
    from {{ source('raw', 'daily_activity') }}
),

renamed as (
    select
        cast("Id" as bigint) as user_id,
        to_date("ActivityDate", 'MM/DD/YYYY') as activity_date,
        cast("TotalSteps" as integer) as total_steps,
        cast("TotalDistance" as numeric(10, 2)) as total_distance,
        cast("VeryActiveMinutes" as integer) as very_active_minutes,
        cast("FairlyActiveMinutes" as integer) as fairly_active_minutes,
        cast("LightlyActiveMinutes" as integer) as lightly_active_minutes,
        cast("SedentaryMinutes" as integer) as sedentary_minutes,
        cast("Calories" as integer) as calories
    from source
)

select *
from renamed
