"""[Phase 1] Tests for CSV schema and input validation."""

import pandas as pd
import pytest

from modules.data_loader import REQUIRED_COLUMNS, load_and_validate_csv


VALID_RECORD = {
    "date": "2024-01-01",
    "server_id": "Server A",
    "total_capacity_gb": 100.0,
    "used_storage_gb": 40.0,
    "available_storage_gb": 60.0,
    "usage_percentage": 40.0,
}


def write_csv(tmp_path, records, name="storage.csv"):
    """Write test records to a temporary CSV file."""
    path = tmp_path / name
    pd.DataFrame(records).to_csv(path, index=False)
    return path


def test_loads_valid_records_in_server_and_date_order(tmp_path):
    later_record = {**VALID_RECORD, "date": "2024-01-02"}
    other_server_record = {**VALID_RECORD, "server_id": "Server B"}
    path = write_csv(tmp_path, [later_record, other_server_record, VALID_RECORD])

    result = load_and_validate_csv(path)

    assert len(result) == 3
    assert list(result.columns) == sorted(REQUIRED_COLUMNS)
    assert list(zip(result["server_id"], result["date"])) == [
        ("Server A", pd.Timestamp("2024-01-01")),
        ("Server A", pd.Timestamp("2024-01-02")),
        ("Server B", pd.Timestamp("2024-01-01")),
    ]


def test_rejects_missing_required_column(tmp_path):
    record = {key: value for key, value in VALID_RECORD.items() if key != "server_id"}
    path = write_csv(tmp_path, [record])

    with pytest.raises(ValueError, match="Missing required columns: server_id"):
        load_and_validate_csv(path)


@pytest.mark.parametrize(
    ("changes", "message"),
    [
        ({"date": "not-a-date"}, "date values are invalid"),
        ({"server_id": ""}, "server_id cannot be empty"),
        ({"server_id": None}, "server_id cannot be empty"),
        ({"total_capacity_gb": 0}, "total_capacity_gb must be greater than zero"),
        ({"used_storage_gb": -1}, "storage cannot be negative"),
        ({"available_storage_gb": -1}, "storage cannot be negative"),
        ({"used_storage_gb": 101}, "Used storage cannot exceed total capacity"),
        ({"usage_percentage": 101}, "usage_percentage must be between 0 and 100"),
        ({"used_storage_gb": "invalid"}, "missing or non-numeric values"),
        ({"used_storage_gb": float("inf")}, "must contain finite values"),
        ({"available_storage_gb": 59}, "must equal total capacity"),
        (
            {"usage_percentage": 41},
            "must match used storage divided by total capacity",
        ),
    ],
)
def test_rejects_invalid_records(tmp_path, changes, message):
    record = {**VALID_RECORD, **changes}
    path = write_csv(tmp_path, [record])

    with pytest.raises(ValueError, match=message):
        load_and_validate_csv(path)


def test_rejects_duplicate_server_date_observations(tmp_path):
    path = write_csv(tmp_path, [VALID_RECORD, VALID_RECORD])

    with pytest.raises(ValueError, match="Duplicate date/server_id"):
        load_and_validate_csv(path)


def test_rejects_empty_csv(tmp_path):
    path = tmp_path / "empty.csv"
    path.write_text("", encoding="utf-8")

    with pytest.raises(ValueError, match="Could not parse the CSV file"):
        load_and_validate_csv(path)


def test_reports_missing_csv(tmp_path):
    with pytest.raises(FileNotFoundError, match="Dataset file was not found"):
        load_and_validate_csv(tmp_path / "missing.csv")
