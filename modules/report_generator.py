"""[Phase 4] Generate validated CSV and PDF storage reports."""

from datetime import datetime
from io import BytesIO, StringIO
from xml.sax.saxutils import escape

import numpy as np
import pandas as pd
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import (
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)


REPORT_COLUMNS = [
    "date",
    "server_id",
    "total_capacity_gb",
    "used_storage_gb",
    "available_storage_gb",
    "usage_percentage",
]
NUMERIC_COLUMNS = [
    "total_capacity_gb",
    "used_storage_gb",
    "available_storage_gb",
    "usage_percentage",
]
ARITHMETIC_TOLERANCE_GB = 0.02
PERCENTAGE_TOLERANCE = 0.02
DEFAULT_DATA_LABEL = "Synthetic/demo data"


def _validate_records(records: pd.DataFrame) -> pd.DataFrame:
    if not isinstance(records, pd.DataFrame):
        raise TypeError("Report records must be provided as a pandas DataFrame.")
    missing = set(REPORT_COLUMNS) - set(records.columns)
    if missing:
        raise ValueError(f"Missing required report columns: {', '.join(sorted(missing))}")

    frame = records[REPORT_COLUMNS].copy()
    parsed_dates = pd.to_datetime(frame["date"], errors="coerce")
    if parsed_dates.isna().any():
        raise ValueError("Report records contain invalid dates.")
    frame["date"] = parsed_dates.dt.strftime("%Y-%m-%d")

    server_ids = frame["server_id"].astype("string").str.strip()
    if server_ids.isna().any() or server_ids.eq("").any():
        raise ValueError("server_id cannot be empty.")
    frame["server_id"] = server_ids

    for column in NUMERIC_COLUMNS:
        frame[column] = pd.to_numeric(frame[column], errors="coerce")
    numeric_values = frame[NUMERIC_COLUMNS].to_numpy(dtype=float)
    if not np.isfinite(numeric_values).all():
        raise ValueError("Report records must contain finite numeric values.")
    if (frame["total_capacity_gb"] <= 0).any():
        raise ValueError("total_capacity_gb must be greater than zero.")
    if (frame[["used_storage_gb", "available_storage_gb"]] < 0).any().any():
        raise ValueError("Used and available storage cannot be negative.")
    if (frame["used_storage_gb"] > frame["total_capacity_gb"]).any():
        raise ValueError("Used storage cannot exceed total capacity.")
    if ((frame["usage_percentage"] < 0) | (frame["usage_percentage"] > 100)).any():
        raise ValueError("usage_percentage must be between 0 and 100.")

    capacity_error = (
        frame["used_storage_gb"]
        + frame["available_storage_gb"]
        - frame["total_capacity_gb"]
    ).abs()
    if (capacity_error > ARITHMETIC_TOLERANCE_GB).any():
        raise ValueError("Used storage plus available storage must equal total capacity.")
    expected_usage = frame["used_storage_gb"] / frame["total_capacity_gb"] * 100
    if ((frame["usage_percentage"] - expected_usage).abs() > PERCENTAGE_TOLERANCE).any():
        raise ValueError("usage_percentage does not match used storage and capacity.")
    if frame.duplicated(subset=["date", "server_id"]).any():
        raise ValueError("Duplicate date/server_id observations were found.")

    return frame.sort_values(["date", "server_id"]).reset_index(drop=True)


def _report_metadata(
    records: pd.DataFrame,
    generated_at: datetime | None,
    data_label: str,
) -> dict[str, str]:
    if not isinstance(data_label, str) or not data_label.strip():
        raise ValueError("data_label must be a non-empty string.")
    if generated_at is not None and not isinstance(generated_at, datetime):
        raise TypeError("generated_at must be a datetime or None.")

    report_time = generated_at or datetime.now().astimezone()
    if report_time.tzinfo is None:
        generated_text = report_time.strftime("%Y-%m-%d %H:%M")
    else:
        generated_text = report_time.strftime("%Y-%m-%d %H:%M %Z")

    if records.empty:
        server_summary = "No servers"
        start_date = end_date = "No records"
    else:
        servers = sorted(records["server_id"].unique())
        server_summary = ", ".join(servers)
        start_date = records["date"].min()
        end_date = records["date"].max()

    return {
        "generated_at": generated_text,
        "data_label": data_label.strip(),
        "server_summary": server_summary,
        "start_date": start_date,
        "end_date": end_date,
    }


def _csv_ready_frame(
    records: pd.DataFrame,
    metadata: dict[str, str],
) -> pd.DataFrame:
    frame = records.rename(
        columns={
            "date": "date",
            "total_capacity_gb": "total_capacity_gb",
            "used_storage_gb": "used_storage_gb",
            "available_storage_gb": "available_storage_gb",
            "usage_percentage": "usage_percentage",
        }
    ).copy()
    frame.insert(0, "data_label", metadata["data_label"])
    frame.insert(1, "report_generated_at", metadata["generated_at"])
    frame.insert(2, "report_servers", metadata["server_summary"])
    frame.insert(3, "report_start_date", metadata["start_date"])
    frame.insert(4, "report_end_date", metadata["end_date"])
    return frame


