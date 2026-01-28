with activity as (
    select
        user_id,
        activity_date,
        total_steps
    from {{ ref('user_daily_activity') }}
    where total_steps is not null
      and total_steps > 0
),

ranked as (
    select
        user_id,
        activity_date,
        total_steps,
        row_number() over (
            partition by user_id
            order by activity_date
        ) as active_day_rank
    from activity
),

baseline_window as (
    select
        user_id,
        activity_date,
        total_steps
    from ranked
    where active_day_rank <= 14
),

baseline_summary as (
    select
        user_id,
        min(activity_date) as baseline_start_date,
        max(activity_date) as baseline_end_date,
        count(*) as baseline_active_days,
        percentile_cont(0.5) within group (order by total_steps) as baseline_steps
    from baseline_window
    group by user_id
)

select *
from baseline_summary
