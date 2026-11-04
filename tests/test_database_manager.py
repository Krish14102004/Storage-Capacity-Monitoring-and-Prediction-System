"""[Phase 2] Tests for SQLite setup, import safety, and filtered reads."""

import sqlite3

import pandas as pd
import pytest

from modules.database_manager import (
    get_servers,
    get_storage_records,
    import_storage_records,
    initialize_database,
)


def make_record(day, server_id="Server A", used=40.0, capacity=100.0):
    available = capacity - used
    return {
        "date": day,
        "server_id": server_id,
        "total_capacity_gb": capacity,
        "used_storage_gb": used,
        "available_storage_gb": available,
        "usage_percentage": used / capacity * 100,
    }


def make_records(*records):
    return pd.DataFrame(records)


def test_initializes_database_schema(tmp_path):
    db_path = tmp_path / "nested" / "storage.db"

    result = initialize_database(db_path)

    assert result == db_path
    with sqlite3.connect(db_path) as connection:
        tables = {
            row[0]
            for row in connection.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table'"
            )
        }
    assert {"servers", "storage_records", "alerts"} <= tables


def test_imports_idempotently_and_filters_records(tmp_path):
    db_path = tmp_path / "storage.db"
    records = make_records(
        make_record("2024-01-02"),
        make_record("2024-01-01"),
        make_record("2024-01-01", server_id="Server B", capacity=200.0),
    )

    assert import_storage_records(records, db_path) == 3
    assert import_storage_records(records, db_path) == 0

    filtered = get_storage_records(
        server_id="Server A",
        start_date="2024-01-02",
        end_date="2024-01-02",
        db_path=db_path,
    )
    assert len(filtered) == 1
    assert filtered.iloc[0]["date"] == "2024-01-02"
    assert filtered.iloc[0]["total_capacity_gb"] == 100.0
    assert get_servers(db_path)["server_id"].tolist() == ["Server A", "Server B"]


def test_does_not_overwrite_conflicting_observation(tmp_path):
    db_path = tmp_path / "storage.db"
    original = make_record("2024-01-01")
    conflicting = make_record("2024-01-01", used=45.0)
    import_storage_records(make_records(original), db_path)

    with pytest.raises(ValueError, match="Conflicting record already exists"):
        import_storage_records(make_records(conflicting), db_path)

    stored = get_storage_records(db_path=db_path)
    assert len(stored) == 1
    assert stored.iloc[0]["used_storage_gb"] == 40.0


def test_import_is_atomic_when_a_later_record_conflicts(tmp_path):
    db_path = tmp_path / "storage.db"
    original = make_record("2024-01-01")
    import_storage_records(make_records(original), db_path)
    new_record = make_record("2024-01-02")
    conflicting_record = make_record("2024-01-01", used=45.0)

    with pytest.raises(ValueError, match="Conflicting record already exists"):
        import_storage_records(
            make_records(new_record, conflicting_record),
            db_path,
        )

    stored = get_storage_records(db_path=db_path)
    assert stored["date"].tolist() == ["2024-01-01"]
    assert stored.iloc[0]["used_storage_gb"] == 40.0


@pytest.mark.parametrize(
    ("records", "message"),
    [
        (make_records(make_record("bad-date")), "invalid dates"),
        (
            make_records({**make_record("2024-01-01"), "usage_percentage": 50}),
            "must match used storage",
        ),
        (
            make_records(
                make_record("2024-01-01"),
                make_record("2024-01-01"),
            ),
            "Duplicate date/server_id",
        ),
        (
            pd.DataFrame([{"date": "2024-01-01"}]),
            "Missing required columns",
        ),
    ],
)
def test_rejects_invalid_import_records(tmp_path, records, message):
    with pytest.raises(ValueError, match=message):
        import_storage_records(records, tmp_path / "storage.db")


def test_rejects_invalid_date_filter_and_date_order(tmp_path):
    with pytest.raises(ValueError, match="ISO format YYYY-MM-DD"):
        get_storage_records(start_date="01/01/2024", db_path=tmp_path / "storage.db")
    with pytest.raises(ValueError, match="on or before"):
        get_storage_records(
            start_date="2024-02-01",
            end_date="2024-01-01",
            db_path=tmp_path / "storage.db",
        )


def test_empty_database_returns_empty_records_with_expected_columns(tmp_path):
    records = get_storage_records(db_path=tmp_path / "storage.db")

    assert records.empty
    assert records.columns.tolist() == [
        "date",
        "server_id",
        "total_capacity_gb",
        "used_storage_gb",
        "available_storage_gb",
        "usage_percentage",
    ]