def generate_csv_report(
    records: pd.DataFrame,
    *,
    generated_at: datetime | None = None,
    data_label: str = DEFAULT_DATA_LABEL,
) -> bytes:
    """Return UTF-8 CSV bytes with report context and storage observations."""
    frame = _validate_records(records)
    metadata = _report_metadata(frame, generated_at, data_label)
    output = StringIO()
    _csv_ready_frame(frame, metadata).to_csv(output, index=False, lineterminator="\n")
    return output.getvalue().encode("utf-8")


def _pdf_table(records: pd.DataFrame, styles) -> Table:
    headers = [
        "Date",
        "Server",
        "Total (GB)",
        "Used (GB)",
        "Available (GB)",
        "Usage (%)",
    ]
    rows = [headers]
    for record in records.itertuples(index=False):
        rows.append(
            [
                record.date,
                Paragraph(escape(str(record.server_id)), styles["table_cell"]),
                f"{record.total_capacity_gb:,.2f}",
                f"{record.used_storage_gb:,.2f}",
                f"{record.available_storage_gb:,.2f}",
                f"{record.usage_percentage:.2f}%",
            ]
        )

    table = Table(
        rows,
        colWidths=[25 * mm, 36 * mm, 30 * mm, 30 * mm, 34 * mm, 26 * mm],
        repeatRows=1,
        hAlign="LEFT",
    )
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#2563EB")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, -1), 8),
                ("LEADING", (0, 0), (-1, -1), 10),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#CBD5E1")),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F3F5F9")]),
                ("ALIGN", (2, 1), (-1, -1), "RIGHT"),
                ("LEFTPADDING", (0, 0), (-1, -1), 5),
                ("RIGHTPADDING", (0, 0), (-1, -1), 5),
                ("TOPPADDING", (0, 0), (-1, -1), 5),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ]
        )
    )
    return table


def generate_pdf_report(
    records: pd.DataFrame,
    *,
    generated_at: datetime | None = None,
    data_label: str = DEFAULT_DATA_LABEL,
) -> bytes:
    """Return a readable PDF summary and table for the supplied observations."""
    frame = _validate_records(records)
    metadata = _report_metadata(frame, generated_at, data_label)
    output = BytesIO()
    document = SimpleDocTemplate(
        output,
        pagesize=landscape(A4),
        rightMargin=15 * mm,
        leftMargin=15 * mm,
        topMargin=15 * mm,
        bottomMargin=15 * mm,
        title="Storage Capacity Report",
        author="Intelligent Storage Capacity Monitoring System",
    )
    styles = getSampleStyleSheet()
    styles.add(
        ParagraphStyle(
            name="ReportTitle",
            parent=styles["Title"],
            alignment=TA_CENTER,
            textColor=colors.HexColor("#1F2937"),
            fontName="Helvetica-Bold",
            fontSize=18,
            leading=22,
        )
    )
    styles.add(
        ParagraphStyle(
            name="table_cell",
            parent=styles["BodyText"],
            fontName="Helvetica",
            fontSize=8,
            leading=10,
            spaceAfter=0,
        )
    )

    content = [
        Paragraph("Storage Capacity Report", styles["ReportTitle"]),
        Spacer(1, 5 * mm),
        Paragraph(f"<b>Data:</b> {escape(metadata['data_label'])}", styles["BodyText"]),
        Paragraph(
            f"<b>Generated:</b> {escape(metadata['generated_at'])}",
            styles["BodyText"],
        ),
        Paragraph(
            f"<b>Server(s):</b> {escape(metadata['server_summary'])}",
            styles["BodyText"],
        ),
        Paragraph(
            f"<b>Date range:</b> {escape(metadata['start_date'])} to "
            f"{escape(metadata['end_date'])}",
            styles["BodyText"],
        ),
        Paragraph(f"<b>Records:</b> {len(frame)}", styles["BodyText"]),
        Spacer(1, 4 * mm),
    ]

    if frame.empty:
        content.append(Paragraph("No storage records match the selected filters.", styles["BodyText"]))
    else:
        grouped = frame.groupby("server_id", sort=True)
        summary = []
        for server_id, server_records in grouped:
            latest = server_records.iloc[-1]
            summary.append(
                [
                    Paragraph(escape(str(server_id)), styles["table_cell"]),
                    f"{latest['total_capacity_gb']:,.2f} GB",
                    f"{latest['used_storage_gb']:,.2f} GB",
                    f"{latest['available_storage_gb']:,.2f} GB",
                    f"{latest['usage_percentage']:.2f}%",
                ]
            )
        summary_table = Table(
            [
                ["Server", "Total capacity", "Latest used", "Latest available", "Latest utilization"],
                *summary,
            ],
            colWidths=[38 * mm, 38 * mm, 38 * mm, 43 * mm, 40 * mm],
            repeatRows=1,
        )
        summary_table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#E2E8F0")),
                    ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                    ("FONTSIZE", (0, 0), (-1, -1), 8),
                    ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#CBD5E1")),
                    ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                    ("LEFTPADDING", (0, 0), (-1, -1), 5),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 5),
                    ("TOPPADDING", (0, 0), (-1, -1), 5),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
                ]
            )
        )
        content.extend(
            [
                Paragraph("Latest server summary", styles["Heading2"]),
                summary_table,
                Spacer(1, 5 * mm),
                Paragraph("Storage observations", styles["Heading2"]),
                _pdf_table(frame, styles),
            ]
        )

    document.build(content)
    return output.getvalue()
