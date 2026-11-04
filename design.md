# Visual Design Specification
## Intelligent Storage Capacity Monitoring and Prediction System

**Design direction:** Clean, professional infrastructure-monitoring dashboard. Prioritize readability, clear status communication, and compact data visualization.

## 1. Theme

- Light theme by default.
- Neutral surfaces with a restrained blue accent.
- Use status colors only for operational states.
- Avoid decorative gradients, excessive shadows, and crowded layouts.
- Keep charts and tables visually consistent.

## 2. Color palette

| Role | Color | Hex |
|---|---|---|
| Page background | Cool light gray | `#F3F5F9` |
| Main surface | White | `#FFFFFF` |
| Primary text | Charcoal | `#1F2937` |
| Secondary text | Slate gray | `#64748B` |
| Primary accent | Blue | `#2563EB` |
| Accent hover | Dark blue | `#1D4ED8` |
| Border | Light slate | `#E2E8F0` |
| Normal | Green | `#16A34A` |
| Warning | Amber | `#D97706` |
| Critical | Orange | `#EA580C` |
| Emergency | Red | `#DC2626` |

Do not rely on color alone: show text labels/icons for alert severity.

## 3. Typography

- Preferred font: Inter.
- Fallback: system sans-serif.
- Page title: 24–30 px, semibold.
- Section heading: 18–22 px, semibold.
- Metric value: 26–32 px, semibold.
- Body text: 14–16 px, regular.
- Supporting labels: 12–13 px.
- Tables: 13–14 px with adequate row spacing.

Use consistent capitalization and concise labels. Always include units (GB, %, days).

## 4. Layout

- Sidebar navigation for Overview, Storage Monitoring, Capacity Prediction, Alerts, and Reports.
- Main content uses a responsive single-column flow with metric cards arranged in rows where space allows.
- Keep a consistent page title and short explanatory subtitle.
- Place filters near the top of the relevant page.
- Use tables for exact values and charts for trends.
- Avoid horizontal scrolling where possible.

## 5. Dashboard components

### Overview metric cards
- Total capacity
- Used storage
- Available storage
- Average utilization

### Storage monitoring
- Server selector
- Utilization progress indicator
- Historical usage line chart
- Detailed storage table

### Capacity prediction
- Historical observations and predicted line shown distinctly
- Forecast horizon selector
- Estimated threshold-crossing date, or a clear explanation when unavailable
- Visible note: forecasts are estimates based on historical data

### Alerts
- Severity label
- Server name
- Current utilization
- Threshold crossed
- Date/time or observation date

### Reports
- Server/date filters
- CSV download
- PDF download

## 6. Chart rules

- Use Plotly.
- Label axes and units.
- Include legends when observed and predicted series are shown together.
- Keep dates chronological.
- Avoid misleading truncated axes unless clearly indicated.
- Use consistent server labels across pages.
- Do not imply that simulated values are live telemetry.

## 7. Streamlit implementation notes

- Use Streamlit's native layout and widgets first.
- Use `assets/style.css` only for small, necessary visual refinements.
- Do not inject unsafe HTML or JavaScript for basic styling.
- Do not add a React frontend; Streamlit is the approved interface.
