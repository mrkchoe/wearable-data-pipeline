with activity as (
    select *
    from {{ ref('user_daily_activity') }}
),

baseline as (
    select *
    from {{ ref('user_baseline_activity') }}
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
        activity.user_day_id,
        baseline.baseline_steps,
        baseline.baseline_start_date,
        baseline.baseline_end_date,
        baseline.baseline_active_days,
        case
            when baseline.baseline_steps is null or baseline.baseline_steps = 0 then null
            else activity.total_steps / baseline.baseline_steps
        end as steps_pct_of_baseline,
        case
            when baseline.baseline_steps is null then null
            else activity.total_steps - baseline.baseline_steps
        end as steps_delta_from_baseline,
        case
            when activity.activity_date between baseline.baseline_start_date
                and baseline.baseline_end_date then true
            else false
        end as is_baseline_window
    from activity
    left join baseline
        on activity.user_id = baseline.user_id
)

select *
from joined
