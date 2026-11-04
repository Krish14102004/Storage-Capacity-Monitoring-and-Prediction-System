"""Streamlit overview dashboard for storage capacity monitoring."""

import plotly.express as px
import streamlit as st

from modules.alert_manager import classify_utilization
from modules.dashboard_helpers import (
    latest_records_by_server,
    load_dashboard_records,
    page_title,
)


st.set_page_config(
    page_title="Storage Capacity Monitor",
    page_icon="💾",
    layout="wide",
)

records = load_dashboard_records()
page_title(
    "Storage Capacity Overview",
    "Current capacity and historical utilization across the simulated servers.",
)

latest = latest_records_by_server(records)
total_capacity = latest["total_capacity_gb"].sum()
used_storage = latest["used_storage_gb"].sum()
available_storage = latest["available_storage_gb"].sum()
average_utilization = latest["usage_percentage"].mean()

metric_columns = st.columns(4)
metric_columns[0].metric("Total capacity", f"{total_capacity:,.2f} GB")
metric_columns[1].metric("Used storage", f"{used_storage:,.2f} GB")
metric_columns[2].metric("Available storage", f"{available_storage:,.2f} GB")
metric_columns[3].metric("Average utilization", f"{average_utilization:.2f}%")

st.subheader("Latest server status")
latest["status"] = latest["usage_percentage"].map(classify_utilization)
st.dataframe(
    latest[
        [
            "server_id",
            "total_capacity_gb",
            "used_storage_gb",
            "available_storage_gb",
            "usage_percentage",
            "status",
            "date",
        ]
    ].rename(
        columns={
            "server_id": "Server",
            "total_capacity_gb": "Total capacity (GB)",
            "used_storage_gb": "Used (GB)",
            "available_storage_gb": "Available (GB)",
            "usage_percentage": "Utilization (%)",
            "status": "Status",
            "date": "Observation date",
        }
    ),
    hide_index=True,
    width="stretch",
)

st.subheader("Historical utilization")
history_chart = px.line(
    records.sort_values("date"),
    x="date",
    y="usage_percentage",
    color="server_id",
    markers=False,
    labels={
        "date": "Date",
        "usage_percentage": "Utilization (%)",
        "server_id": "Server",
    },
)
history_chart.update_layout(legend_title_text="Server")
st.plotly_chart(history_chart, width="stretch")

st.caption(
    "Forecasts are estimates based on historical trends. Use Capacity Prediction "
    "for the selected forecast horizon and assumptions."
)
