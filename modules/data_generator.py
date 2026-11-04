"""[Phase 1] Generate deterministic synthetic storage records and save data/storage_data.csv."""

from datetime import date, timedelta
from pathlib import Path

import numpy as np
import pandas as pd


SERVERS = [
    {
        "server_id": "Server A",
        "total_capacity_gb": 1000.0,
        "initial_used_gb": 420.0,
        "daily_growth_gb": 4.5,
    },
    {
        "server_id": "Server B",
        "total_capacity_gb": 2000.0,
        "initial_used_gb": 1100.0,
        "daily_growth_gb": 8.0,
    },
    {
        "server_id": "Server C",
        "total_capacity_gb": 500.0,
        "initial_used_gb": 250.0,
        "daily_growth_gb": 2.5,
    },
]


def generate_dataset(days: int = 90, seed: int = 42) -> pd.DataFrame:
    """Generate `days` observations per server using reproducible simulated growth."""
    if days < 2:
        raise ValueError("days must be at least 2 to support trend analysis")

    rng = np.random.default_rng(seed)
    start_date = date.today() - timedelta(days=days - 1)
    records = []

    for server in SERVERS:
        used = server["initial_used_gb"]

        for day_index in range(days):
            if day_index > 0:
                noise = rng.normal(loc=0.0, scale=0.5)
                used += server["daily_growth_gb"] + noise

            used = min(used, server["total_capacity_gb"])
            available = max(server["total_capacity_gb"] - used, 0.0)
            utilization = (used / server["total_capacity_gb"]) * 100.0

            records.append(
                {
                    "date": (start_date + timedelta(days=day_index)).isoformat(),
                    "server_id": server["server_id"],
                    "total_capacity_gb": server["total_capacity_gb"],
                    "used_storage_gb": round(used, 2),
                    "available_storage_gb": round(available, 2),
                    "usage_percentage": round(utilization, 2),
                }
            )

    return pd.DataFrame(records)


def save_dataset(
    df: pd.DataFrame,
    output_path: Path | None = None,
) -> Path:
    """Save generated records to the project's data directory."""
    if output_path is None:
        output_path = Path(__file__).resolve().parents[1] / "data" / "storage_data.csv"

    output_path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(output_path, index=False)
    return output_path


if __name__ == "__main__":
    dataset = generate_dataset()
    saved_path = save_dataset(dataset)
    print("Synthetic dataset generated successfully.")
    print(f"Rows: {len(dataset)}")
    print(f"Servers: {dataset['server_id'].nunique()}")
    print(f"Rows per server:\n{dataset.groupby('server_id').size().to_string()}")
    print(f"Saved to: {saved_path}")
