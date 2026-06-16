from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from dq_monitoring.db import fetch_dataframe, get_engine  # noqa: E402


st.set_page_config(page_title="Data Quality Monitoring", page_icon=":bar_chart:", layout="wide")


@st.cache_resource
def engine():
    return get_engine()


@st.cache_data(ttl=60)
def load_data() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    db = engine()
    status = fetch_dataframe(db, "select * from mart_source_status order by status, source_name")
    quality = fetch_dataframe(
        db,
        """
        select *
        from mart_daily_quality
        where metric_date >= current_date - interval '60 days'
        order by metric_date, source_name
        """,
    )
    incidents = fetch_dataframe(
        db,
        """
        select *
        from mart_incident_summary
        order by opened_at desc
        limit 200
        """,
    )
    return status, quality, incidents


def format_status(value: str) -> str:
    return {
        "healthy": "Healthy",
        "warning": "Warning",
        "critical": "Critical",
        "no_data": "No data",
    }.get(value, value)


status_df, quality_df, incidents_df = load_data()

st.title("Data Quality Monitoring")

if status_df.empty:
    st.warning("No monitoring data found. Run `python scripts/run_pipeline.py --days 30 --reset`.")
    st.stop()

latest_quality = quality_df.sort_values("metric_date").groupby("source_name").tail(1)

total_sources = len(status_df)
critical_sources = int((status_df["status"] == "critical").sum())
warning_sources = int((status_df["status"] == "warning").sum())
open_incidents = int(status_df["open_incidents"].sum())

metric_cols = st.columns(4)
metric_cols[0].metric("Sources", total_sources)
metric_cols[1].metric("Critical", critical_sources)
metric_cols[2].metric("Warning", warning_sources)
metric_cols[3].metric("Open incidents", open_incidents)

st.subheader("Source Status")
status_view = status_df.copy()
status_view["status"] = status_view["status"].map(format_status)
status_view["completeness_rate"] = status_view["completeness_rate"].astype(float).round(3)
status_view["duplicate_rate"] = status_view["duplicate_rate"].astype(float).round(3)
status_view["null_rate"] = status_view["null_rate"].astype(float).round(3)
status_view["record_count_delta"] = status_view["record_count_delta"].astype(float).round(3)
st.dataframe(
    status_view[
        [
            "source_name",
            "domain",
            "owner_team",
            "last_batch_date",
            "status",
            "completeness_rate",
            "freshness_lag_minutes",
            "duplicate_rate",
            "null_rate",
            "record_count_delta",
            "schema_drift_flag",
            "failed_jobs_count",
            "open_incidents",
        ]
    ],
    use_container_width=True,
    hide_index=True,
)

left, right = st.columns([1, 2])
with left:
    source_names = sorted(quality_df["source_name"].dropna().unique())
    selected_source = st.selectbox("Source", source_names)
    metric_name = st.selectbox(
        "Metric",
        [
            "completeness_rate",
            "freshness_lag_minutes",
            "duplicate_rate",
            "null_rate",
            "record_count_delta",
            "failed_jobs_count",
        ],
    )

with right:
    source_quality = quality_df[quality_df["source_name"] == selected_source].copy()
    source_quality["metric_date"] = pd.to_datetime(source_quality["metric_date"])
    st.line_chart(source_quality.set_index("metric_date")[[metric_name]])

st.subheader("Latest Quality Snapshot")
snapshot = latest_quality[
    [
        "source_name",
        "metric_date",
        "completeness_rate",
        "freshness_lag_minutes",
        "duplicate_rate",
        "null_rate",
        "record_count_delta",
        "schema_drift_flag",
        "failed_jobs_count",
        "total_records",
    ]
].copy()
st.dataframe(snapshot, use_container_width=True, hide_index=True)

st.subheader("Incidents")
if incidents_df.empty:
    st.success("No incidents found.")
else:
    incident_filter = st.radio(
        "Status",
        options=["all", "open", "acknowledged", "resolved"],
        index=0,
        horizontal=True,
    )
    filtered_incidents = incidents_df.copy()
    if incident_filter != "all":
        filtered_incidents = filtered_incidents[filtered_incidents["status"] == incident_filter]
    st.dataframe(
        filtered_incidents[
            [
                "opened_at",
                "batch_date",
                "source_name",
                "severity",
                "status",
                "metric_name",
                "metric_value",
                "threshold_value",
                "title",
            ]
        ],
        use_container_width=True,
        hide_index=True,
    )
