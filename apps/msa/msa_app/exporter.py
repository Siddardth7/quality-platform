"""
exporter.py
Measurement System Analysis — Export Layer

MSA-specific export *config* (which fields, metadata, layout) composed over the
shared, app-agnostic primitives in ``quality_core.io.export`` (CSV/formula-injection
escaping, openpyxl styling, fpdf2 table rendering) — the same pattern SPC and the
Control Plan already use.

One report kind — a Gage R&R study — rendered four ways:

    Study CSV      — the validated study frame, round-trippable (matches Control
                     Plan's ``export_csv(validated)``).
    Results CSV    — a flat one-row table of the computed metrics/verdict.
    Excel (.xlsx)  — a results summary sheet + the study data sheet.
    PDF            — title + %GRR/ndc/verdict strip + a metric detail table.

Builders take a frozen report dataclass (the values the page has already computed)
and return raw bytes suitable for ``st.download_button``.
"""

from __future__ import annotations

import io
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

import openpyxl
import pandas as pd
from quality_core.io.export import (
    export_csv as _core_export_csv,
)
from quality_core.io.export import (
    fmt,
    fmt_opt,
    generated_line,
    now,
    pdf_subheader,
    pdf_summary_cells,
    pdf_title,
    render_table,
    safe_text,
    sanitize_for_export,
    write_keyvalue_sheet,
    write_table_sheet,
)

from msa_app import __version__

_TOOL_VERSION = __version__
_ENGINEERING_REF = "AIAG MSA Reference Manual, 4th Ed."

_STUDY_COLUMNS = ["part", "appraiser", "trial", "measurement"]

_WHITE_RGB = (255, 255, 255)

# Verdict -> plain-English interpretation. Single source of truth: both the page
# (results display) and this exporter pull from here, so the sentence never
# drifts from the AIAG thresholds in gage_rr_engine.py / ASSUMPTIONS_LOG.md.
VERDICT_SENTENCES: dict[str, str] = {
    "Accept": (
        "Accept — ndc >= 5 and %GRR < 10%. Measurement system is adequate for the "
        "intended use."
    ),
    "Marginal": (
        "Marginal — ndc 2-4 or %GRR 10-30%. Acceptable for some uses; consider an "
        "improvement plan."
    ),
    "Reject": (
        "Reject — ndc < 2 or %GRR > 30%. Measurement system is inadequate and must "
        "be improved."
    ),
}
_VERDICT_FALLBACK = "Unrecognized verdict — review the study inputs."


def verdict_sentence(verdict: str) -> str:
    """The plain-English interpretation for a verdict (falls back for unknown values)."""
    return VERDICT_SENTENCES.get(verdict, _VERDICT_FALLBACK)


# ===========================================================================
# Report input
# ===========================================================================


@dataclass(frozen=True)
class GageStudyReport:
    """Everything the Gage R&R page already computed."""

    study: pd.DataFrame  # the validated study frame (part/appraiser/trial/measurement)
    results: Mapping[str, Any]  # compute_gage_rr(...) return dict
    usl: float | None
    lsl: float | None


# ===========================================================================
# Formatting helpers
# ===========================================================================


def _fmt_pct(value: float) -> str:
    return f"{value:.2f}%"


def _fmt_pct_opt(value: float | None) -> str:
    return "N/A" if value is None else f"{value:.2f}%"


# ===========================================================================
# Detail rows (shared by Excel + PDF)
# ===========================================================================


def _detail_rows(report: GageStudyReport) -> list[tuple[str, object]]:
    """Metric/value rows shared by the Excel summary sheet and the PDF detail table."""
    results = report.results
    verdict = str(results["verdict"])
    return [
        ("EV (Repeatability)", fmt(results["ev"], precision=6)),
        ("AV (Reproducibility)", fmt(results["av"], precision=6)),
        ("GR&R", fmt(results["grr"], precision=6)),
        ("PV (Part Variation)", fmt(results["pv"], precision=6)),
        ("TV (Total Variation)", fmt(results["tv"], precision=6)),
        ("%EV (Study)", _fmt_pct(results["pev_study"])),
        ("%AV (Study)", _fmt_pct(results["pav_study"])),
        ("%GRR (Study)", _fmt_pct(results["pgrr_study"])),
        ("%PV (Study)", _fmt_pct(results["ppv_study"])),
        ("%EV (Tolerance)", _fmt_pct_opt(results["pev_tolerance"])),
        ("%AV (Tolerance)", _fmt_pct_opt(results["pav_tolerance"])),
        ("%GRR (Tolerance)", _fmt_pct_opt(results["pgrr_tolerance"])),
        ("%PV (Tolerance)", _fmt_pct_opt(results["ppv_tolerance"])),
        ("ndc", str(results["ndc"])),
        ("Verdict", verdict),
        ("Verdict Interpretation", verdict_sentence(verdict)),
        ("Parts", str(results["n_parts"])),
        ("Appraisers", str(results["n_appraisers"])),
        ("Trials", str(results["n_trials"])),
        ("USL", fmt_opt(report.usl, precision=6)),
        ("LSL", fmt_opt(report.lsl, precision=6)),
        ("Mean", fmt(results["mean"], precision=6)),
        ("Method", str(results["method"])),
        ("Method Limitation", str(results["method_note"])),
    ]


