with activity as (
    select
        user_id,
        activity_date,
        sum(total_steps) as total_steps,
        sum(total_distance) as total_distance,
        sum(very_active_minutes) as very_active_minutes,
        sum(fairly_active_minutes) as fairly_active_minutes,
        sum(lightly_active_minutes) as lightly_active_minutes,
        sum(sedentary_minutes) as sedentary_minutes,
        sum(calories) as calories
    from {{ ref('stg_daily_activity') }}
    group by 1, 2
),

sleep as (
    select
        user_id,
        sleep_date,
        sum(total_sleep_records) as total_sleep_records,
        sum(total_minutes_asleep) as total_minutes_asleep,
        sum(total_time_in_bed) as total_time_in_bed
    from {{ ref('stg_sleep') }}
    group by 1, 2
),

joined as (
    select
        activity.user_id,
        activity.activity_date,
        activity.total_steps,
        activity.total_distance,
        activity.very_active_minutes,
        activity.fairly_active_minutes,
        activity.lightly_active_minutes,
        activity.sedentary_minutes,
        activity.calories,
        sleep.total_sleep_records,
        sleep.total_minutes_asleep,
        sleep.total_time_in_bed,
        activity.user_id::text || '-' || activity.activity_date::text as user_day_id
    from activity
    left join sleep
        on activity.user_id = sleep.user_id
        and activity.activity_date = sleep.sleep_date
),

final as (
    select
        user_id,
        activity_date,
        max(total_steps) as total_steps,
        max(total_distance) as total_distance,
        max(very_active_minutes) as very_active_minutes,
        max(fairly_active_minutes) as fairly_active_minutes,
        max(lightly_active_minutes) as lightly_active_minutes,
        max(sedentary_minutes) as sedentary_minutes,
        max(calories) as calories,
        max(total_sleep_records) as total_sleep_records,
        max(total_minutes_asleep) as total_minutes_asleep,
        max(total_time_in_bed) as total_time_in_bed,
        max(user_day_id) as user_day_id
    from joined
    group by 1, 2
)

select *
from final
