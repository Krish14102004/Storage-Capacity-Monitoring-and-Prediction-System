"""[Phase 6] Integration checks for the Streamlit dashboard workflow."""

from pathlib import Path

import pandas as pd
import pytest
from streamlit.testing.v1 import AppTest

import modules.database_manager as database_manager
from modules.dashboard_helpers import load_dashboard_records
from modules.database_manager import get_storage_records, import_storage_records


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DASHBOARD_SCRIPTS = [
    PROJECT_ROOT / "app.py",
    PROJECT_ROOT / "pages" / "1_Storage_Monitoring.py",
    PROJECT_ROOT / "pages" / "2_Capacity_Prediction.py",
    PROJECT_ROOT / "pages" / "3_Alerts.py",
    PROJECT_ROOT / "pages" / "4_Reports.py",
]


@pytest.fixture(autouse=True)
def temporary_dashboard_database(tmp_path, monkeypatch):
    """Route default dashboard database operations to a test-only location."""
    database_path = tmp_path / "dashboard.db"
    original_path_function = database_manager._database_path

    def use_temporary_database(path):
        if path is None:
            return database_path
        return original_path_function(path)

    monkeypatch.setattr(database_manager, "_database_path", use_temporary_database)
    return database_path


def test_first_dashboard_load_imports_validated_demo_data_once():
    first_load = load_dashboard_records()
    second_load = load_dashboard_records()
    stored_records = get_storage_records()

    assert database_manager._database_path(None).exists()
    assert len(first_load) == len(second_load) == len(stored_records) == 270
    assert first_load["server_id"].nunique() == 3
    assert first_load.groupby("server_id").size().eq(90).all()
    assert pd.api.types.is_datetime64_any_dtype(first_load["date"])
    pd.testing.assert_frame_equal(
        first_load.sort_values(["date", "server_id"]).reset_index(drop=True),
        second_load.sort_values(["date", "server_id"]).reset_index(drop=True),
    )


def test_existing_database_records_are_not_merged_with_demo_csv():
    existing_record = pd.DataFrame(
        [
            {
                "date": "2020-01-01",
                "server_id": "Owner Server",
                "total_capacity_gb": 10.0,
                "used_storage_gb": 2.0,
                "available_storage_gb": 8.0,
                "usage_percentage": 20.0,
            }
        ]
    )
    assert import_storage_records(existing_record) == 1

    loaded_records = load_dashboard_records()

    assert len(loaded_records) == 1
    assert loaded_records.iloc[0]["server_id"] == "Owner Server"
    assert get_storage_records()["server_id"].tolist() == ["Owner Server"]


@pytest.mark.parametrize(
    "script_path",
    DASHBOARD_SCRIPTS,
    ids=lambda path: path.relative_to(PROJECT_ROOT).as_posix(),
)
def test_dashboard_scripts_render_without_exceptions(
    script_path,
):
    app = AppTest.from_file(str(script_path), default_timeout=45).run()

    assert not app.exception, [item.message for item in app.exception]
    assert any("Synthetic/demo data only" in item.value for item in app.warning)


def test_alert_page_applies_custom_thresholds():
    app = AppTest.from_file(
        str(PROJECT_ROOT / "pages" / "3_Alerts.py"),
        default_timeout=45,
    ).run()
    assert not app.exception

    app.number_input[0].set_value(60)
    app.number_input[1].set_value(80)
    app.number_input[2].set_value(90)
    app.button[0].click().run()

    assert not app.exception, [item.message for item in app.exception]
    assert any(
        "Normal: below 60.0%" in item.value
        for item in app.caption
    )


def test_monitoring_server_filter_updates_capacity_metrics():
    app = AppTest.from_file(
        str(PROJECT_ROOT / "pages" / "1_Storage_Monitoring.py"),
        default_timeout=45,
    ).run()
    assert not app.exception

    app.selectbox[0].set_value("Server B").run()

    assert not app.exception, [item.message for item in app.exception]
    assert app.metric[0].value == "2,000.00 GB"


def test_report_server_filter_updates_selected_record_count():
    app = AppTest.from_file(
        str(PROJECT_ROOT / "pages" / "4_Reports.py"),
        default_timeout=45,
    ).run()
    assert not app.exception

    app.selectbox[0].set_value("Server B").run()

    assert not app.exception, [item.message for item in app.exception]
    assert any("Selected records: 90." in item.value for item in app.info)
