"""
exporter.py
FMEA Risk Prioritization Tool — Export Layer

FMEA-specific export *config* (which columns, tier colors, metadata, PDF layout)
composed over the shared, app-agnostic primitives in ``quality_core.io.export``
(CSV/formula-injection escaping, openpyxl styling, fpdf2 table rendering). The
shared machinery is written once in core and reused by SPC and the Control Plan.

Functions:
    export_csv(df)   → bytes  (UTF-8 CSV, formula-injection escaped)
    export_excel(df) → bytes  (openpyxl .xlsx — ranked sheet + metadata sheet)
    export_pdf(df)   → bytes  (fpdf2 .pdf, charts rendered via matplotlib)

All return raw bytes suitable for st.download_button().

Author: Siddardth | M.S. Aerospace Engineering, UIUC
"""

from __future__ import annotations

import io
import os
import tempfile
from datetime import datetime
from typing import Any

import openpyxl
import pandas as pd
from quality_core.io.export import (
    add_image_page,
    export_csv,
    render_table,
    safe_text,
    sanitize_for_export,
    write_keyvalue_sheet,
    write_table_sheet,
)
from quality_core.theme import TIER_FILL_HEX, TIER_RGB

from fmea_app import __version__

# Re-export the shared CSV exporter and sanitizer under the names this module's
# consumers/tests already use (behavior is identical — the logic now lives in core).
_sanitize_for_export = sanitize_for_export

# ---------------------------------------------------------------------------
# FMEA export configuration
# ---------------------------------------------------------------------------

_EXPORT_COLUMNS = [
    "ID", "Process_Step", "Component", "Failure_Mode",
    "Effect", "Severity", "Occurrence", "Detection",
    "RPN", "AP", "Risk_Tier",
    "Flag_High_RPN", "Flag_High_Severity", "Flag_Action_Priority_H",
]

_COL_WIDTHS = {
    "ID": 6, "Process_Step": 20, "Component": 16, "Failure_Mode": 28,
    "Effect": 24, "Severity": 10, "Occurrence": 12, "Detection": 11,
    "RPN": 8, "AP": 10, "Risk_Tier": 12,
    "Flag_High_RPN": 14, "Flag_High_Severity": 16, "Flag_Action_Priority_H": 20,
}

# Read from the package single source of truth (fmea_app/__init__.py) — never hardcode.
_TOOL_VERSION = __version__

_PDF_TABLE_COLS = [
    ("ID",           10),
    ("Process Step", 38),
    ("Failure Mode", 52),
    ("S",             8),
    ("O",             8),
    ("D",             8),
    ("RPN",          12),
    ("AP",           14),
    ("Tier",         16),
    ("Flags",        51),
]


def _row_tier(row: pd.Series) -> str:
    return str(row.get("Risk_Tier", "Green"))


def _excel_row_fill(row: pd.Series) -> str:
    """Tier → solid fill hex for the Excel ranked sheet (defaults to Green)."""
    return TIER_FILL_HEX.get(_row_tier(row), TIER_FILL_HEX["Green"])


# ---------------------------------------------------------------------------
# export_excel
# ---------------------------------------------------------------------------

def export_excel(df: pd.DataFrame) -> bytes:
    """
    Export the analyzed FMEA DataFrame to an Excel workbook.

    Sheet 1 — "FMEA Analysis": ranked table with Risk_Tier row coloring.
    Sheet 2 — "Metadata": run timestamp, row counts, flag summary.

    Parameters
    ----------
    df : pd.DataFrame
        Output of run_pipeline() — must include RPN, Risk_Tier, Flag_* columns.

    Returns
    -------
    bytes
        Raw .xlsx bytes suitable for st.download_button().
    """
    df = sanitize_for_export(df)
    wb = openpyxl.Workbook()

    ws = wb.active
    assert ws is not None  # a freshly created workbook always has an active sheet
    write_table_sheet(
        ws, df,
        title="FMEA Analysis",
        columns=_EXPORT_COLUMNS,
        col_widths=_COL_WIDTHS,
        row_fill_hex=_excel_row_fill,
    )
    write_keyvalue_sheet(wb.create_sheet("Metadata"), _metadata_rows(df))

    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()


