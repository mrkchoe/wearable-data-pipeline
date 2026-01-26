from __future__ import annotations

from pathlib import Path

import pandas as pd
import streamlit as st


st.set_page_config(page_title="Wearable Daily Summary", layout="wide")

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CSV = REPO_ROOT / "sample_data" / "daily_user_summary_sample.csv"

st.title("Wearable Daily Summary")
st.caption("Local-only dashboard using a CSV export of daily_user_summary.")

with st.sidebar:
    st.header("Data source")
    source = st.radio(
        "Choose data source",
        ["Sample data", "Local CSV path"],
        index=0,
    )
    csv_path_input = ""
    if source == "Local CSV path":
        csv_path_input = st.text_input(
            "Path to CSV",
            placeholder="/path/to/daily_user_summary.csv",
        )


def load_data() -> pd.DataFrame | None:
    if source == "Sample data":
        if not DEFAULT_CSV.exists():
            st.error(f"Sample file not found: {DEFAULT_CSV}")
            return None
        path = DEFAULT_CSV
    else:
        if not csv_path_input:
            st.info("Enter a local CSV path to continue.")
            return None
        path = Path(csv_path_input).expanduser()
        if not path.exists():
            st.error(f"CSV not found: {path}")
            return None
    try:
        data = pd.read_csv(path)
    except Exception as exc:  # pragma: no cover - streamlit runtime
        st.error(f"Failed to read CSV: {exc}")
        return None
    return data


df = load_data()
if df is None or df.empty:
    st.stop()

if "activity_date" in df.columns:
    df["activity_date"] = pd.to_datetime(df["activity_date"], errors="coerce")

st.subheader("Quick stats")
col1, col2, col3, col4 = st.columns(4)

user_count = df["user_id"].nunique() if "user_id" in df.columns else 0
date_min = df["activity_date"].min() if "activity_date" in df.columns else None
date_max = df["activity_date"].max() if "activity_date" in df.columns else None
avg_steps = df["total_steps"].mean() if "total_steps" in df.columns else None
avg_sleep = df["total_minutes_asleep"].mean() if "total_minutes_asleep" in df.columns else None

col1.metric("Users", f"{user_count}")
col2.metric("Date range", f"{date_min.date()} → {date_max.date()}" if date_min and date_max else "n/a")
col3.metric("Avg steps", f"{avg_steps:,.0f}" if avg_steps is not None else "n/a")
col4.metric("Avg sleep (min)", f"{avg_sleep:,.0f}" if avg_sleep is not None else "n/a")

st.subheader("Trends")
user_filter = "All users"
if "user_id" in df.columns:
    user_ids = sorted(df["user_id"].dropna().unique().tolist())
    user_filter = st.selectbox("User", ["All users"] + [str(uid) for uid in user_ids])
    if user_filter != "All users":
        df = df[df["user_id"].astype(str) == user_filter]

trend_cols = []
for col in ["total_steps", "total_minutes_asleep", "calories"]:
    if col in df.columns:
        trend_cols.append(col)

if "activity_date" in df.columns and trend_cols:
    chart_df = df.groupby("activity_date", as_index=False)[trend_cols].mean()
    st.line_chart(chart_df.set_index("activity_date"))
else:
    st.info("Add activity_date and metric columns to see charts.")

st.subheader("Data preview")
st.dataframe(df.head(25), use_container_width=True)
