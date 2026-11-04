"""Streamlit page for server-wise storage metrics and history."""

import plotly.graph_objects as go
import streamlit as st

from modules.dashboard_helpers import (
    load_dashboard_records,
    page_title,
    render_date_filter,
)


st.set_page_config(
    page_title="Storage Monitoring",
    page_icon="📊",
    layout="wide",
)

records = load_dashboard_records()
page_title(
    "Storage Monitoring",
    "Review capacity, available space, and observed storage history for a server.",
)

server_ids = sorted(records["server_id"].unique())
server_id = st.selectbox("Server", server_ids, key="monitor_server")
server_records = records[records["server_id"] == server_id].copy()
start_date, end_date = render_date_filter(
    server_records,
    key="monitor_date_range",
)
filtered = server_records[
    server_records["date"].between(start_date, end_date)
].sort_values("date")

if filtered.empty:
    st.info("No observations are available for the selected server and date range.")
    st.stop()

latest = filtered.iloc[-1]
columns = st.columns(4)
columns[0].metric("Total capacity", f"{latest['total_capacity_gb']:,.2f} GB")
columns[1].metric("Used storage", f"{latest['used_storage_gb']:,.2f} GB")
columns[2].metric("Available storage", f"{latest['available_storage_gb']:,.2f} GB")
columns[3].metric("Utilization", f"{latest['usage_percentage']:.2f}%")
st.caption(f"Latest selected observation: {latest['date'].date().isoformat()}")

st.subheader("Observed storage history")
figure = go.Figure()
figure.add_trace(
    go.Scatter(
        x=filtered["date"],
        y=filtered["used_storage_gb"],
        name="Used storage",
        mode="lines+markers",
        line={"color": "#2563EB", "width": 2},
    )
)
figure.add_trace(
    go.Scatter(
        x=filtered["date"],
        y=filtered["available_storage_gb"],
        name="Available storage",
        mode="lines",
        line={"color": "#16A34A", "width": 2},
    )
)
figure.update_layout(
    xaxis_title="Date",
    yaxis_title="Storage (GB)",
    legend_title="Measurement",
    hovermode="x unified",
)
st.plotly_chart(figure, width="stretch")

st.subheader("Storage observations")
st.dataframe(
    filtered[
        [
            "date",
            "total_capacity_gb",
            "used_storage_gb",
            "available_storage_gb",
            "usage_percentage",
        ]
    ].rename(
        columns={
            "date": "Date",
            "total_capacity_gb": "Total capacity (GB)",
            "used_storage_gb": "Used (GB)",
            "available_storage_gb": "Available (GB)",
            "usage_percentage": "Utilization (%)",
        }
    ),
    hide_index=True,
    width="stretch",
)