def _metadata_rows(df: pd.DataFrame) -> list[tuple[str, object]]:
    return [
        ("Generated",         datetime.now().strftime("%Y-%m-%d %H:%M:%S")),
        ("Tool Version",      _TOOL_VERSION),
        ("Engineering Ref",   "AIAG FMEA-4 (4th Ed.) + AIAG/VDA FMEA Handbook (5th Ed., 2019)"),
        ("",                  ""),
        ("Total Rows",        len(df)),
        ("Red (Immediate)",   int((df["Risk_Tier"] == "Red").sum())    if "Risk_Tier"               in df.columns else "N/A"),
        ("Yellow",            int((df["Risk_Tier"] == "Yellow").sum()) if "Risk_Tier"               in df.columns else "N/A"),
        ("Green",             int((df["Risk_Tier"] == "Green").sum())  if "Risk_Tier"               in df.columns else "N/A"),
        ("High RPN (>100)",   int(df["Flag_High_RPN"].sum())           if "Flag_High_RPN"           in df.columns else "N/A"),
        ("Severity >= 9",     int(df["Flag_High_Severity"].sum())      if "Flag_High_Severity"      in df.columns else "N/A"),
        ("Action Priority H", int(df["Flag_Action_Priority_H"].sum())  if "Flag_Action_Priority_H"  in df.columns else "N/A"),
        ("",                  ""),
        ("AP High",           int((df["AP"] == "High").sum())          if "AP"                      in df.columns else "N/A"),
        ("AP Medium",         int((df["AP"] == "Medium").sum())        if "AP"                      in df.columns else "N/A"),
        ("AP Low",            int((df["AP"] == "Low").sum())           if "AP"                      in df.columns else "N/A"),
    ]


# ---------------------------------------------------------------------------
# export_pdf
# ---------------------------------------------------------------------------

def export_pdf(df: pd.DataFrame) -> bytes:
    """
    Export the analyzed FMEA DataFrame to a PDF report using matplotlib.

    Page 1: Summary header + flag counts + ranked FMEA table.
    Page 2: Pareto chart (matplotlib).
    Page 3: Risk heatmap (matplotlib).

    Parameters
    ----------
    df : pd.DataFrame
        Output of run_pipeline().

    Returns
    -------
    bytes
        Raw .pdf bytes suitable for st.download_button().
    """
    import matplotlib.pyplot as plt
    from fpdf import FPDF

    from fmea_app.visualizer import pareto_chart as mpl_pareto
    from fmea_app.visualizer import risk_heatmap as mpl_heatmap

    pdf = FPDF(orientation="L", unit="mm", format="A4")
    pdf.set_auto_page_break(auto=True, margin=12)
    pdf.set_margins(10, 10, 10)

    _pdf_page1(pdf, df)

    # Use matplotlib (no Chrome/kaleido needed on Streamlit Cloud)
    with tempfile.TemporaryDirectory(prefix="fmea_pdf_") as tmp_dir:
        for idx, (chart_fn, title) in enumerate([
            (lambda: mpl_pareto(df),   "Pareto Chart - Failure Modes Ranked by RPN"),
            (lambda: mpl_heatmap(df),  "Risk Heatmap - Severity x Occurrence"),
        ]):
            fig = chart_fn()
            tmp_path = os.path.join(tmp_dir, f"chart_{idx}.png")
            try:
                fig.savefig(tmp_path, dpi=150, bbox_inches="tight")
            finally:
                plt.close(fig)
            # Call via the module global so tests can monkeypatch this seam.
            _pdf_chart_page_from_file(pdf, tmp_path, title)
    # TemporaryDirectory removes tmp_dir and its contents on exit, even on exception.

    return bytes(pdf.output())


# ---------------------------------------------------------------------------
# PDF helpers — FMEA layout over the shared renderer
# ---------------------------------------------------------------------------

