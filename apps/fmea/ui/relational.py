"""
ui/relational.py
Relational hierarchy view + action tracking UI (W05-5).

Thin Streamlit rendering over the shared relational model. The testable logic —
building the model from the uploaded flat frame (`rpn_engine.dataframe_to_relational`)
and attaching user-entered actions (`attach_actions` here) — is kept separate from
the `render_*` widgets, since Streamlit pages are excluded from the coverage bar.
"""
from __future__ import annotations

from datetime import date
from typing import Any

import pandas as pd
import pydantic
import streamlit as st
from quality_core.schema import Action, ActionStatus, RelationalFMEA

from fmea_app.exporter import export_csv, export_excel, export_pdf
from fmea_app.rpn_engine import relational_to_dataframe, run_pipeline_relational
from ui import df_content_hash

_STATUSES = [s.value for s in ActionStatus]
_EDITABLE = ["Owner", "Status", "Due", "S_After", "O_After", "D_After"]
_READONLY = ["ID", "Failure_Mode", "Effect", "Severity", "Occurrence", "Detection"]


# ---------------------------------------------------------------------------
# Pure logic (unit-tested; no Streamlit)
# ---------------------------------------------------------------------------

def _opt_int(value: Any) -> int | None:
    """A cell from the editor's number columns → an int rating or None if blank."""
    if value is None or (not isinstance(value, str) and pd.isna(value)):
        return None
    return int(value)


def _opt_due(value: Any) -> date | None:
    """A cell from the editor's date column → a date or None. Action parses str/date."""
    if value is None or (not isinstance(value, (str, date)) and pd.isna(value)):
        return None
    return value


def attach_actions(model: RelationalFMEA, edited: pd.DataFrame) -> RelationalFMEA:
    """Attach `Action`s from an edited action table to the model's links by row ID.

    A row whose ``Owner`` is blank records no action. Raises ``ValueError`` with a
    row-addressed message if an action's fields are invalid (bad rating, status,
    or date), so the caller can surface it. Every link's action is (re)assigned
    from the current edit — so the call is idempotent and clears an action when its
    owner is removed, even though Streamlit reuses the same model across reruns.
    """
    by_id: dict[int, Action] = {}
    for _, row in edited.iterrows():
        owner = str(row.get("Owner") or "").strip()
        if not owner:
            continue
        rid = int(row["ID"])
        status_val = str(row.get("Status") or ActionStatus.OPEN.value)
        if status_val not in _STATUSES:
            raise ValueError(f"Row ID {rid}, 'Status': {status_val!r} is not a valid status")
        try:
            by_id[rid] = Action(
                owner=owner,
                status=ActionStatus(status_val),
                due=_opt_due(row.get("Due")),
                s_after=_opt_int(row.get("S_After")),
                o_after=_opt_int(row.get("O_After")),
                d_after=_opt_int(row.get("D_After")),
            )
        except pydantic.ValidationError as exc:
            first = exc.errors()[0]
            field = str(first.get("loc", ("action",))[0])
            raise ValueError(f"Row ID {rid}, '{field}': {first.get('msg', 'invalid value')}") from exc

    # Assign every link (None where no owner) so a removed owner clears its action.
    for function in model.functions:
        for fm in function.failure_modes:
            for link in fm.links:
                link.action = by_id.get(link.row_id)
    return RelationalFMEA(functions=model.functions)  # revalidate with actions attached


# ---------------------------------------------------------------------------
# Rendering (thin; Streamlit only)
# ---------------------------------------------------------------------------

def render_hierarchy(model: RelationalFMEA) -> None:
    """Draw the Function → Failure Mode → Effect/Cause/Control tree (read-only)."""
    st.caption(
        "Function → Failure Mode → Effect / Cause / Control — auto-built from your "
        "data via the relational adapter. Severity lives on the Effect, Occurrence "
        "on the Cause, Detection on the Control (AIAG/VDA)."
    )
    for function in model.functions:
        header = f"🔧  {function.description}  ·  {function.process_step} / {function.component}"
        with st.expander(header, expanded=False):
            for fm in function.failure_modes:
                st.markdown(f"**Failure mode — {fm.description}**")
                col_e, col_c, col_ct = st.columns(3)
                with col_e:
                    st.markdown("*Effects (S)*")
                    for effect in fm.effects:
                        st.markdown(f"- {effect.description} · **S{effect.severity}**")
                with col_c:
                    st.markdown("*Causes (O)*")
                    for cause in fm.causes:
                        st.markdown(f"- {cause.description} · **O{cause.occurrence}**")
                with col_ct:
                    st.markdown("*Controls (D)*")
                    for control in fm.controls:
                        st.markdown(f"- {control.description} · **D{control.detection}**")
                st.divider()


