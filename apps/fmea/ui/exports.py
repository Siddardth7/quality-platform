"""
ui/exports.py
Export button rendering with lazy caching and error isolation.
"""
from __future__ import annotations

import pandas as pd
import streamlit as st

from fmea_app._logging import get_logger
from fmea_app.exporter import export_csv, export_excel, export_pdf
from ui import df_content_hash

logger = get_logger(__name__)


def _export_cache_key(
    df: pd.DataFrame,
    rpn_min: int,
    sev9_only: bool,
    process_steps: list[str],
    export_type: str,
) -> tuple:
    df_hash = df_content_hash(df)
    return (df_hash, rpn_min, sev9_only, tuple(sorted(process_steps)), export_type)


def render_export_buttons(
    df: pd.DataFrame,
    rpn_min: int,
    sev9_only: bool,
    process_steps: list[str],
) -> None:
    st.subheader("📥  Export Report")
    col_xl, col_pdf, col_csv, _ = st.columns([1, 1, 1, 3])

    # Excel
    xl_key = _export_cache_key(df, rpn_min, sev9_only, process_steps, "excel")
    if st.session_state.get("_xl_cache_key") != xl_key:
        with st.spinner("Building Excel report…"):
            try:
                st.session_state["_xl_bytes"] = export_excel(df)
                st.session_state["_xl_cache_key"] = xl_key
            except (ValueError, KeyError, OSError, RuntimeError) as exc:
                logger.exception("Excel export failed")
                st.session_state["_xl_bytes"] = None
                st.session_state["_xl_cache_key"] = xl_key
                st.warning(f"Excel export unavailable: {exc}")

    with col_xl:
        xl_bytes = st.session_state.get("_xl_bytes")
        st.download_button(
            label="📊  Download Excel",
            data=xl_bytes or b"",
            file_name="fmea_analysis.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True,
            disabled=xl_bytes is None,
            help="Color-coded 2-sheet workbook with metadata summary",
        )

    # PDF
    pdf_key = _export_cache_key(df, rpn_min, sev9_only, process_steps, "pdf")
    if st.session_state.get("_pdf_cache_key") != pdf_key:
        with st.spinner("Building PDF report…"):
            try:
                pdf_data = export_pdf(df) if not df.empty else None
                st.session_state["_pdf_bytes"] = pdf_data
                st.session_state["_pdf_cache_key"] = pdf_key
            except (ValueError, KeyError, OSError, RuntimeError) as exc:
                logger.exception("PDF export failed")
                st.session_state["_pdf_bytes"] = None
                st.session_state["_pdf_cache_key"] = pdf_key
                st.warning(f"PDF export unavailable: {exc}")

    with col_pdf:
        pdf_bytes = st.session_state.get("_pdf_bytes")
        st.download_button(
            label="📄  Download PDF",
            data=pdf_bytes or b"",
            file_name="fmea_report.pdf",
            mime="application/pdf",
            use_container_width=True,
            disabled=pdf_bytes is None,
            help="3-page A4 landscape: table + Pareto + Heatmap",
        )

    # CSV
    with col_csv:
        st.download_button(
            label="📋  Download CSV",
            data=export_csv(df),
            file_name="fmea_analysis.csv",
            mime="text/csv",
            use_container_width=True,
            help="Full analyzed dataset with all calculated columns",
        )
