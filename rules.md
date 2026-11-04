# Project Rules and Engineering Boundaries

These rules apply to every implementation phase and to any AI coding agent contributing to the project.

## 1. Approved stack

Use:
- Python 3.10+ (prefer a version supported by all pinned dependencies).
- Streamlit for the UI.
- Pandas and NumPy for data handling.
- Scikit-learn `LinearRegression` for the approved forecasting baseline.
- Plotly for charts.
- SQLite through Python's standard `sqlite3` module.
- ReportLab for PDF generation.
- pytest for tests.

Avoid adding dependencies unless a concrete requirement cannot be met by the approved stack. Explain the reason and ask the project owner before adding a major dependency.

## 2. Architecture rules

- Keep UI, data loading, business logic, prediction, database access, alerts, and reports in separate modules.
- Do not put the entire application in `app.py`.
- Do not duplicate business rules across pages.
- Do not import Streamlit into model or database modules.
- Use functions with clear inputs and outputs.
- Use `pathlib.Path` for filesystem paths.
- Keep configuration values in one documented location; do not scatter magic numbers.

## 3. Data and validation rules

- Label generated data as synthetic/demo data in the UI and documentation.
- Never describe simulated records as real organization measurements.
- Validate required columns, types, date parsing, duplicate observations, and numeric ranges.
- Capacity must be positive; used and available storage must be non-negative.
- Used storage must not exceed total capacity in the initial dataset.
- Reconcile `used + available` with `total` within a documented tolerance.
- Do not silently drop malformed records. Report how many records are rejected and why.
- Do not overwrite a user's input dataset without explicit confirmation.

## 4. Prediction rules

- Use Linear Regression as the baseline model.
- Train separately for each server.
- Use elapsed time (days) as the feature and used storage in GB as the target.
- Sort observations by date before fitting.
- Guard against too few observations, missing values, zero/negative slope, capacity already reached, and unrealistic forecast horizons.
- Distinguish observed points from predicted points visually and textually.
- State that forecasts are estimates based on historical trends, not guarantees.
- Do not claim high accuracy without a valid evaluation procedure and reported metric.
- Do not silently replace Linear Regression with another model.

## 5. Alert rules

Initial default thresholds:
- Below 70%: Normal
- 70% to below 85%: Warning
- 85% to below 95%: Critical
- 95% to 100%: Emergency

Keep threshold definitions centralized. Test exact boundary values (70, 85, 95, 100). Do not create duplicate alerts on every page refresh; use a stable deduplication rule or document that alerts are generated as a current-state view.

## 6. Error handling and logging

- Catch specific exceptions where possible; do not use broad `except:`.
- Show users concise, actionable messages.
- Keep technical details in logs or developer diagnostics, not in confusing UI stack traces.
- Never hide a failed import, failed prediction, failed database write, or failed report export.
- Validate external/user-provided input before processing.
- Do not log secrets or sensitive records.

## 7. AI agent boundaries

The AI coding agent must:
- Read `PRD.md`, `architecture.md`, `rules.md`, `phases.md`, `design.md`, and `memory.md` before editing.
- Work only on the current phase unless asked to proceed.
- Inspect the existing files before modifying them.
- Explain the intended change and list files it will create/edit.
- Ask the project owner to perform any required manual action, with exact steps, expected result, and how to report completion.
- Never claim a command, download, installation, test, or deployment succeeded unless it actually observed the result.
- Update `memory.md` after each completed task or phase.
- Ask before changing the approved stack, scope, thresholds, schema, or design system.
- Never invent API keys, credentials, datasets, URLs, or user-specific environment details.

The agent must not:
- Add real server monitoring, cloud integrations, authentication, email, or external APIs without approval.
- upload project data to third-party services.
- fabricate test results or screenshots.
- replace the chosen Streamlit interface with React.
- add AI/LLM features: the current project is a deterministic storage monitoring and Linear Regression forecasting system, not an autonomous agent.

## 8. Security and privacy

- No credentials are required for the initial local prototype.
- Never commit `.env`, secrets, private keys, or real infrastructure records.
- Keep the SQLite database local and exclude it from version control by default.
- If real organizational data is proposed later, stop and ask for permission and data-handling requirements first.

## 9. Code quality

- Use descriptive names and type hints for non-trivial functions.
- Add docstrings to public functions.
- Keep functions focused and reasonably short.
- Add tests for calculations, edge cases, and data validation.
- Prefer deterministic tests and fixed random seeds.
- Avoid unnecessary abstractions and premature optimization.
