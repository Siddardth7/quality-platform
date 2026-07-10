"""
tests/test_relational_ui.py
Pure logic behind the W05-5 relational + action-tracking UI (the Streamlit
rendering itself is manually verified — pages are excluded from the coverage bar).

Covers `rpn_engine.dataframe_to_relational` (flat upload → relational model) and
`ui.relational.attach_actions` (an edited action table → actions attached to the
model's links), including the blank-row skip and invalid-input error path.
"""

from __future__ import annotations

from datetime import date

import pandas as pd
import pytest

from fmea_app.rpn_engine import (
    REQUIRED_COLUMNS,
    dataframe_to_relational,
    relational_to_dataframe,
    run_pipeline_relational,
)
from ui.relational import attach_actions

_ROWS = [
    dict(ID=1, Process_Step="Mix", Component="Resin", Function="Bond layers",
         Failure_Mode="Uncured", Effect="Delamination", Severity=9,
         Cause="Low temperature", Occurrence=8, Current_Control="Oven", Detection=5),
    dict(ID=2, Process_Step="Seal", Component="Edge", Function="Seal edge",
         Failure_Mode="Void", Effect="Leak", Severity=6,
         Cause="Gap", Occurrence=3, Current_Control="Visual", Detection=7),
]


def _flat_df() -> pd.DataFrame:
    return pd.DataFrame(_ROWS, columns=REQUIRED_COLUMNS)


def _edited(**overrides: dict[str, object]) -> pd.DataFrame:
    """Simulate what st.data_editor returns: the seed rows + action columns."""
    df = relational_to_dataframe(dataframe_to_relational(_flat_df()))[
        ["ID", "Failure_Mode", "Effect", "Severity", "Occurrence", "Detection"]
    ].copy()
    df["Owner"] = ""
    df["Status"] = "Open"
    df["Due"] = None
    df["S_After"] = pd.NA
    df["O_After"] = pd.NA
    df["D_After"] = pd.NA
    for rid, fields in overrides.items():
        df.loc[df["ID"] == int(rid), list(fields.keys())] = list(fields.values())
    return df


# --- dataframe_to_relational --------------------------------------------------


def test_dataframe_to_relational_round_trips() -> None:
    model = dataframe_to_relational(_flat_df())
    assert relational_to_dataframe(model)["ID"].tolist() == [1, 2]
    assert model.functions[0].failure_modes[0].effects[0].severity == 9


# --- attach_actions -----------------------------------------------------------


def test_attach_action_flows_to_effectiveness() -> None:
    edited = _edited(**{"1": {"Owner": "QE", "Status": "Closed",
                              "Due": date(2026, 8, 1), "O_After": 1}})
    model = attach_actions(dataframe_to_relational(_flat_df()), edited)
    link = model.functions[0].failure_modes[0].links[0]
    assert link.action is not None and link.action.owner == "QE"
    scored = run_pipeline_relational(model)
    row1 = scored[scored["ID"] == 1].iloc[0]
    assert row1["RPN_Revised"] == 45 and row1["RPN_Delta"] == -315


def test_blank_owner_records_no_action() -> None:
    model = attach_actions(dataframe_to_relational(_flat_df()), _edited())
    assert all(
        link.action is None
        for fn in model.functions for fm in fn.failure_modes for link in fm.links
    )


def test_invalid_rating_raises_row_addressed_error() -> None:
    edited = _edited(**{"1": {"Owner": "QE", "S_After": 11}})  # 11 is out of 1–10
    with pytest.raises(ValueError, match="Row ID 1"):
        attach_actions(dataframe_to_relational(_flat_df()), edited)


def test_removing_owner_clears_a_previously_attached_action() -> None:
    # Streamlit reuses one model across reruns; clearing the owner must clear the
    # action, not leave a stale one from the previous edit.
    model = dataframe_to_relational(_flat_df())
    model = attach_actions(model, _edited(**{"1": {"Owner": "QE", "O_After": 1}}))
    assert model.functions[0].failure_modes[0].links[0].action is not None
    model = attach_actions(model, _edited())  # owner cleared
    assert model.functions[0].failure_modes[0].links[0].action is None
