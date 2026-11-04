"""[Phase 2] Tests for storage calculations and input validation."""

import math

import pytest

from modules.storage_monitor import calculate_storage_metrics


def test_calculates_capacity_and_utilization():
    metrics = calculate_storage_metrics(1000, 425)

    assert metrics == {
        "total_capacity_gb": 1000.0,
        "used_storage_gb": 425.0,
        "available_storage_gb": 575.0,
        "usage_percentage": 42.5,
    }


@pytest.mark.parametrize(
    ("total_capacity", "used_storage", "message"),
    [
        (0, 0, "greater than zero"),
        (-10, 0, "greater than zero"),
        (100, -1, "cannot be negative"),
        (100, 101, "cannot exceed total capacity"),
        (math.inf, 1, "finite numbers"),
        (100, math.nan, "finite numbers"),
        ("invalid", 1, "must be numeric"),
    ],
)
def test_rejects_invalid_capacity_values(total_capacity, used_storage, message):
    with pytest.raises(ValueError, match=message):
        calculate_storage_metrics(total_capacity, used_storage)
