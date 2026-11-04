"""[Phase 3] Tests for alert thresholds, validation, and current-state output."""

import pandas as pd
import pytest

from modules.alert_manager import (
    ALERT_COLUMNS,
    AlertThresholds,
    classify_utilization,
    generate_current_alerts,
)


@pytest.mark.parametrize(
    ("percentage", "expected"),
    [
        (0, "Normal"),
        (69.99, "Normal"),
        (70, "Warning"),
        (84.99, "Warning"),
        (85, "Critical"),
        (94.99, "Critical"),
        (95, "Emergency"),
        (100, "Emergency"),
    ],
)
def test_classifies_default_threshold_boundaries(percentage, expected):
    assert classify_utilization(percentage) == expected


def test_supports_validated_custom_thresholds():
    thresholds = AlertThresholds(warning=60, critical=80, emergency=90)

    assert classify_utilization(60, thresholds) == "Warning"
    assert classify_utilization(80, thresholds) == "Critical"
    assert classify_utilization(90, thresholds) == "Emergency"


@pytest.mark.parametrize(
    "values",
    [
        (85, 85, 95),
        (90, 85, 95),
        (-1, 85, 95),
        (70, 85, 101),
        (70, float("nan"), 95),
        ("bad", 85, 95),
    ],
)
def test_rejects_invalid_threshold_sets(values):
    with pytest.raises(ValueError):
        AlertThresholds(*values)


@pytest.mark.parametrize("percentage", [-0.1, 100.1, float("inf"), float("nan"), "bad"])
def test_rejects_invalid_utilization_values(percentage):
    with pytest.raises(ValueError):
        classify_utilization(percentage)


def test_generates_alerts_for_each_servers_latest_non_normal_state():
    records = pd.DataFrame(
        [
            {"date": "2024-01-01", "server_id": "Server A", "usage_percentage": 69},
            {"date": "2024-01-02", "server_id": "Server A", "usage_percentage": 70},
            {"date": "2024-01-01", "server_id": "Server B", "usage_percentage": 90},
            {"date": "2024-01-02", "server_id": "Server B", "usage_percentage": 69},
            {"date": "2024-01-02", "server_id": "Server C", "usage_percentage": 96},
        ]
    )

    alerts = generate_current_alerts(records)

    assert alerts.columns.tolist() == ALERT_COLUMNS
    assert alerts["server_id"].tolist() == ["Server A", "Server C"]
    assert alerts["severity"].tolist() == ["Warning", "Emergency"]
    assert alerts["threshold_crossed"].tolist() == [70.0, 95.0]
    assert alerts["date"].tolist() == ["2024-01-02", "2024-01-02"]
    assert "Warning" in alerts.iloc[0]["message"]


def test_current_alert_evaluation_is_repeatable_and_does_not_mutate_input():
    records = pd.DataFrame(
        [{"date": "2024-01-01", "server_id": "Server A", "usage_percentage": 85}]
    )
    original = records.copy(deep=True)

    first = generate_current_alerts(records)
    second = generate_current_alerts(records)

    pd.testing.assert_frame_equal(first, second)
    pd.testing.assert_frame_equal(records, original)


def test_returns_typed_empty_result_for_empty_input():
    records = pd.DataFrame(columns=["date", "server_id", "usage_percentage"])

    alerts = generate_current_alerts(records)

    assert alerts.empty
    assert alerts.columns.tolist() == ALERT_COLUMNS


@pytest.mark.parametrize(
    ("records", "message"),
    [
        (
            pd.DataFrame([{"date": "2024-01-01", "server_id": "A"}]),
            "Missing required columns",
        ),
        (
            pd.DataFrame(
                [
                    {"date": "bad-date", "server_id": "A", "usage_percentage": 80}
                ]
            ),
            "invalid dates",
        ),
        (
            pd.DataFrame(
                [{"date": "2024-01-01", "server_id": "", "usage_percentage": 80}]
            ),
            "server_id cannot be empty",
        ),
        (
            pd.DataFrame(
                [
                    {"date": "2024-01-01", "server_id": "A", "usage_percentage": 80},
                    {"date": "2024-01-01", "server_id": "A", "usage_percentage": 85},
                ]
            ),
            "Duplicate observations",
        ),
    ],
)
def test_rejects_invalid_current_records(records, message):
    with pytest.raises(ValueError, match=message):
        generate_current_alerts(records)
