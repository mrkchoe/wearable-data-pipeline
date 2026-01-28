with activity as (
    select
        user_id,
        activity_date,
        total_steps,
        total_distance,
        very_active_minutes,
        fairly_active_minutes,
        lightly_active_minutes,
        sedentary_minutes,
        calories,
        user_id::text || '-' || activity_date::text as user_day_id
    from {{ ref('stg_daily_activity') }}
)

select *
from activity
