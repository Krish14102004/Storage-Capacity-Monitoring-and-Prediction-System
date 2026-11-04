"""[Phase 3] Tests for Linear Regression forecasts and edge cases."""

import numpy as np
import pandas as pd
import pytest

from models.prediction_model import predict_server_usage


def records_for(used, dates=None, server_id="Server A", capacity=100.0):
    if dates is None:
        dates = pd.date_range("2024-01-01", periods=len(used), freq="D")
    return pd.DataFrame(
        {
            "date": dates,
            "server_id": server_id,
            "total_capacity_gb": capacity,
            "used_storage_gb": used,
        }
    )


def test_fits_linear_regression_and_returns_future_points_only():
    history = records_for([20, 22, 24, 26])

    result = predict_server_usage(history, forecast_days=3, threshold_percentage=32)

    assert result.server_id == "Server A"
    assert result.forecast_horizon_days == 3
    assert result.slope_gb_per_day == pytest.approx(2.0)
    assert result.forecast["days_ahead"].tolist() == [1, 2, 3]
    assert result.forecast["date"].tolist() == list(
        pd.date_range("2024-01-05", periods=3, freq="D")
    )
    assert result.forecast["predicted_used_storage_gb"].tolist() == pytest.approx(
        [28, 30, 32]
    )
    assert result.threshold_date == pd.Timestamp("2024-01-07")
    assert "not a guarantee" in result.threshold_estimate_message
    assert "predicted_used_storage_gb" not in history.columns


def test_sorts_observations_before_fitting_model():
    history = records_for(
        [24, 20, 26, 22],
        dates=pd.to_datetime(
            ["2024-01-03", "2024-01-01", "2024-01-04", "2024-01-02"]
        ),
    )

    result = predict_server_usage(history, forecast_days=1)

    assert result.slope_gb_per_day == pytest.approx(2.0)
    assert result.forecast.iloc[0]["predicted_used_storage_gb"] == pytest.approx(28)
    assert result.forecast.iloc[0]["date"] == pd.Timestamp("2024-01-05")


def test_flat_or_decreasing_trend_does_not_estimate_crossing_date():
    for history in (records_for([50, 50, 50]), records_for([60, 55, 50])):
        result = predict_server_usage(history, forecast_days=2)

        assert result.threshold_date is None
        assert "flat or decreasing" in result.threshold_estimate_message


def test_already_reached_capacity_does_not_estimate_exhaustion():
    history = records_for([80, 90, 100])

    result = predict_server_usage(history, forecast_days=2)

    assert result.threshold_date is None
    assert "Capacity is already reached" in result.threshold_estimate_message


def test_already_reached_custom_threshold_does_not_predict_future_crossing():
    history = records_for([60, 70, 80])

    result = predict_server_usage(
        history,
        forecast_days=2,
        threshold_percentage=75,
    )

    assert result.threshold_date is None
    assert "already at or above the 75% threshold" in result.threshold_estimate_message


def test_crossing_beyond_forecast_limit_is_not_reported():
    history = records_for([10, 10.1])

    result = predict_server_usage(history, forecast_days=30)

    assert result.threshold_date is None
    assert "beyond the 30-day forecast horizon" in result.threshold_estimate_message


def test_threshold_estimate_does_not_exceed_selected_forecast_horizon():
    history = records_for([70, 71])

    result = predict_server_usage(
        history,
        forecast_days=10,
        threshold_percentage=85,
    )

    assert result.threshold_date is None
    assert "beyond the 10-day forecast horizon" in result.threshold_estimate_message


@pytest.mark.parametrize(
    ("history", "forecast_days", "threshold_percentage", "message"),
    [
        (records_for([50]), 1, 100, "At least two observations"),
        (records_for([50, 55]), 0, 100, "between 1 and 90"),
        (records_for([50, 55]), 91, 100, "between 1 and 90"),
        (records_for([50, 55]), True, 100, "must be an integer"),
        (records_for([50, 55]), 1, 0, "greater than 0"),
        (records_for([50, 55]), 1, 101, "at most 100"),
        (
            pd.concat([records_for([50, 55]), records_for([60, 65], server_id="B")]),
            1,
            100,
            "exactly one server",
        ),
        (
            records_for([50, 55], dates=pd.to_datetime(["2024-01-01", "2024-01-01"])),
            1,
            100,
            "Duplicate observations",
        ),
        (records_for([50, 55], capacity=100).assign(total_capacity_gb=[100, 200]), 1, 100, "consistent"),
    ],
)
def test_rejects_invalid_forecast_inputs(
    history,
    forecast_days,
    threshold_percentage,
    message,
):
    with pytest.raises(ValueError, match=message):
        predict_server_usage(history, forecast_days, threshold_percentage)


def test_rejects_non_finite_observations():
    history = records_for([50, np.inf])

    with pytest.raises(ValueError, match="finite numeric values"):
        predict_server_usage(history)


@pytest.mark.parametrize("used", [-1, 101])
def test_rejects_used_storage_outside_capacity(used):
    history = records_for([50, used])

    with pytest.raises(ValueError, match="cannot be negative|cannot exceed"):
        predict_server_usage(history)
