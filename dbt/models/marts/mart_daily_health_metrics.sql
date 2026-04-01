-- Daily user metrics: steps and sleep efficiency (minutes asleep / time in bed).
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
    total_sleep_records,
    total_minutes_asleep,
    total_time_in_bed,
    case
        when total_time_in_bed is not null and total_time_in_bed > 0
            then round((total_minutes_asleep::numeric / total_time_in_bed), 4)
    end as sleep_efficiency_ratio,
    user_day_id
from {{ ref('daily_user_summary') }}
