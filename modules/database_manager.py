"""[Phase 2] Initialize SQLite tables and persist validated storage records."""

import math
import sqlite3
from contextlib import contextmanager
from datetime import date, datetime
from pathlib import Path
from typing import Generator

import pandas as pd


REQUIRED_COLUMNS = {
    "date",
    "server_id",
    "total_capacity_gb",
    "used_storage_gb",
    "available_storage_gb",
    "usage_percentage",
}
NUMERIC_COLUMNS = (
    "total_capacity_gb",
    "used_storage_gb",
    "available_storage_gb",
    "usage_percentage",
)
RESULT_COLUMNS = [
    "date",
    "server_id",
    "total_capacity_gb",
    "used_storage_gb",
    "available_storage_gb",
    "usage_percentage",
]
ARITHMETIC_TOLERANCE_GB = 0.02
PERCENTAGE_TOLERANCE = 0.02


def _database_path(db_path: str | Path | None) -> Path:
    if db_path is not None:
        return Path(db_path)
    return Path(__file__).resolve().parents[1] / "database" / "storage.db"


def _connect(db_path: str | Path | None) -> sqlite3.Connection:
    path = _database_path(db_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(path)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    return connection


@contextmanager
def _connection(db_path: str | Path | None) -> Generator[sqlite3.Connection, None, None]:
    connection = _connect(db_path)
    try:
        with connection:
            yield connection
    finally:
        connection.close()


def initialize_database(db_path: str | Path | None = None) -> Path:
    """Create the local database and its server, history, and alert tables."""
    path = _database_path(db_path)
    with _connection(path) as connection:
        connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS servers (
                server_id TEXT PRIMARY KEY,
                total_capacity_gb REAL NOT NULL
                    CHECK (total_capacity_gb > 0),
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS storage_records (
                id INTEGER PRIMARY KEY,
                server_id TEXT NOT NULL,
                record_date TEXT NOT NULL,
                used_storage_gb REAL NOT NULL CHECK (used_storage_gb >= 0),
                available_storage_gb REAL NOT NULL
                    CHECK (available_storage_gb >= 0),
                usage_percentage REAL NOT NULL
                    CHECK (usage_percentage BETWEEN 0 AND 100),
                FOREIGN KEY (server_id) REFERENCES servers (server_id),
                UNIQUE (server_id, record_date)
            );

            CREATE INDEX IF NOT EXISTS idx_storage_records_date
                ON storage_records (record_date);

            CREATE TABLE IF NOT EXISTS alerts (
                id INTEGER PRIMARY KEY,
                server_id TEXT NOT NULL,
                alert_date TEXT NOT NULL,
                usage_percentage REAL NOT NULL
                    CHECK (usage_percentage BETWEEN 0 AND 100),
                severity TEXT NOT NULL,
                message TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'Open',
                FOREIGN KEY (server_id) REFERENCES servers (server_id)
            );
            """
        )
    return path


def _prepare_records(records: pd.DataFrame) -> list[dict[str, object]]:
    if not isinstance(records, pd.DataFrame):
        raise TypeError("Storage records must be provided as a pandas DataFrame.")

    missing = REQUIRED_COLUMNS - set(records.columns)
    if missing:
        raise ValueError(f"Missing required columns: {', '.join(sorted(missing))}")

    frame = records[RESULT_COLUMNS].copy()
    parsed_dates = pd.to_datetime(frame["date"], errors="coerce")
    if parsed_dates.isna().any():
        raise ValueError("Storage records contain invalid dates.")
    frame["date"] = parsed_dates.dt.strftime("%Y-%m-%d")

    server_ids = frame["server_id"].astype("string").str.strip()
    if server_ids.isna().any() or server_ids.eq("").any():
        raise ValueError("server_id cannot be empty.")
    frame["server_id"] = server_ids

    for column in NUMERIC_COLUMNS:
        frame[column] = pd.to_numeric(frame[column], errors="coerce")
    if frame[list(NUMERIC_COLUMNS)].isna().any().any():
        raise ValueError("Storage records contain missing or non-numeric values.")
    if not all(
        math.isfinite(float(value))
        for value in frame[list(NUMERIC_COLUMNS)].to_numpy().ravel()
    ):
        raise ValueError("Storage records must contain finite numeric values.")

    if (frame["total_capacity_gb"] <= 0).any():
        raise ValueError("total_capacity_gb must be greater than zero.")
    if (frame[["used_storage_gb", "available_storage_gb"]] < 0).any().any():
        raise ValueError("Used and available storage cannot be negative.")
    if (frame["used_storage_gb"] > frame["total_capacity_gb"]).any():
        raise ValueError("Used storage cannot exceed total capacity.")
    if ((frame["usage_percentage"] < 0) | (frame["usage_percentage"] > 100)).any():
        raise ValueError("usage_percentage must be between 0 and 100.")

    capacity_error = (
        frame["used_storage_gb"]
        + frame["available_storage_gb"]
        - frame["total_capacity_gb"]
    ).abs()
    if (capacity_error > ARITHMETIC_TOLERANCE_GB).any():
        raise ValueError(
            "Used storage plus available storage must equal total capacity "
            "within 0.02 GB."
        )

    expected_usage = frame["used_storage_gb"] / frame["total_capacity_gb"] * 100
    if ((frame["usage_percentage"] - expected_usage).abs() > PERCENTAGE_TOLERANCE).any():
        raise ValueError(
            "usage_percentage must match used storage divided by total capacity "
            "within 0.02 percentage points."
        )

    if frame.duplicated(subset=["server_id", "date"]).any():
        raise ValueError("Duplicate date/server_id observations were found.")

    return frame.to_dict(orient="records")


def import_storage_records(
    records: pd.DataFrame,
    db_path: str | Path | None = None,
) -> int:
    """Insert valid records; skip exact repeats and reject conflicting history.

    Returns the number of new storage observations inserted. Existing records
    are never silently overwritten.
    """
    prepared_records = _prepare_records(records)
    initialize_database(db_path)
    inserted_count = 0

    with _connection(db_path) as connection:
        for record in prepared_records:
            server_id = str(record["server_id"])
            capacity = float(record["total_capacity_gb"])
            server = connection.execute(
                "SELECT total_capacity_gb FROM servers WHERE server_id = ?",
                (server_id,),
            ).fetchone()

            if server is None:
                connection.execute(
                    "INSERT INTO servers (server_id, total_capacity_gb) VALUES (?, ?)",
                    (server_id, capacity),
                )
            elif not math.isclose(
                float(server["total_capacity_gb"]),
                capacity,
                rel_tol=0.0,
                abs_tol=ARITHMETIC_TOLERANCE_GB,
            ):
                raise ValueError(
                    f"Capacity for {server_id} differs from its stored server "
                    "capacity; existing data was not changed."
                )

            stored = connection.execute(
                """
                SELECT used_storage_gb, available_storage_gb, usage_percentage
                FROM storage_records
                WHERE server_id = ? AND record_date = ?
                """,
                (server_id, str(record["date"])),
            ).fetchone()

            values = (
                float(record["used_storage_gb"]),
                float(record["available_storage_gb"]),
                float(record["usage_percentage"]),
            )
            if stored is not None:
                if not all(
                    math.isclose(float(stored[column]), value, rel_tol=0.0, abs_tol=1e-6)
                    for column, value in zip(
                        (
                            "used_storage_gb",
                            "available_storage_gb",
                            "usage_percentage",
                        ),
                        values,
                    )
                ):
                    raise ValueError(
                        f"Conflicting record already exists for {server_id} "
                        f"on {record['date']}; existing data was not changed."
                    )
                continue

            connection.execute(
                """
                INSERT INTO storage_records (
                    server_id,
                    record_date,
                    used_storage_gb,
                    available_storage_gb,
                    usage_percentage
                )
                VALUES (?, ?, ?, ?, ?)
                """,
                (server_id, str(record["date"]), *values),
            )
            inserted_count += 1

    return inserted_count


def _normalize_date(value: date | datetime | str | None, label: str) -> str | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.date().isoformat()
    if isinstance(value, date):
        return value.isoformat()
    if isinstance(value, str):
        try:
            parsed = date.fromisoformat(value)
        except ValueError as exc:
            raise ValueError(f"{label} must use ISO format YYYY-MM-DD.") from exc
        if parsed.isoformat() != value:
            raise ValueError(f"{label} must use ISO format YYYY-MM-DD.")
        return parsed.isoformat()
    raise TypeError(f"{label} must be a date, datetime, ISO date string, or None.")


def get_storage_records(
    server_id: str | None = None,
    start_date: date | datetime | str | None = None,
    end_date: date | datetime | str | None = None,
    db_path: str | Path | None = None,
) -> pd.DataFrame:
    """Return records ordered by date, optionally filtered by server and dates."""
    start = _normalize_date(start_date, "start_date")
    end = _normalize_date(end_date, "end_date")
    if start is not None and end is not None and start > end:
        raise ValueError("start_date must be on or before end_date.")
    if server_id is not None and not server_id.strip():
        raise ValueError("server_id cannot be empty.")

    initialize_database(db_path)
    conditions = []
    parameters: list[str] = []
    if server_id is not None:
        conditions.append("records.server_id = ?")
        parameters.append(server_id)
    if start is not None:
        conditions.append("records.record_date >= ?")
        parameters.append(start)
    if end is not None:
        conditions.append("records.record_date <= ?")
        parameters.append(end)
    where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""

    query = f"""
        SELECT
            records.record_date AS date,
            records.server_id,
            servers.total_capacity_gb,
            records.used_storage_gb,
            records.available_storage_gb,
            records.usage_percentage
        FROM storage_records AS records
        JOIN servers ON servers.server_id = records.server_id
        {where_clause}
        ORDER BY records.record_date, records.server_id
    """
    with _connection(db_path) as connection:
        rows = connection.execute(query, parameters).fetchall()
    return pd.DataFrame([dict(row) for row in rows], columns=RESULT_COLUMNS)


def get_servers(db_path: str | Path | None = None) -> pd.DataFrame:
    """Return known servers and their configured total capacities."""
    initialize_database(db_path)
    with _connection(db_path) as connection:
        rows = connection.execute(
            """
            SELECT server_id, total_capacity_gb, created_at
            FROM servers
            ORDER BY server_id
            """
        ).fetchall()
    return pd.DataFrame(
        [dict(row) for row in rows],
        columns=["server_id", "total_capacity_gb", "created_at"],
    )
