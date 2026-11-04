"""[Phase 6] Integration tests for deterministic synthetic dataset generation."""

import numpy as np
import pandas as pd
import pytest

from modules.data_generator import generate_dataset, save_dataset
from modules.data_loader import load_and_validate_csv


def test_generates_reproducible_270_row_three_server_dataset():
    first = generate_dataset(days=90, seed=7)
    second = generate_dataset(days=90, seed=7)

    pd.testing.assert_frame_equal(first, second)
    assert len(first) == 270
    assert first["server_id"].nunique() == 3
    assert first.groupby("server_id").size().eq(90).all()


def test_generated_dataset_obeys_capacity_and_utilization_constraints():
    records = generate_dataset(days=90)

    assert (records["total_capacity_gb"] > 0).all()
    assert (records["used_storage_gb"] >= 0).all()
    assert (records["used_storage_gb"] <= records["total_capacity_gb"]).all()
    assert (records["available_storage_gb"] >= 0).all()
    assert np.allclose(
        records["used_storage_gb"] + records["available_storage_gb"],
        records["total_capacity_gb"],
        atol=0.02,
    )
    assert np.allclose(
        records["used_storage_gb"] / records["total_capacity_gb"] * 100,
        records["usage_percentage"],
        atol=0.02,
    )


@pytest.mark.parametrize("days", [0, 1, -1])
def test_requires_at_least_two_days(days):
    with pytest.raises(ValueError, match="at least 2"):
        generate_dataset(days=days)


def test_saved_generated_csv_passes_phase_one_validation(tmp_path):
    output_path = tmp_path / "generated.csv"
    records = generate_dataset(days=5, seed=123)

    saved_path = save_dataset(records, output_path)
    loaded_records = load_and_validate_csv(saved_path)

    assert saved_path == output_path
    assert len(loaded_records) == 15
    assert loaded_records.groupby("server_id").size().eq(5).all()
