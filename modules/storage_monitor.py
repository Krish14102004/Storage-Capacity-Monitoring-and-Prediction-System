"""[Phase 2] Calculate storage capacity and utilization metrics."""

import math
from typing import TypedDict


class StorageMetrics(TypedDict):
    """Calculated storage amounts and utilization percentage."""

    total_capacity_gb: float
    used_storage_gb: float
    available_storage_gb: float
    usage_percentage: float


def calculate_storage_metrics(
    total_capacity_gb: float,
    used_storage_gb: float,
) -> StorageMetrics:
    """Calculate available capacity and utilization after validating inputs."""
    try:
        total_capacity = float(total_capacity_gb)
        used_storage = float(used_storage_gb)
    except (TypeError, ValueError) as exc:
        raise ValueError("Capacity values must be numeric.") from exc

    if not math.isfinite(total_capacity) or not math.isfinite(used_storage):
        raise ValueError("Capacity values must be finite numbers.")
    if total_capacity <= 0:
        raise ValueError("Total capacity must be greater than zero.")
    if used_storage < 0:
        raise ValueError("Used storage cannot be negative.")
    if used_storage > total_capacity:
        raise ValueError("Used storage cannot exceed total capacity.")

    available_storage = total_capacity - used_storage
    usage_percentage = used_storage / total_capacity * 100.0
    return {
        "total_capacity_gb": total_capacity,
        "used_storage_gb": used_storage,
        "available_storage_gb": available_storage,
        "usage_percentage": usage_percentage,
    }