def _seed_editor(model: RelationalFMEA) -> pd.DataFrame:
    base = relational_to_dataframe(model)[
        ["ID", "Failure_Mode", "Effect", "Severity", "Occurrence", "Detection"]
    ].copy()
    base["Owner"] = ""
    base["Status"] = ActionStatus.OPEN.value
    base["Due"] = None
    base["S_After"] = pd.NA
    base["O_After"] = pd.NA
    base["D_After"] = pd.NA
    return base


def _action_editor_config() -> dict[str, Any]:
    return {
        "Failure_Mode": st.column_config.TextColumn("Failure Mode"),
        "Status": st.column_config.SelectboxColumn("Status", options=_STATUSES, required=True),
        "Due": st.column_config.DateColumn("Due"),
        "S_After": st.column_config.NumberColumn("S'", min_value=1, max_value=10, step=1),
        "O_After": st.column_config.NumberColumn("O'", min_value=1, max_value=10, step=1),
        "D_After": st.column_config.NumberColumn("D'", min_value=1, max_value=10, step=1),
        "Severity": st.column_config.NumberColumn("S"),
        "Occurrence": st.column_config.NumberColumn("O"),
        "Detection": st.column_config.NumberColumn("D"),
    }


def render_action_tracker(model: RelationalFMEA) -> None:
    """Editor for per-failure actions + a before→after effectiveness summary."""
    st.caption(
        "Record an action per failure mode: set an **Owner**, status, optional due "
        "date, and any re-rated **S'/O'/D'**. Leave Owner blank for rows with no "
        "action yet. Revised RPN / Action Priority update below."
    )
    edited = st.data_editor(
        _seed_editor(model),
        key="fmea_action_editor",
        column_config=_action_editor_config(),
        disabled=_READONLY,
        hide_index=True,
        use_container_width=True,
    )

    try:
        model_with_actions = attach_actions(model, edited)
    except ValueError as exc:
        st.error(f"**Invalid action:** {exc}")
        return

    scored = run_pipeline_relational(model_with_actions)
    if "Action_Owner" not in scored.columns:
        st.info("No actions recorded yet — add an Owner above to track effectiveness.")
        return

    actions = scored[scored["Action_Owner"].astype(str).str.len() > 0]
    st.divider()
    st.subheader("🎯  Action Effectiveness")
    total_delta = int(actions["RPN_Delta"].sum())
    c1, c2 = st.columns([1, 3])
    c1.metric("Total RPN change", total_delta, help="Sum of revised − initial RPN across all actions")
    summary = actions[[
        "ID", "Failure_Mode", "Action_Owner", "Action_Status",
        "RPN", "RPN_Revised", "RPN_Delta", "AP_Revised",
    ]].rename(columns={
        "Action_Owner": "Owner", "Action_Status": "Status",
        "RPN": "RPN (before)", "RPN_Revised": "RPN (after)",
        "RPN_Delta": "Δ RPN", "AP_Revised": "AP (after)",
    })
    st.dataframe(summary.reset_index(drop=True), use_container_width=True, hide_index=True)

    st.divider()
    _render_action_exports(scored)


def _render_action_exports(scored: pd.DataFrame) -> None:
    st.subheader("📥  Export (with action tracking)")
    key = df_content_hash(scored)
    if st.session_state.get("_action_export_key") != key:
        with st.spinner("Building action-tracking reports…"):
            try:
                st.session_state["_action_xl"] = export_excel(scored)
                st.session_state["_action_pdf"] = export_pdf(scored)
            except (ValueError, KeyError, OSError, RuntimeError) as exc:
                st.session_state["_action_xl"] = None
                st.session_state["_action_pdf"] = None
                st.warning(f"Export unavailable: {exc}")
        st.session_state["_action_export_key"] = key

    xl = st.session_state.get("_action_xl")
    pdf = st.session_state.get("_action_pdf")
    col_xl, col_pdf, col_csv, _ = st.columns([1, 1, 1, 3])
    with col_xl:
        st.download_button(
            "📊  Excel", data=xl or b"", file_name="fmea_with_actions.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True, disabled=xl is None,
        )
    with col_pdf:
        st.download_button(
            "📄  PDF", data=pdf or b"", file_name="fmea_with_actions.pdf",
            mime="application/pdf", use_container_width=True, disabled=pdf is None,
        )
    with col_csv:
        st.download_button(
            "📋  CSV", data=export_csv(scored), file_name="fmea_with_actions.csv",
            mime="text/csv", use_container_width=True,
        )
