"""Shared data loading and presentation helpers for the Streamlit dashboard."""

import sqlite3
from pathlib import Path

import pandas as pd
import streamlit as st

from modules.data_loader import load_and_validate_csv
from modules.database_manager import get_storage_records, import_storage_records


SYNTHETIC_DATA_NOTICE = (
    "Synthetic data — these records are simulated and are not live "
    "server telemetry."
)


def load_dashboard_records() -> pd.DataFrame:
    """Load persisted observations, importing the approved CSV only if empty."""
    try:
        records = get_storage_records()
        if records.empty:
            data_path = Path(__file__).resolve().parents[1] / "data" / "storage_data.csv"
            csv_records = load_and_validate_csv(data_path)
            import_storage_records(csv_records)
            records = get_storage_records()
    except (FileNotFoundError, ValueError, OSError, sqlite3.Error) as exc:
        st.error(
            "Storage data could not be loaded. Check that "
            "`data/storage_data.csv` is valid and that the local database directory "
            f"is writable. Details: {exc}"
        )
        st.stop()

    if records.empty:
        st.error("No storage records are available in the local database or CSV.")
        st.stop()

    records["date"] = pd.to_datetime(records["date"], errors="raise")
    return records


def render_synthetic_data_notice() -> None:
    """Show the required synthetic-data disclosure on every dashboard page."""
    st.warning(SYNTHETIC_DATA_NOTICE)


def latest_records_by_server(records: pd.DataFrame) -> pd.DataFrame:
    """Return one latest observation per server in stable server order."""
    return (
        records.sort_values(["date", "server_id"])
        .groupby("server_id", as_index=False, sort=True)
        .tail(1)
        .sort_values("server_id")
        .reset_index(drop=True)
    )


def render_date_filter(
    records: pd.DataFrame,
    *,
    key: str,
) -> tuple[pd.Timestamp, pd.Timestamp]:
    """Render a date-range selector and return validated timestamp bounds."""
    first_date = records["date"].min().date()
    last_date = records["date"].max().date()
    selection = st.date_input(
        "Date range",
        value=(first_date, last_date),
        min_value=first_date,
        max_value=last_date,
        key=key,
    )
    if not isinstance(selection, (tuple, list)) or len(selection) != 2:
        st.info("Select both a start date and an end date.")
        st.stop()
    start_date, end_date = selection
    if start_date > end_date:
        st.error("The start date must be on or before the end date.")
        st.stop()
    return pd.Timestamp(start_date), pd.Timestamp(end_date)


def page_title(title: str, subtitle: str) -> None:
    """Render a consistent title and subtitle for a dashboard page."""
    st.title(title)
    st.caption(subtitle)
    render_synthetic_data_notice()
