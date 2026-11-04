"""Streamlit page for per-server Linear Regression forecasts."""

import plotly.graph_objects as go
import streamlit as st

from models.prediction_model import MAX_FORECAST_DAYS, predict_server_usage
from modules.dashboard_helpers import load_dashboard_records, page_title


st.set_page_config(
    page_title="Capacity Prediction",
    page_icon="📈",
    layout="wide",
)

records = load_dashboard_records()
page_title(
    "Capacity Prediction",
    "Estimate future used storage from the selected server's historical trend.",
)

server_ids = sorted(records["server_id"].unique())
server_id = st.selectbox("Server", server_ids, key="prediction_server")
server_records = records[records["server_id"] == server_id].sort_values("date")
first, last = st.columns(2)
forecast_days = first.slider(
    "Forecast horizon (days)",
    min_value=1,
    max_value=MAX_FORECAST_DAYS,
    value=30,
    help="Forecast horizon is capped at 90 days.",
)
threshold_percentage = last.slider(
    "Threshold for estimated date (%)",
    min_value=1,
    max_value=100,
    value=100,
    help="Choose the utilization threshold whose estimated crossing date you want to assess.",
)

try:
    result = predict_server_usage(
        server_records,
        forecast_days=forecast_days,
        threshold_percentage=threshold_percentage,
    )
except ValueError as exc:
    st.error(f"A forecast could not be calculated: {exc}")
    st.stop()

latest = server_records.iloc[-1]
columns = st.columns(3)
columns[0].metric("Current used storage", f"{latest['used_storage_gb']:,.2f} GB")
columns[1].metric("Observed capacity", f"{latest['total_capacity_gb']:,.2f} GB")
columns[2].metric("Fitted trend", f"{result.slope_gb_per_day:.2f} GB/day")

if result.threshold_date is None:
    st.info(result.threshold_estimate_message)
else:
    st.success(
        f"{result.threshold_estimate_message} Estimated date: "
        f"{result.threshold_date.date().isoformat()}."
    )

st.warning(
    f"Forecast horizon: {forecast_days} days. These predictions are estimates "
    "from a Linear Regression fitted to historical observations; actual usage "
    "may differ."
)

figure = go.Figure()
figure.add_trace(
    go.Scatter(
        x=server_records["date"],
        y=server_records["used_storage_gb"],
        name="Observed used storage",
        mode="lines+markers",
        line={"color": "#2563EB", "width": 2},
    )
)
forecast_dates = [latest["date"], *result.forecast["date"].tolist()]
forecast_values = [
    float(latest["used_storage_gb"]),
    *result.forecast["predicted_used_storage_gb"].astype(float).tolist(),
]
figure.add_trace(
    go.Scatter(
        x=forecast_dates,
        y=forecast_values,
        name="Linear Regression estimate",
        mode="lines+markers",
        line={"color": "#EA580C", "width": 2, "dash": "dash"},
    )
)
threshold_gb = float(latest["total_capacity_gb"]) * threshold_percentage / 100
figure.add_hline(
    y=threshold_gb,
    line_dash="dot",
    line_color="#DC2626",
    annotation_text=f"{threshold_percentage}% threshold ({threshold_gb:,.1f} GB)",
)
figure.update_layout(
    xaxis_title="Date",
    yaxis_title="Used storage (GB)",
    legend_title="Series",
    hovermode="x unified",
)
st.plotly_chart(figure, width="stretch")

st.subheader("Forecast values")
st.dataframe(
    result.forecast.rename(
        columns={
            "date": "Date",
            "days_ahead": "Days ahead",
            "predicted_used_storage_gb": "Estimated used storage (GB)",
        }
    ).style.format({"Estimated used storage (GB)": "{:,.2f}"}),
    hide_index=True,
    width="stretch",
)
