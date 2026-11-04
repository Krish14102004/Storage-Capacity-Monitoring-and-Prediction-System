# Product Requirements Document (PRD)
## Intelligent Storage Capacity Monitoring and Prediction System

**Status:** Initial specification  
**Version:** 1.0  
**Project type:** Academic Information Storage Management (ISM) project  
**Primary users:** Storage/System Administrators and IT/Infrastructure Managers

---

## 1. Product overview

Build a web-based application that monitors storage capacity across a set of storage servers, presents historical usage, predicts future storage consumption, and warns administrators before capacity becomes critical.

The first release will use a clearly labelled synthetic dataset representing three servers. It will demonstrate the monitoring and forecasting workflow without requiring access to real enterprise infrastructure.

## 2. Problem statement

Storage usage grows over time. If administrators do not notice capacity trends early, a storage volume may become full and cause failed writes, degraded services, or service interruptions. Manually checking multiple servers and estimating future capacity is inefficient.

The proposed system centralizes storage statistics, visualizes usage trends, forecasts capacity requirements using Linear Regression, and provides threshold-based alerts and downloadable reports.

## 3. Product goals

1. Show total, used, and available storage for each monitored server.
2. Calculate and display storage utilization percentages.
3. Show historical storage consumption over time.
4. Forecast future consumption using Linear Regression.
5. Estimate when a server may reach a configured utilization threshold or full capacity.
6. Generate alerts when utilization crosses configured thresholds.
7. Allow users to download CSV and PDF reports.
8. Store server details, historical records, and alerts in SQLite.

## 4. Target users

### 4.1 Storage/System Administrator
- Monitors storage capacity and utilization.
- Reviews historical usage and forecasts.
- Configures warning thresholds.
- Investigates critical alerts.
- Downloads reports.

### 4.2 IT/Infrastructure Manager
- Reviews capacity trends across servers.
- Uses forecasts to plan storage expansion.
- Downloads reports for operational planning.

### 4.3 Evaluator / Demonstrator
- Explores the dashboard using sample data.
- Checks calculations, forecasts, alerts, and report generation.

## 5. Scope

### In scope for the initial version
- Streamlit web dashboard.
- Three simulated servers.
- 90 days of generated historical data per server (270 records total).
- CSV data import and validation.
- SQLite persistence.
- Storage utilization calculations.
- Historical trend charts.
- Linear Regression forecasting.
- Configurable threshold values.
- Normal, Warning, Critical, and Emergency statuses.
- CSV and PDF report downloads.
- Basic validation, error messages, and tests.

### Out of scope for the initial version
- Connecting to production servers or cloud-provider APIs.
- Real-time telemetry agents.
- Automatic disk provisioning or deletion.
- Authentication against an organization identity provider.
- Blockchain, distributed storage, or enterprise-grade high availability.
- Claims that synthetic measurements represent real infrastructure.

These may be considered future enhancements, not silently added to the first release.

## 6. Functional requirements

| ID | Requirement | Acceptance condition |
|---|---|---|
| FR-01 | Load storage records | Valid CSV records load; invalid data produces a clear error |
| FR-02 | Show overview | Dashboard displays total, used, available capacity, and utilization |
| FR-03 | Filter by server | Selecting a server updates its metrics and charts |
| FR-04 | Show history | Historical usage is displayed over time |
| FR-05 | Predict usage | Linear Regression produces future usage estimates from historical records |
| FR-06 | Estimate capacity date | Show an estimated threshold/full date only when the model supports a meaningful estimate |
| FR-07 | Generate alerts | Threshold crossings are labelled and visible |
| FR-08 | Configure thresholds | Thresholds are validated and applied consistently |
| FR-09 | Export CSV | User can download a report containing relevant records and metrics |
| FR-10 | Export PDF | User can download a readable summary report |
| FR-11 | Persist data | Server, history, and alert records can be stored in SQLite |
| FR-12 | Explain limitations | UI identifies sample/synthetic data and forecast assumptions |

## 7. Data requirements

Each storage record should contain:

- `date`: observation date in ISO format (`YYYY-MM-DD`).
- `server_id`: stable server identifier.
- `total_capacity_gb`: total capacity in GB.
- `used_storage_gb`: used capacity in GB.
- `available_storage_gb`: available capacity in GB.
- `usage_percentage`: utilization from 0 to 100.

Initial sample configuration:

| Server | Capacity | Initial used | Approx. daily growth |
|---|---:|---:|---:|
| Server A | 1000 GB | 420 GB | 4.5 GB |
| Server B | 2000 GB | 1100 GB | 8 GB |
| Server C | 500 GB | 250 GB | 2.5 GB |

These values are simulated demonstration data. The generator must prevent used capacity from exceeding total capacity and should keep available capacity non-negative.

## 8. Prediction requirements

- Use `sklearn.linear_model.LinearRegression`.
- Use elapsed days as the independent variable and used storage (GB) as the target.
- Train separately for each server.
- Do not train on future or test observations when evaluating model performance.
- Never present a forecast as a guarantee.
- Avoid extrapolating beyond a documented forecast horizon without a warning.
- If the historical series is insufficient, flat, invalid, or already at capacity, explain that a reliable exhaustion estimate cannot be made.
- Clearly distinguish observed data from predicted data.

## 9. Alert thresholds

Initial defaults (make configurable):

| Utilization | Status |
|---:|---|
| Below 70% | Normal |
| 70% to below 85% | Warning |
| 85% to below 95% | Critical |
| 95% to 100% | Emergency |

Boundary handling must be consistent. Values must be clamped/validated so utilization cannot exceed 100% in the initial simulated dataset.

## 10. Non-functional requirements

- Beginner-friendly code organization and naming.
- Clear separation between UI, data access, business logic, prediction, alerts, and reporting.
- Helpful validation and error messages; no silent failures.
- Reproducible sample dataset generation using a fixed random seed.
- No hard-coded secrets.
- Reasonable performance for a few hundred to a few thousand records.
- Accessible labels, readable charts, and consistent units.
- Tests for calculations, thresholds, prediction edge cases, and exports.

## 11. Success criteria

The first release is successful when:
1. The application starts using the documented command.
2. The generated dataset contains 270 records across three servers.
3. Dashboard totals and utilization calculations are correct.
4. Server filters update the displayed data.
5. Historical charts render.
6. Linear Regression forecasts are displayed and labelled as estimates.
7. Threshold alerts match the configured rules.
8. CSV and PDF reports download successfully.
9. Invalid/missing data produces understandable errors.
10. The README explains setup, execution, limitations, and project structure.

## 12. Assumptions and risks

- Initial data is synthetic, not collected from real machines.
- Linear Regression assumes a roughly linear usage trend; actual growth may be seasonal or irregular.
- A forecast date depends on the observed growth trend and may change as new data arrives.
- The project is an academic prototype, not a production monitoring platform.
- SQLite is sufficient for the demonstration scale.

## 13. Future enhancements

- Real server metrics collection (e.g., an authenticated agent or approved monitoring API).
- Cloud storage integrations.
- More advanced forecasting models with evaluation and comparison.
- User authentication and role-based access.
- Email notifications.
- Multiple storage volumes per server.
- Scheduled data collection and report generation.
