# Database directory — Phase 2

The SQLite database is created at runtime by `modules/database_manager.py`.
Expected tables: `servers`, `storage_records`, and `alerts`.
The database file is generated locally and is excluded from version control.

## Import validated CSV records

From the project root, run this command to validate the existing CSV, initialize
the default local database, and import the records:

```powershell
python -c "from modules.data_loader import load_and_validate_csv; from modules.database_manager import import_storage_records; records = load_and_validate_csv('data/storage_data.csv'); print(f'Inserted records: {import_storage_records(records)}')"
```

The database is created at `database/storage.db` only when initialized or
accessed. The import is safe to repeat: identical observations are skipped,
while conflicting server/date observations or changed server capacity raise a
clear error and roll back the import. The initial schema treats each server's
capacity as fixed; a capacity change requires a future schema decision rather
than silently rewriting historical metrics.

Use the module functions to initialize an alternate database, query the data,
or filter by server and ISO date:

```python
from modules.database_manager import get_storage_records, initialize_database

initialize_database("database/demo.db")
records = get_storage_records(
    server_id="Server A",
    start_date="2026-01-01",
    end_date="2026-03-31",
    db_path="database/demo.db",
)
```
