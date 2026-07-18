"""Control Plan page — FMEA ingest -> connector -> review/edit -> export.

Uploads a flat FMEA CSV (or loads the bundled demo) through the shared
validated-ingest boundary, adapts it to a relational FMEA, and calls
``controlplan_app.connector.build_control_plan`` to derive the Control Plan
rows. The derived plan is shown in an editable ``st.data_editor``; edits are
re-validated through the existing ``ControlPlanRow``/``ControlPlanDataset``
models (the trust boundary — edits are untrusted input) before any export.
Export is CSV/Excel/PDF via ``controlplan_app.exporter``, mirroring the FMEA
app's export UI.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, BinaryIO, cast

import pandas as pd
import pydantic
import streamlit as st
from quality_core.io import IngestError, TableSchema, load_table
from quality_core.schema import FMEADataset, FMEARow, RelationalFMEA, flat_to_relational

from controlplan_app.connector import build_control_plan
from controlplan_app.exporter import export_csv, export_excel, export_pdf
from controlplan_app.schema import ControlPlanDataset, ControlPlanRow

_DATA_DIR = Path(__file__).resolve().parents[2] / "data"
TEMPLATE_PATH = _DATA_DIR / "fmea_input_template.csv"
DEMO_PATH = _DATA_DIR / "composite_panel_fmea_demo.csv"

#: FMEA flat-CSV ingest contract, reused from the FMEA app's own boundary
#: (``load_table`` + ``FMEARow``/``FMEADataset``) — see spec "FMEA ingest".
FMEA_INPUT_SCHEMA = TableSchema(
    name="FMEA",
    row_model=FMEARow,
    dataset_model=FMEADataset,
    template_hint="data/fmea_input_template.csv",
)

#: Session-state key holding the current (possibly edited) plan DataFrame, so
#: the edit survives a rerun and is what actually gets exported.
_PLAN_STATE_KEY = "_controlplan_plan_df"


def load_uploaded_fmea(source: str | BinaryIO) -> RelationalFMEA:
    """Route an uploaded/demo flat FMEA CSV through the shared ingest boundary.

    Raises :class:`IngestError` (a ``ValueError`` subclass) on a malformed or
    invalid FMEA CSV — the page catches it and calls ``st.error``.
    """
    df = load_table(source, FMEA_INPUT_SCHEMA)
    dataset = FMEADataset(
        rows=[
            FMEARow(**cast("dict[str, Any]", {k: (None if pd.isna(v) else v) for k, v in rec.items()}))
            for rec in df.to_dict("records")
        ]
    )
    return flat_to_relational(dataset)


def validate_edited_plan(edited: pd.DataFrame) -> ControlPlanDataset:
    """Re-validate an edited plan DataFrame at the trust boundary.

    Raises ``pydantic.ValidationError`` on a row/dataset rule violation (blank
    cell, ``usl <= lsl``, out-of-band target, invalid chart, duplicate
    characteristic) — the caller surfaces the first error and blocks export.
    """
    rows = [
        ControlPlanRow(
            **cast(
                "dict[str, Any]",
                {key: (None if pd.isna(value) else value) for key, value in record.items()},
            )
        )
        for record in edited.to_dict("records")
    ]
    return ControlPlanDataset(rows=rows)


def _plan_to_df(dataset: ControlPlanDataset) -> pd.DataFrame:
    return pd.DataFrame([row.model_dump() for row in dataset.rows])


def _first_error_message(exc: pydantic.ValidationError) -> str:
    first = exc.errors()[0]
    column = ".".join(str(part) for part in first.get("loc", ()))
    where = f"column '{column}'" if column else "dataset"
    msg = first.get("msg", "invalid value")
    for prefix in ("Value error, ", "Assertion failed, "):
        msg = msg.removeprefix(prefix)
    return f"{where}: {msg}"


def render_control_plan() -> None:
    st.title("Control Plan")
    st.caption(
        "Load an FMEA to derive a draft Control Plan, review/edit the generated "
        "rows, then export."
    )

    with st.sidebar:
        st.header("Load FMEA")
        upload = st.file_uploader("Upload FMEA CSV", type=["csv"])
        use_demo = st.button("Load demo FMEA")
        st.download_button(
            "Download FMEA CSV template",
            data=TEMPLATE_PATH.read_bytes(),
            file_name="fmea_input_template.csv",
            mime="text/csv",
        )

    source: str | BinaryIO | None = None
    if upload is not None:
        source = upload
    elif use_demo:
        source = str(DEMO_PATH)

    if source is None and _PLAN_STATE_KEY not in st.session_state:
        st.info(
            "Upload a flat FMEA CSV, or click 'Load demo FMEA', to derive a draft "
            "Control Plan."
        )
        return

    if source is not None:
        try:
            relational = load_uploaded_fmea(source)
        except IngestError as exc:
            st.error(str(exc))
            st.stop()
        plan = build_control_plan(relational)
        st.session_state[_PLAN_STATE_KEY] = _plan_to_df(plan)

    plan_df = cast("pd.DataFrame", st.session_state[_PLAN_STATE_KEY])

    st.subheader("Review / edit the derived Control Plan")
    edited_df = st.data_editor(
        plan_df,
        num_rows="dynamic",
        column_config={
            "recommended_chart": st.column_config.SelectboxColumn(
                "recommended_chart",
                options=["Xbar-R", "Xbar-S", "I-MR", "p", "c", "u"],
            ),
        },
        key="_controlplan_editor",
    )
    st.session_state[_PLAN_STATE_KEY] = edited_df

    if edited_df.empty:
        st.info("No rows to export — add a row or reload an FMEA.")
        return

    try:
        validated = validate_edited_plan(edited_df)
    except pydantic.ValidationError as exc:
        st.error(f"Cannot export: {_first_error_message(exc)}")
        return

    st.success(f"{len(validated.rows)} row(s) validated and ready to export.")

    col1, col2, col3 = st.columns(3)
    with col1:
        st.download_button(
            "Download CSV",
            data=export_csv(validated),
            file_name="control_plan.csv",
            mime="text/csv",
        )
    with col2:
        st.download_button(
            "Download Excel",
            data=export_excel(validated),
            file_name="control_plan.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
    with col3:
        st.download_button(
            "Download PDF",
            data=export_pdf(validated),
            file_name="control_plan.pdf",
            mime="application/pdf",
        )
