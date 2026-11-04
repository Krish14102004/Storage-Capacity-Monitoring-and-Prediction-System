# Intelligent Storage Capacity Monitoring and Prediction System

A Streamlit-based academic ISM project for storage utilization monitoring, historical analysis, Linear Regression forecasting, threshold alerts, and downloadable CSV/PDF reports.

## Approved stack

Python, Streamlit, Pandas, NumPy, Scikit-learn, Plotly, SQLite, ReportLab, pytest.
Use Python 3.10 or newer.

## Current status

Phases 1–6 provide synthetic dataset generation and validation, storage
calculations, local SQLite persistence, Linear Regression forecasts, threshold
alerts, CSV/PDF reports, and the Streamlit dashboard. Check `memory.md` for
verified progress and remaining phase gates. Phase 6 adds automated dashboard
integration tests and setup/run verification.

## Quick start (after Phase 0 setup)

```bash
python -m venv .venv
```

Windows PowerShell:
```powershell
.venv\Scripts\Activate.ps1
```

Windows Command Prompt:
```bat
.venv\Scripts\activate.bat
```

Install dependencies:
```bash
pip install -r requirements.txt
```

Generate the synthetic Phase 1 CSV with:
```bash
python -m modules.data_generator
```

This command replaces `data/storage_data.csv` if it already exists. Do not run
it over an owner-provided dataset without approval. Validate the existing file
without changing it:
```bash
python -c "from modules.data_loader import load_and_validate_csv; df = load_and_validate_csv('data/storage_data.csv'); print(f'Valid rows: {len(df)}; servers: {df.server_id.nunique()}')"
python -m pytest tests/test_data_loader.py
```

Import the validated dataset into the local SQLite database:
```bash
python -c "from modules.data_loader import load_and_validate_csv; from modules.database_manager import import_storage_records; records = load_and_validate_csv('data/storage_data.csv'); print(f'Inserted records: {import_storage_records(records)}')"
```
The SQLite file is created only when this import runs. Identical repeated
imports are skipped; conflicting existing observations are reported and not
overwritten. See `database/README.md` for database functions and filtering.

Phase 3 exposes deterministic business logic for per-server Linear Regression
forecasts (`models.prediction_model.predict_server_usage`) and current-state
threshold evaluation (`modules.alert_manager.generate_current_alerts`). The
forecast horizon is limited to 90 days; threshold crossing dates are omitted
when growth is flat/decreasing, capacity or the threshold is already reached,
or the fitted crossing is beyond that limit. Alert thresholds default to 70%,
85%, and 95%, and can be overridden with `AlertThresholds`.

Phase 4 report functions accept prepared storage records and return downloadable
bytes:
```python
from modules.report_generator import generate_csv_report, generate_pdf_report

csv_bytes = generate_csv_report(records)
pdf_bytes = generate_pdf_report(records)
```
Both exports include the generation time, selected server/date range, units,
and a `Synthetic/demo data` label by default. Pass already-filtered records to
report only a selected server or date range. Invalid or inconsistent records
raise a clear validation error; empty filtered results produce valid empty
reports.

## Run the dashboard

From the project root, launch the Streamlit app:
```bash
python -m streamlit run app.py
```

The first dashboard run validates `data/storage_data.csv` and imports it into
`database/storage.db` only when that database has no storage records. The
database is local and excluded from version control. Later runs use the stored
observations; they do not overwrite or automatically merge changes into the
database.

The sidebar provides Overview, Storage Monitoring, Capacity Prediction,
Alerts, and Reports pages. The Alerts page can configure thresholds for the
current Streamlit session. The Reports page filters by server and date before
offering CSV and PDF downloads. All pages identify the sample as synthetic;
forecasts are estimates based on historical trends, not guarantees.

## Verify the project

Run the complete unit and dashboard integration test suite from the project
root:

```powershell
python -m pytest -q
```

The dashboard tests use temporary SQLite databases and do not read or modify
`database/storage.db`. The tests cover dataset generation and validation,
capacity calculations, database imports and filters, predictions, threshold
alerts, CSV/PDF exports, and Streamlit page rendering.

To check installed dependency consistency:

```powershell
python -m pip check
```

## Project documents

- `PRD.md` — requirements, users, features, acceptance criteria.
- `architecture.md` — app flow, architecture, data model, file structure, stack.
- `rules.md` — coding, validation, security, and AI-agent boundaries.
- `phases.md` — phased implementation plan.
- `design.md` — colors, theme, typography, and UI rules.
- `memory.md` — ongoing implementation progress.
- `AI_AGENT_PROMPT.md` — reusable AI coding-agent instructions.

## Important

The first dataset is synthetic demonstration data, not real server telemetry. Predictions are estimates based on historical trends and are not guarantees.
