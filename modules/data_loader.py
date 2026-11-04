"""[Phase 1] Load CSV input and validate schema, types, ranges, and duplicate records."""

from pathlib import Path

import numpy as np
import pandas as pd


REQUIRED_COLUMNS = {
    "date",
    "server_id",
    "total_capacity_gb",
    "used_storage_gb",
    "available_storage_gb",
    "usage_percentage",
}


def load_and_validate_csv(path: str | Path) -> pd.DataFrame:
    """Load a storage CSV and raise ValueError with a useful message if invalid."""
    csv_path = Path(path)
    if not csv_path.exists():
        raise FileNotFoundError(f"Dataset file was not found: {csv_path}")

    try:
        df = pd.read_csv(csv_path)
    except (
        pd.errors.EmptyDataError,
        pd.errors.ParserError,
        UnicodeDecodeError,
    ) as exc:
        raise ValueError(f"Could not parse the CSV file: {exc}") from exc

    missing = REQUIRED_COLUMNS - set(df.columns)
    if missing:
        raise ValueError(f"Missing required columns: {', '.join(sorted(missing))}")

    df = df[list(sorted(REQUIRED_COLUMNS))].copy()
    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    if df["date"].isna().any():
        raise ValueError("One or more date values are invalid.")

    numeric_columns = [
        "total_capacity_gb",
        "used_storage_gb",
        "available_storage_gb",
        "usage_percentage",
    ]
    for column in numeric_columns:
        df[column] = pd.to_numeric(df[column], errors="coerce")

    if df[numeric_columns].isna().any().any():
        raise ValueError("Numeric storage columns contain missing or non-numeric values.")

    if not np.isfinite(df[numeric_columns].to_numpy(dtype=float)).all():
        raise ValueError("Numeric storage columns must contain finite values.")

    if df["server_id"].isna().any() or (df["server_id"].astype(str).str.strip() == "").any():
        raise ValueError("server_id cannot be empty.")

    if (df["total_capacity_gb"] <= 0).any():
        raise ValueError("total_capacity_gb must be greater than zero.")

    if (df["used_storage_gb"] < 0).any() or (df["available_storage_gb"] < 0).any():
        raise ValueError("Used and available storage cannot be negative.")

    if (df["used_storage_gb"] > df["total_capacity_gb"]).any():
        raise ValueError("Used storage cannot exceed total capacity.")

    if ((df["usage_percentage"] < 0) | (df["usage_percentage"] > 100)).any():
        raise ValueError("usage_percentage must be between 0 and 100.")

    expected_usage = (
        df["used_storage_gb"] / df["total_capacity_gb"] * 100.0
    )
    if ((df["usage_percentage"] - expected_usage).abs() > 0.02).any():
        raise ValueError(
            "usage_percentage must match used storage divided by total capacity "
            "within 0.02 percentage points."
        )

    arithmetic_total = df["used_storage_gb"] + df["available_storage_gb"]
    if ((arithmetic_total - df["total_capacity_gb"]).abs() > 0.02).any():
        raise ValueError("Used storage plus available storage must equal total capacity.")

    if df.duplicated(subset=["date", "server_id"]).any():
        raise ValueError("Duplicate date/server_id observations were found.")

    return df.sort_values(["server_id", "date"]).reset_index(drop=True)
