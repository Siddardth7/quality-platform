"""
exporter.py
Control Plan — Export Layer

Composes the shared, app-agnostic export primitives in ``quality_core.io.export``
(CSV/formula-injection escaping, openpyxl styling, fpdf2 table rendering) — the
same machinery FMEA uses. No matplotlib/chart pages: a Control Plan is a table.

Functions:
    export_csv(dataset)   -> bytes  (UTF-8 CSV, formula-injection escaped)
    export_excel(dataset) -> bytes  (openpyxl .xlsx — plan sheet + metadata sheet)
    export_pdf(dataset)   -> bytes  (fpdf2 .pdf, plan table only)

All return raw bytes suitable for ``st.download_button()``.
"""

from __future__ import annotations

import io
from datetime import datetime
from typing import Any

import openpyxl
import pandas as pd
from fpdf import FPDF
from quality_core.io.export import (
    export_csv as _core_export_csv,
)
from quality_core.io.export import (
    pdf_subheader,
    pdf_title,
    render_table,
    safe_text,
    sanitize_for_export,
    write_keyvalue_sheet,
    write_table_sheet,
)

from controlplan_app import __version__
from controlplan_app.schema import ControlPlanDataset

# Column order matches the template/export order named in the spec.
# `source_cause_id` (OQ1, W07-2 #89) is appended last so the FMEA join key
# survives a CSV export/reimport round trip — not part of the original AIAG
# column set, so it goes after it rather than reordering the documented shape.
_EXPORT_COLUMNS = [
    "characteristic",
    "lsl",
    "usl",
    "target",
    "measurement_method",
    "sample_size",
    "frequency",
    "recommended_chart",
    "reaction_plan",
    "source_cause_id",
]

_COL_WIDTHS = {
    "characteristic": 30,
    "lsl": 10,
    "usl": 10,
    "target": 10,
    "measurement_method": 24,
    "sample_size": 12,
    "frequency": 14,
    "recommended_chart": 16,
    "reaction_plan": 40,
}

_PDF_TABLE_COLS = [
    ("Characteristic", 50),
    ("LSL", 16),
    ("USL", 16),
    ("Target", 16),
    ("Method", 40),
    ("n", 10),
    ("Frequency", 25),
    ("Chart", 18),
    ("Reaction Plan", 66),
]

_TOOL_VERSION = __version__


def _to_dataframe(dataset: ControlPlanDataset) -> pd.DataFrame:
    """Validated dataset -> DataFrame, columns in the export order above."""
    df = pd.DataFrame([row.model_dump() for row in dataset.rows])
    if df.empty:
        return pd.DataFrame(columns=_EXPORT_COLUMNS)
    return df[_EXPORT_COLUMNS]


def export_csv(dataset: ControlPlanDataset) -> bytes:
    """Export the validated Control Plan to UTF-8 CSV bytes (injection-escaped)."""
    return _core_export_csv(_to_dataframe(dataset))


def _metadata_rows(df: pd.DataFrame) -> list[tuple[str, object]]:
    return [
        ("Generated", datetime.now().strftime("%Y-%m-%d %H:%M:%S")),
        ("Tool Version", _TOOL_VERSION),
        ("Engineering Ref", "AIAG Control Plan format (see ROADMAP.md §4)"),
        ("Row Count", len(df)),
    ]


def export_excel(dataset: ControlPlanDataset) -> bytes:
    """Export the validated Control Plan to an Excel workbook.

    Sheet 1 — "Control Plan": the plan table. Sheet 2 — "Metadata": run
    timestamp, tool version, standards ref, row count.
    """
    df = sanitize_for_export(_to_dataframe(dataset))
    wb = openpyxl.Workbook()

    ws = wb.active
    assert ws is not None  # a freshly created workbook always has an active sheet
    write_table_sheet(
        ws, df,
        title="Control Plan",
        columns=_EXPORT_COLUMNS,
        col_widths=_COL_WIDTHS,
    )
    write_keyvalue_sheet(wb.create_sheet("Metadata"), _metadata_rows(df))

    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()


def _pdf_row_values(row: pd.Series) -> list[str]:
    return [
        safe_text(str(row.get("characteristic", ""))[:40]),
        safe_text("" if pd.isna(row.get("lsl")) else row.get("lsl")),
        safe_text("" if pd.isna(row.get("usl")) else row.get("usl")),
        safe_text("" if pd.isna(row.get("target")) else row.get("target")),
        safe_text(str(row.get("measurement_method", ""))[:30]),
        safe_text(str(row.get("sample_size", ""))),
        safe_text(str(row.get("frequency", ""))[:18]),
        safe_text("" if pd.isna(row.get("recommended_chart")) else row.get("recommended_chart")),
        safe_text(str(row.get("reaction_plan", ""))[:60]),
    ]


def _pdf_row_rgb(row: pd.Series) -> tuple[int, int, int]:
    return (255, 255, 255)


def _pdf_page1(pdf: Any, df: pd.DataFrame) -> None:
    pdf.add_page()
    pdf_title(pdf, "Control Plan")
    pdf_subheader(
        pdf,
        f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}   |   "
        "AIAG Control Plan format",
    )
    render_table(
        pdf, df,
        columns=_PDF_TABLE_COLS,
        row_values=_pdf_row_values,
        row_rgb=_pdf_row_rgb,
    )


def export_pdf(dataset: ControlPlanDataset) -> bytes:
    """Export the validated Control Plan to a PDF report (table only, no charts)."""
    df = _to_dataframe(dataset)

    pdf = FPDF(orientation="L", unit="mm", format="A4")
    pdf.set_auto_page_break(auto=True, margin=12)
    pdf.set_margins(10, 10, 10)

    _pdf_page1(pdf, df)

    return bytes(pdf.output())
