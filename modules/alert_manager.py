"""[Phase 3] Classify utilization and evaluate current-state threshold alerts."""

from dataclasses import dataclass
import math

import pandas as pd


ALERT_COLUMNS = [
    "server_id",
    "date",
    "usage_percentage",
    "severity",
    "threshold_crossed",
    "message",
]


@dataclass(frozen=True)
class AlertThresholds:
    """Configurable utilization boundaries for warning, critical, and emergency."""

    warning: float = 70.0
    critical: float = 85.0
    emergency: float = 95.0

    def __post_init__(self) -> None:
        try:
            values = tuple(
                float(value) for value in (self.warning, self.critical, self.emergency)
            )
        except (TypeError, ValueError) as exc:
            raise ValueError("Alert thresholds must be numeric.") from exc
        if not all(math.isfinite(value) for value in values):
            raise ValueError("Alert thresholds must be finite numbers.")
        if not 0 <= values[0] < values[1] < values[2] <= 100:
            raise ValueError(
                "Thresholds must satisfy 0 <= warning < critical < emergency <= 100."
            )
        object.__setattr__(self, "warning", values[0])
        object.__setattr__(self, "critical", values[1])
        object.__setattr__(self, "emergency", values[2])


DEFAULT_THRESHOLDS = AlertThresholds()
REQUIRED_COLUMNS = {"date", "server_id", "usage_percentage"}


def _validated_percentage(value: object) -> float:
    try:
        percentage = float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError("usage_percentage must be numeric.") from exc
    if not math.isfinite(percentage) or not 0 <= percentage <= 100:
        raise ValueError("usage_percentage must be a finite value from 0 to 100.")
    return percentage


def classify_utilization(
    usage_percentage: float,
    thresholds: AlertThresholds = DEFAULT_THRESHOLDS,
) -> str:
    """Return Normal, Warning, Critical, or Emergency for one utilization value."""
    percentage = _validated_percentage(usage_percentage)
    if percentage >= thresholds.emergency:
        return "Emergency"
    if percentage >= thresholds.critical:
        return "Critical"
    if percentage >= thresholds.warning:
        return "Warning"
    return "Normal"


def generate_current_alerts(
    records: pd.DataFrame,
    thresholds: AlertThresholds = DEFAULT_THRESHOLDS,
) -> pd.DataFrame:
    """Return non-normal alerts for each server's latest observation.

    This is a current-state evaluation, not persisted event generation. Calling
    it repeatedly with the same records produces the same rows and no duplicate
    alert records are written to the database.
    """
    if not isinstance(records, pd.DataFrame):
        raise TypeError("Storage records must be provided as a pandas DataFrame.")
    missing = REQUIRED_COLUMNS - set(records.columns)
    if missing:
        raise ValueError(f"Missing required columns: {', '.join(sorted(missing))}")
    if records.empty:
        return pd.DataFrame(columns=ALERT_COLUMNS)

    frame = records[["date", "server_id", "usage_percentage"]].copy()
    parsed_dates = pd.to_datetime(frame["date"], errors="coerce")
    if parsed_dates.isna().any():
        raise ValueError("Storage records contain invalid dates.")
    frame["date"] = parsed_dates.dt.normalize()

    server_ids = frame["server_id"].astype("string").str.strip()
    if server_ids.isna().any() or server_ids.eq("").any():
        raise ValueError("server_id cannot be empty.")
    frame["server_id"] = server_ids
    frame["usage_percentage"] = frame["usage_percentage"].map(_validated_percentage)

    if frame.duplicated(subset=["server_id", "date"]).any():
        raise ValueError("Duplicate observations for the same server and date were found.")

    current_records = (
        frame.sort_values(["date", "server_id"])
        .groupby("server_id", as_index=False, sort=True)
        .tail(1)
        .sort_values("server_id")
    )
    alerts = []
    for record in current_records.itertuples(index=False):
        severity = classify_utilization(record.usage_percentage, thresholds)
        if severity == "Normal":
            continue
        threshold = getattr(thresholds, severity.lower())
        alerts.append(
            {
                "server_id": str(record.server_id),
                "date": record.date.strftime("%Y-%m-%d"),
                "usage_percentage": float(record.usage_percentage),
                "severity": severity,
                "threshold_crossed": float(threshold),
                "message": (
                    f"{record.server_id} is at {record.usage_percentage:.2f}% "
                    f"utilization ({severity}; threshold {threshold:g}%)."
                ),
            }
        )

    return pd.DataFrame(alerts, columns=ALERT_COLUMNS)
