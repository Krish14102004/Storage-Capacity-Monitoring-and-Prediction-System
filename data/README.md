# Data directory — Phase 1

This directory contains the generated or owner-approved input dataset.
- `storage_data.csv` is created by `modules/data_generator.py`.
- Expected initial dataset: 90 days × 3 servers = 270 rows.
- Label all generated data as synthetic/demo data.
- Do not commit real infrastructure data or overwrite owner-provided data without approval.

## Generate and validate

From the project root, generate the reproducible synthetic sample with:

```powershell
python -m modules.data_generator
```

This writes `storage_data.csv`, replacing any existing file at that path. Do not
run it over an owner-provided dataset without first backing it up or obtaining
approval.

Validate the current CSV without changing it:

```powershell
python -c "from modules.data_loader import load_and_validate_csv; df = load_and_validate_csv('data/storage_data.csv'); print(f'Valid rows: {len(df)}; servers: {df.server_id.nunique()}')"
python -m pytest tests/test_data_loader.py
```

The loader checks the required schema, dates, numeric values, capacity bounds,
duplicate server/date pairs, and that `used + available` equals total capacity
within 0.02 GB. It also checks that utilization matches `used / total * 100`
within 0.02 percentage points.
