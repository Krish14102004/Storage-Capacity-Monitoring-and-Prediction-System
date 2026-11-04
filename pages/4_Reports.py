"""Streamlit page for filtered CSV and PDF report downloads."""

from datetime import datetime

import streamlit as st

from modules.dashboard_helpers import (
    load_dashboard_records,
    page_title,
    render_date_filter,
)
from modules.report_generator import (
    DEFAULT_DATA_LABEL,
    generate_csv_report,
    generate_pdf_report,
)


st.set_page_config(
    page_title="Storage Reports",
    page_icon="📄",
    layout="wide",
)

records = load_dashboard_records()
page_title(
    "Storage Reports",
    "Filter the observations, review the selection, and download CSV or PDF reports.",
)

server_options = ["All servers", *sorted(records["server_id"].unique())]
server_selection = st.selectbox("Server", server_options, key="report_server")
if server_selection == "All servers":
    server_records = records
else:
    server_records = records[records["server_id"] == server_selection]

start_date, end_date = render_date_filter(
    server_records,
    key="report_date_range",
)
selected_records = server_records[
    server_records["date"].between(start_date, end_date)
].sort_values(["date", "server_id"])

st.info(
    f"Report label: {DEFAULT_DATA_LABEL}. Selected records: "
    f"{len(selected_records)}."
)
if selected_records.empty:
    st.warning("No records match these filters. Downloads will contain an empty report.")
else:
    st.dataframe(
        selected_records[
            [
                "date",
                "server_id",
                "total_capacity_gb",
                "used_storage_gb",
                "available_storage_gb",
                "usage_percentage",
            ]
        ].rename(
            columns={
                "date": "Date",
                "server_id": "Server",
                "total_capacity_gb": "Total capacity (GB)",
                "used_storage_gb": "Used (GB)",
                "available_storage_gb": "Available (GB)",
                "usage_percentage": "Utilization (%)",
            }
        ),
        hide_index=True,
        width="stretch",
    )

generated_at = datetime.now().astimezone()
filename_date = generated_at.strftime("%Y%m%d_%H%M%S")
try:
    csv_report = generate_csv_report(
        selected_records,
        generated_at=generated_at,
    )
    pdf_report = generate_pdf_report(
        selected_records,
        generated_at=generated_at,
    )
except (TypeError, ValueError) as exc:
    st.error(f"Reports could not be generated: {exc}")
    st.stop()

download_columns = st.columns(2)
download_columns[0].download_button(
    "Download CSV report",
    data=csv_report,
    file_name=f"storage_report_{filename_date}.csv",
    mime="text/csv",
    width="stretch",
)
download_columns[1].download_button(
    "Download PDF report",
    data=pdf_report,
    file_name=f"storage_report_{filename_date}.pdf",
    mime="application/pdf",
    width="stretch",
)
