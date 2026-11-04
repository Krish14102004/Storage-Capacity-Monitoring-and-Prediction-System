"""[Phase 4] Tests for CSV and PDF storage report exports."""

from datetime import datetime
from io import BytesIO

import pandas as pd
import pytest

from modules.report_generator import (
    DEFAULT_DATA_LABEL,
    generate_csv_report,
    generate_pdf_report,
)


FIXED_GENERATED_AT = datetime(2024, 2, 1, 12, 30)


def valid_records():
    return pd.DataFrame(
        [
            {
                "date": "2024-01-02",
                "server_id": "Server A",
                "total_capacity_gb": 100.0,
                "used_storage_gb": 45.0,
                "available_storage_gb": 55.0,
                "usage_percentage": 45.0,
            },
            {
                "date": "2024-01-01",
                "server_id": "Server A",
                "total_capacity_gb": 100.0,
                "used_storage_gb": 40.0,
                "available_storage_gb": 60.0,
                "usage_percentage": 40.0,
            },
            {
                "date": "2024-01-01",
                "server_id": "Server B",
                "total_capacity_gb": 200.0,
                "used_storage_gb": 100.0,
                "available_storage_gb": 100.0,
                "usage_percentage": 50.0,
            },
        ]
    )


def test_csv_report_contains_context_units_and_sorted_records():
    original = valid_records()
    report_bytes = generate_csv_report(original, generated_at=FIXED_GENERATED_AT)
    report = pd.read_csv(BytesIO(report_bytes))

    assert report["data_label"].unique().tolist() == [DEFAULT_DATA_LABEL]
    assert report["report_generated_at"].unique().tolist() == ["2024-02-01 12:30"]
    assert report["report_servers"].unique().tolist() == ["Server A, Server B"]
    assert report["report_start_date"].unique().tolist() == ["2024-01-01"]
    assert report["report_end_date"].unique().tolist() == ["2024-01-02"]
    assert report["date"].tolist() == ["2024-01-01", "2024-01-01", "2024-01-02"]
    assert report["server_id"].tolist() == ["Server A", "Server B", "Server A"]
    assert report["total_capacity_gb"].tolist() == [100.0, 200.0, 100.0]
    assert report["usage_percentage"].tolist() == [40.0, 50.0, 45.0]
    pd.testing.assert_frame_equal(original, valid_records())


def test_csv_report_supports_an_explicit_data_label():
    report = pd.read_csv(
        BytesIO(generate_csv_report(valid_records(), data_label="Approved sample"))
    )

    assert report["data_label"].unique().tolist() == ["Approved sample"]


def test_empty_csv_report_keeps_headers_and_report_context():
    empty_records = valid_records().iloc[0:0]
    report_bytes = generate_csv_report(
        empty_records,
        generated_at=FIXED_GENERATED_AT,
    )
    report = pd.read_csv(BytesIO(report_bytes))

    assert report.empty
    assert report.columns.tolist() == [
        "data_label",
        "report_generated_at",
        "report_servers",
        "report_start_date",
        "report_end_date",
        "date",
        "server_id",
        "total_capacity_gb",
        "used_storage_gb",
        "available_storage_gb",
        "usage_percentage",
    ]
    assert report.columns[0] == "data_label"


def test_pdf_report_is_a_complete_pdf_document():
    report = generate_pdf_report(valid_records(), generated_at=FIXED_GENERATED_AT)

    assert report.startswith(b"%PDF-")
    assert report.rstrip().endswith(b"%%EOF")
    assert len(report) > 1000


def test_pdf_report_handles_empty_filtered_results():
    report = generate_pdf_report(
        valid_records().iloc[0:0],
        generated_at=FIXED_GENERATED_AT,
    )

    assert report.startswith(b"%PDF-")
    assert report.rstrip().endswith(b"%%EOF")


@pytest.mark.parametrize(
    ("changes", "message"),
    [
        ({"date": "invalid"}, "invalid dates"),
        ({"server_id": ""}, "server_id cannot be empty"),
        ({"total_capacity_gb": 0}, "greater than zero"),
        ({"used_storage_gb": -1}, "cannot be negative"),
        ({"used_storage_gb": 101}, "cannot exceed total capacity"),
        ({"available_storage_gb": 59}, "must equal total capacity"),
        ({"usage_percentage": 46}, "does not match"),
        ({"usage_percentage": float("inf")}, "finite numeric values"),
    ],
)
def test_rejects_invalid_report_records(changes, message):
    records = valid_records().iloc[[0]].copy()
    for column, value in changes.items():
        records.loc[records.index[0], column] = value

    with pytest.raises(ValueError, match=message):
        generate_csv_report(records)


def test_rejects_missing_report_column():
    records = valid_records().drop(columns=["available_storage_gb"])

    with pytest.raises(ValueError, match="Missing required report columns"):
        generate_pdf_report(records)


@pytest.mark.parametrize("data_label", ["", "  ", None])
def test_rejects_empty_or_non_string_data_label(data_label):
    with pytest.raises(ValueError, match="data_label must be a non-empty string"):
        generate_csv_report(valid_records(), data_label=data_label)


def test_rejects_non_datetime_generation_time():
    with pytest.raises(TypeError, match="generated_at must be a datetime or None"):
        generate_pdf_report(valid_records(), generated_at="2024-02-01")