def _summary_rows(report: GageStudyReport) -> list[tuple[str, object]]:
    return [
        ("Generated", now()),
        ("Tool Version", _TOOL_VERSION),
        ("Engineering Ref", _ENGINEERING_REF),
        ("", ""),
        *_detail_rows(report),
    ]


# ===========================================================================
# CSV exports (R1: study data + flat results, two separate downloads)
# ===========================================================================


def export_csv(report: GageStudyReport) -> bytes:
    """Export the validated study frame to UTF-8 CSV bytes (injection-escaped)."""
    return _core_export_csv(sanitize_for_export(report.study[_STUDY_COLUMNS]))


def export_results_csv(report: GageStudyReport) -> bytes:
    """Export a flat, one-row results table (EV/AV/GRR/PV/TV, %EV/%AV/%GRR/%PV on both
    the study-variation and tolerance bases, ndc, verdict).

    Values are app-formatted numbers/strings computed by the engine, not user
    input, so (matching the SPC exporter's convention) they are not routed
    through :func:`sanitize_for_export`.
    """
    results = report.results
    verdict = str(results["verdict"])
    row = {
        "EV": fmt(results["ev"], precision=6),
        "AV": fmt(results["av"], precision=6),
        "GRR": fmt(results["grr"], precision=6),
        "PV": fmt(results["pv"], precision=6),
        "TV": fmt(results["tv"], precision=6),
        "%EV Study": _fmt_pct(results["pev_study"]),
        "%AV Study": _fmt_pct(results["pav_study"]),
        "%GRR Study": _fmt_pct(results["pgrr_study"]),
        "%PV Study": _fmt_pct(results["ppv_study"]),
        "%EV Tolerance": _fmt_pct_opt(results["pev_tolerance"]),
        "%AV Tolerance": _fmt_pct_opt(results["pav_tolerance"]),
        "%GRR Tolerance": _fmt_pct_opt(results["pgrr_tolerance"]),
        "%PV Tolerance": _fmt_pct_opt(results["ppv_tolerance"]),
        "ndc": results["ndc"],
        "Verdict": verdict,
        "Verdict Interpretation": verdict_sentence(verdict),
        "Method": results["method"],
        "Method Limitation": results["method_note"],
    }
    return _core_export_csv(pd.DataFrame([row]))


# ===========================================================================
# Excel + PDF exports (full results report)
# ===========================================================================


def export_excel(report: GageStudyReport) -> bytes:
    """Excel workbook: a results/metadata summary sheet + the study data sheet."""
    wb = openpyxl.Workbook()
    ws = wb.active
    assert ws is not None  # a freshly created workbook always has an active sheet
    write_keyvalue_sheet(ws, _summary_rows(report), title="Summary")
    write_table_sheet(
        wb.create_sheet("Study Data"),
        sanitize_for_export(report.study[_STUDY_COLUMNS]),
        title="Study Data",
        columns=_STUDY_COLUMNS,
        col_widths={"part": 14, "appraiser": 14, "trial": 10, "measurement": 16},
    )

    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()


def export_pdf(report: GageStudyReport) -> bytes:
    """PDF report: title, %GRR/ndc/verdict strip, and a metric detail table."""
    from fpdf import FPDF

    results = report.results
    pdf = FPDF(orientation="P", unit="mm", format="A4")
    pdf.set_auto_page_break(auto=True, margin=12)
    pdf.set_margins(10, 10, 10)
    pdf.add_page()

    pdf_title(pdf, "MSA Gage R&R Report")
    pdf_subheader(pdf, generated_line(_ENGINEERING_REF))
    pdf_summary_cells(
        pdf,
        [
            ("%GRR (Study)", _fmt_pct(results["pgrr_study"])),
            ("%GRR (Tol)", _fmt_pct_opt(results["pgrr_tolerance"])),
            ("ndc", str(results["ndc"])),
            ("Verdict", str(results["verdict"])),
        ],
    )

    details = pd.DataFrame(_detail_rows(report), columns=["Metric", "Value"])
    render_table(
        pdf,
        details,
        columns=[("Metric", 90), ("Value", 100)],
        row_values=lambda r: [safe_text(str(r["Metric"])), safe_text(str(r["Value"]))],
        row_rgb=lambda r: _WHITE_RGB,
    )
    return bytes(pdf.output())
