"""[Phase 3] Fit per-server Linear Regression models and produce forecasts."""

from dataclasses import dataclass
from datetime import timedelta
import math

import numpy as np
import pandas as pd
from sklearn.linear_model import LinearRegression


MIN_OBSERVATIONS = 2
MAX_FORECAST_DAYS = 90
REQUIRED_COLUMNS = {
    "date",
    "server_id",
    "total_capacity_gb",
    "used_storage_gb",
}


@dataclass(frozen=True)
class ForecastResult:
    """Forecast points, model growth rate, and threshold-date assessment."""

    server_id: str
    forecast: pd.DataFrame
    slope_gb_per_day: float
    forecast_horizon_days: int
    threshold_percentage: float
    threshold_date: pd.Timestamp | None
    threshold_estimate_message: str


def _finite_number(value: object, label: str) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{label} must be numeric.") from exc
    if not math.isfinite(number):
        raise ValueError(f"{label} must be a finite number.")
    return number


def predict_server_usage(
    records: pd.DataFrame,
    forecast_days: int = 30,
    threshold_percentage: float = 100.0,
) -> ForecastResult:
    """Forecast used storage for one server with elapsed days as the feature.

    Forecasts are estimates from historical Linear Regression trends. The
    horizon is limited to 90 days. The result contains only future predictions;
    observed records remain separate in the input DataFrame.
    """
    if not isinstance(records, pd.DataFrame):
        raise TypeError("Storage records must be provided as a pandas DataFrame.")
    missing = REQUIRED_COLUMNS - set(records.columns)
    if missing:
        raise ValueError(f"Missing required columns: {', '.join(sorted(missing))}")
    if isinstance(forecast_days, bool) or not isinstance(forecast_days, int):
        raise ValueError("forecast_days must be an integer from 1 to 90.")
    if not 1 <= forecast_days <= MAX_FORECAST_DAYS:
        raise ValueError("forecast_days must be between 1 and 90.")

    target_percentage = _finite_number(threshold_percentage, "threshold_percentage")
    if not 0 < target_percentage <= 100:
        raise ValueError("threshold_percentage must be greater than 0 and at most 100.")

    frame = records[list(REQUIRED_COLUMNS)].copy()
    parsed_dates = pd.to_datetime(frame["date"], errors="coerce")
    if parsed_dates.isna().any():
        raise ValueError("Storage records contain invalid dates.")
    frame["date"] = parsed_dates.dt.normalize()

    server_ids = frame["server_id"].astype("string").str.strip()
    if server_ids.isna().any() or server_ids.eq("").any():
        raise ValueError("server_id cannot be empty.")
    if server_ids.nunique() != 1:
        raise ValueError("Provide observations for exactly one server.")
    frame["server_id"] = server_ids

    for column in ("total_capacity_gb", "used_storage_gb"):
        frame[column] = pd.to_numeric(frame[column], errors="coerce")
    numeric_values = frame[["total_capacity_gb", "used_storage_gb"]].to_numpy(
        dtype=float
    )
    if not np.isfinite(numeric_values).all():
        raise ValueError("Storage records must contain finite numeric values.")
    if (frame["total_capacity_gb"] <= 0).any():
        raise ValueError("total_capacity_gb must be greater than zero.")
    if (frame["used_storage_gb"] < 0).any():
        raise ValueError("used_storage_gb cannot be negative.")
    if (frame["used_storage_gb"] > frame["total_capacity_gb"]).any():
        raise ValueError("used_storage_gb cannot exceed total_capacity_gb.")
    if frame["total_capacity_gb"].nunique() != 1:
        raise ValueError("A server's total capacity must be consistent across records.")
    if frame["date"].duplicated().any():
        raise ValueError("Duplicate observations for the same date were found.")

    frame = frame.sort_values("date").reset_index(drop=True)
    if len(frame) < MIN_OBSERVATIONS:
        raise ValueError("At least two observations are required to fit a trend.")

    first_date = frame["date"].iloc[0]
    elapsed_days = (frame["date"] - first_date).dt.days.to_numpy(dtype=float)
    if np.unique(elapsed_days).size < MIN_OBSERVATIONS:
        raise ValueError("Observations must span at least two distinct dates.")

    used_values = frame["used_storage_gb"].to_numpy(dtype=float)
    model = LinearRegression()
    model.fit(elapsed_days.reshape(-1, 1), used_values)
    slope = float(model.coef_[0])

    last_date = frame["date"].iloc[-1]
    future_days = np.arange(
        int(elapsed_days[-1]) + 1,
        int(elapsed_days[-1]) + forecast_days + 1,
        dtype=float,
    )
    predicted_values = model.predict(future_days.reshape(-1, 1))
    forecast = pd.DataFrame(
        {
            "date": [last_date + timedelta(days=index) for index in range(1, forecast_days + 1)],
            "days_ahead": range(1, forecast_days + 1),
            "predicted_used_storage_gb": predicted_values,
        }
    )

    capacity = float(frame["total_capacity_gb"].iloc[0])
    latest_used = float(frame["used_storage_gb"].iloc[-1])
    target_used = capacity * target_percentage / 100.0
    threshold_date = None

    if latest_used >= capacity:
        estimate_message = (
            "Capacity is already reached; no future exhaustion date is estimated."
        )
    elif latest_used >= target_used:
        estimate_message = (
            f"Current usage is already at or above the {target_percentage:g}% "
            "threshold; no future crossing date is estimated."
        )
    elif slope <= 0:
        estimate_message = (
            "The fitted trend is flat or decreasing; a future threshold date "
            "cannot be estimated reliably."
        )
    else:
        model_at_latest = float(model.predict(np.array([[elapsed_days[-1]]]))[0])
        days_to_threshold = (target_used - model_at_latest) / slope
        if days_to_threshold <= 0:
            estimate_message = (
                "The fitted trend implies the threshold was reached by the latest "
                "observation; no future crossing date is estimated."
            )
        elif days_to_threshold > forecast_days:
            estimate_message = (
                f"The estimated crossing is beyond the {forecast_days}-day "
                "forecast horizon; no date is shown."
            )
        else:
            threshold_date = last_date + timedelta(days=math.ceil(days_to_threshold))
            estimate_message = (
                f"Estimated {target_percentage:g}% threshold crossing based on "
                "the fitted historical trend; this is not a guarantee."
            )

    return ForecastResult(
        server_id=str(frame["server_id"].iloc[0]),
        forecast=forecast,
        slope_gb_per_day=slope,
        forecast_horizon_days=forecast_days,
        threshold_percentage=target_percentage,
        threshold_date=threshold_date,
        threshold_estimate_message=estimate_message,
    )
