-- Flags calendar days where stg_daily_activity row count deviates >30% from trailing 7-day average.
with daily_counts as (
    select
        activity_date as metric_date,
        count(*)::bigint as row_count
    from {{ ref('stg_daily_activity') }}
    group by 1
),

ordered as (
    select
        metric_date,
        row_count,
        avg(row_count) over (
            order by metric_date
            rows between 7 preceding and 1 preceding
        ) as trailing_avg_row_count
    from daily_counts
)

select
    metric_date,
    row_count,
    trailing_avg_row_count,
    case
        when trailing_avg_row_count is null or trailing_avg_row_count = 0 then false
        when abs(row_count::numeric - trailing_avg_row_count) / trailing_avg_row_count > 0.3 then true
        else false
    end as row_count_anomaly_flag
from ordered