def _flag_str(row: pd.Series) -> str:
    parts = []
    if row.get("Flag_High_RPN"):
        parts.append("High RPN")
    if row.get("Flag_High_Severity"):
        parts.append("Sev>=9")
    if row.get("Flag_Action_Priority_H"):
        parts.append("AP-H")
    return ", ".join(parts) if parts else "-"


def _pdf_row_values(row: pd.Series) -> list[str]:
    return [
        str(int(row["ID"]))              if "ID"         in row.index else "",
        safe_text(str(row.get("Process_Step", ""))[:22]),
        safe_text(str(row.get("Failure_Mode", ""))[:32]),
        str(int(row["Severity"]))        if "Severity"   in row.index else "",
        str(int(row["Occurrence"]))      if "Occurrence" in row.index else "",
        str(int(row["Detection"]))       if "Detection"  in row.index else "",
        str(int(row["RPN"]))             if "RPN"        in row.index else "",
        safe_text(str(row.get("AP", "-"))) if "AP"       in row.index else "-",
        safe_text(_row_tier(row)),
        safe_text(str(row.get("_flags", "-"))[:38]),
    ]


def _pdf_row_rgb(row: pd.Series) -> tuple[int, int, int]:
    return TIER_RGB.get(_row_tier(row), (255, 255, 255))


def _pdf_page1(pdf: Any, df: pd.DataFrame) -> None:
    pdf.add_page()

    # Title bar
    pdf.set_font("Helvetica", "B", 16)
    pdf.set_fill_color(44, 62, 80)
    pdf.set_text_color(255, 255, 255)
    pdf.cell(0, 10, "FMEA Risk Analysis Report",  # ASCII-safe title
             new_x="LMARGIN", new_y="NEXT", align="C", fill=True)
    pdf.ln(2)

    # Sub-header
    pdf.set_font("Helvetica", "", 9)
    pdf.set_text_color(80, 80, 80)
    pdf.cell(
        0, 5,
        f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}   |   "
        "AIAG FMEA-4 (4th Ed.) + AIAG/VDA FMEA Handbook (5th Ed., 2019)",
        new_x="LMARGIN", new_y="NEXT", align="C",
    )
    pdf.ln(3)

    # Summary metrics
    metrics = [
        ("Total Modes",       len(df)),
        ("Red",               int((df["Risk_Tier"] == "Red").sum())    if "Risk_Tier"               in df.columns else 0),
        ("Yellow",            int((df["Risk_Tier"] == "Yellow").sum()) if "Risk_Tier"               in df.columns else 0),
        ("Green",             int((df["Risk_Tier"] == "Green").sum())  if "Risk_Tier"               in df.columns else 0),
        ("High RPN",          int(df["Flag_High_RPN"].sum())           if "Flag_High_RPN"           in df.columns else 0),
        ("Severity >= 9",     int(df["Flag_High_Severity"].sum())      if "Flag_High_Severity"      in df.columns else 0),
        ("Action Priority H", int(df["Flag_Action_Priority_H"].sum())  if "Flag_Action_Priority_H"  in df.columns else 0),
    ]
    cell_w = 277 / len(metrics)

    pdf.set_font("Helvetica", "B", 9)
    pdf.set_text_color(44, 62, 80)
    for label, _ in metrics:
        pdf.set_fill_color(240, 243, 246)
        pdf.cell(cell_w, 8, label, border=1, align="C", fill=True)
    pdf.ln()

    pdf.set_font("Helvetica", "B", 11)
    for _, value in metrics:
        pdf.cell(cell_w, 8, str(value), border=1, align="C", fill=False)
    pdf.ln(5)

    # Ranked table (shared renderer handles the repeating header + page breaks).
    df2 = df.copy()
    df2["_flags"] = df2.apply(_flag_str, axis=1)
    render_table(
        pdf, df2,
        columns=_PDF_TABLE_COLS,
        row_values=_pdf_row_values,
        row_rgb=_pdf_row_rgb,
    )


def _pdf_chart_page_from_file(pdf: Any, png_path: str, title: str) -> None:
    """Embed a pre-rendered PNG file as a new PDF page (kept as a patchable seam)."""
    add_image_page(pdf, png_path, title)
