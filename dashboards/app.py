from __future__ import annotations

import os

import altair as alt
import pandas as pd
import streamlit as st
from sqlalchemy import create_engine, text


st.set_page_config(page_title="Wearable Baseline Trends", layout="wide")
st.title("Baseline Engagement Trend")
st.caption("Cohort-level activity vs per-user baselines.")


def build_engine():
    host = os.getenv("DB_HOST", "localhost")
    port = os.getenv("DB_PORT", "5432")
    dbname = os.getenv("DB_NAME", "wearable")
    user = os.getenv("DB_USER", "wearable")
    password = os.getenv("DB_PASSWORD", "wearable")
    url = f"postgresql+psycopg2://{user}:{password}@{host}:{port}/{dbname}"
    return create_engine(url)


def load_date_bounds(engine) -> tuple[pd.Timestamp | None, pd.Timestamp | None]:
    query = """
        select
            min(activity_date) as min_date,
            max(activity_date) as max_date
        from user_activity_deviation
    """
    bounds = pd.read_sql(query, engine)
    if bounds.empty:
        return None, None
    min_date = bounds.loc[0, "min_date"]
    max_date = bounds.loc[0, "max_date"]
    return min_date, max_date


def load_deviation_data(engine, start_date, end_date, min_baseline_days: int) -> pd.DataFrame:
    query = text(
        """
        select
            activity_date,
            user_id,
            total_steps,
            baseline_steps,
            baseline_active_days,
            steps_pct_of_baseline
        from user_activity_deviation
        where activity_date between :start_date and :end_date
          and baseline_active_days >= :min_baseline_days
          and baseline_steps is not null
          and baseline_steps > 0
          and steps_pct_of_baseline is not null
        """
    )
    return pd.read_sql(
        query,
        engine,
        params={
            "start_date": start_date,
            "end_date": end_date,
            "min_baseline_days": min_baseline_days,
        },
    )


engine = build_engine()

try:
    min_date, max_date = load_date_bounds(engine)
except Exception as exc:  # pragma: no cover - streamlit runtime
    st.error(f"Failed to connect to Postgres: {exc}")
    st.stop()

if min_date is None or max_date is None:
    st.info("No data found in user_activity_deviation.")
    st.stop()

with st.sidebar:
    st.header("Filters")
    min_baseline_days = st.slider(
        "Minimum baseline days required",
        min_value=1,
        max_value=14,
        value=10,
    )
    date_range = st.date_input(
        "Date range",
        value=(min_date, max_date),
        min_value=min_date,
        max_value=max_date,
    )

if isinstance(date_range, tuple):
    start_date, end_date = date_range
else:
    start_date = date_range
    end_date = date_range

df = load_deviation_data(engine, start_date, end_date, min_baseline_days)
if df.empty:
    st.info("No rows match the selected filters.")
    st.stop()

df["activity_date"] = pd.to_datetime(df["activity_date"], errors="coerce")

daily = (
    df.groupby("activity_date")
    .agg(
        median_pct=("steps_pct_of_baseline", "median"),
        p25=("steps_pct_of_baseline", lambda s: s.quantile(0.25)),
        p75=("steps_pct_of_baseline", lambda s: s.quantile(0.75)),
        active_users=("user_id", "nunique"),
        pct_users_below_0_8=("steps_pct_of_baseline", lambda s: (s < 0.8).mean()),
    )
    .reset_index()
    .sort_values("activity_date")
)

latest = daily.iloc[-1]
st.subheader("Cohort KPIs")
kpi1, kpi2 = st.columns(2)
kpi1.metric("Active users (latest day)", f"{int(latest['active_users'])}")
kpi2.metric(
    "% below 0.8 baseline (latest day)",
    f"{latest['pct_users_below_0_8'] * 100:.1f}%",
)

kpi_chart = daily.set_index("activity_date")[["active_users", "pct_users_below_0_8"]]
kpi_chart["pct_users_below_0_8"] = kpi_chart["pct_users_below_0_8"] * 100
st.line_chart(kpi_chart, height=220)

st.subheader("Cohort deviation trend")
band = (
    alt.Chart(daily)
    .mark_area(opacity=0.2)
    .encode(
        x="activity_date:T",
        y="p25:Q",
        y2="p75:Q",
    )
)

median_line = (
    alt.Chart(daily)
    .mark_line()
    .encode(
        x="activity_date:T",
        y="median_pct:Q",
        tooltip=["activity_date:T", "median_pct:Q"],
    )
)

st.altair_chart(band + median_line, use_container_width=True)
