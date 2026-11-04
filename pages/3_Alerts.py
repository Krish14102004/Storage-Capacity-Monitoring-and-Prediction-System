"""Streamlit page for configurable threshold status and alerts."""

import plotly.express as px
import streamlit as st

from modules.alert_manager import (
    AlertThresholds,
    classify_utilization,
    generate_current_alerts,
)
from modules.dashboard_helpers import (
    latest_records_by_server,
    load_dashboard_records,
    page_title,
)


st.set_page_config(
    page_title="Storage Alerts",
    page_icon="🚦",
    layout="wide",
)

records = load_dashboard_records()
page_title(
    "Storage Alerts",
    "Review each server's latest status using configurable utilization thresholds.",
)

st.subheader("Configure utilization thresholds")
saved_thresholds = st.session_state.get(
    "alert_threshold_values",
    {"warning": 70.0, "critical": 85.0, "emergency": 95.0},
)
with st.form("alert_threshold_form"):
    threshold_columns = st.columns(3)
    warning_threshold = threshold_columns[0].number_input(
        "Warning begins at (%)",
        min_value=0.0,
        max_value=98.0,
        value=saved_thresholds["warning"],
    )
    critical_threshold = threshold_columns[1].number_input(
        "Critical begins at (%)",
        min_value=1.0,
        max_value=99.0,
        value=saved_thresholds["critical"],
    )
    emergency_threshold = threshold_columns[2].number_input(
        "Emergency begins at (%)",
        min_value=2.0,
        max_value=100.0,
        value=saved_thresholds["emergency"],
    )
    submitted = st.form_submit_button("Apply thresholds")

if submitted:
    try:
        thresholds = AlertThresholds(
            warning=warning_threshold,
            critical=critical_threshold,
            emergency=emergency_threshold,
        )
    except ValueError as exc:
        st.error(f"Thresholds were not applied: {exc}")
        thresholds = AlertThresholds(**saved_thresholds)
    else:
        saved_thresholds = {
            "warning": thresholds.warning,
            "critical": thresholds.critical,
            "emergency": thresholds.emergency,
        }
        st.session_state["alert_threshold_values"] = saved_thresholds
else:
    thresholds = AlertThresholds(**saved_thresholds)

warning_threshold = thresholds.warning
critical_threshold = thresholds.critical
emergency_threshold = thresholds.emergency
st.caption(
    f"Normal: below {warning_threshold}% · Warning: "
    f"{warning_threshold}% to below {critical_threshold}% · Critical: "
    f"{critical_threshold}% to below {emergency_threshold}% · Emergency: "
    f"{emergency_threshold}% to 100%."
)

latest = latest_records_by_server(records)
latest["severity"] = latest["usage_percentage"].map(
    lambda value: classify_utilization(value, thresholds)
)
alerts = generate_current_alerts(records, thresholds)

st.subheader("Latest server status")
st.dataframe(
    latest[
        [
            "server_id",
            "date",
            "usage_percentage",
            "severity",
            "used_storage_gb",
            "available_storage_gb",
            "total_capacity_gb",
        ]
    ].rename(
        columns={
            "server_id": "Server",
            "date": "Observation date",
            "usage_percentage": "Utilization (%)",
            "severity": "Status",
            "used_storage_gb": "Used (GB)",
            "available_storage_gb": "Available (GB)",
            "total_capacity_gb": "Total capacity (GB)",
        }
    ),
    hide_index=True,
    width="stretch",
)

status_chart = px.bar(
    latest,
    x="server_id",
    y="usage_percentage",
    color="severity",
    category_orders={
        "severity": ["Normal", "Warning", "Critical", "Emergency"]
    },
    color_discrete_map={
        "Normal": "#16A34A",
        "Warning": "#D97706",
        "Critical": "#EA580C",
        "Emergency": "#DC2626",
    },
    labels={
        "server_id": "Server",
        "usage_percentage": "Utilization (%)",
        "severity": "Status",
    },
    range_y=[0, 100],
)
st.plotly_chart(status_chart, width="stretch")

st.subheader("Current threshold alerts")
if alerts.empty:
    st.success("No servers currently exceed the Normal status threshold.")
else:
    st.dataframe(
        alerts[
            [
                "severity",
                "server_id",
                "usage_percentage",
                "threshold_crossed",
                "date",
                "message",
            ]
        ].rename(
            columns={
                "severity": "Severity",
                "server_id": "Server",
                "usage_percentage": "Utilization (%)",
                "threshold_crossed": "Threshold (%)",
                "date": "Observation date",
                "message": "Details",
            }
        ),
        hide_index=True,
        width="stretch",
    )
st.caption(
    "Alerts are calculated from each server's latest observation as a "
    "current-state view; refreshing the page does not create stored duplicate alerts."
)
