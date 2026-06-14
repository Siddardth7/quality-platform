"""
tests/test_rpn_engine.py
Unit tests for src/rpn_engine.py

Test coverage (per EXECUTION_ROADMAP.md W1D6 requirements):
    TC-01  RPN calculation: 9 × 3 × 4 = 108
    TC-02  Severity = 9 triggers Flag_High_Severity and Flag_Action_Priority_H
    TC-03  Severity = 1 (with low O/D) triggers no flags
    TC-04  Missing required column raises ValueError

Extended coverage:
    TC-05  Flag_High_RPN triggers when RPN > 100
    TC-06  Flag_Action_Priority_H triggers on RPN ≥ 200 alone (Severity < 9)
    TC-07  Risk_Tier assignment: Red / Yellow / Green logic
    TC-08  rank_by_rpn sorts descending by RPN
    TC-09  run_pipeline produces correct end-to-end output
    TC-10  validate_input rejects empty DataFrame
    TC-11  validate_input rejects out-of-range S/O/D scores
    TC-12  flag_critical raises KeyError if RPN column missing
    TC-13  rank_by_rpn raises KeyError if upstream columns missing

Run with:
    python -m pytest tests/ -v
"""

import numpy as np
import pandas as pd
import pydantic
import pytest

from src.rpn_engine import (
    calculate_rpn,
    flag_critical,
    rank_by_rpn,
    run_pipeline,
    validate_input,
)
from src.schema import FMEADataset, FMEARow

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_row(
    id_val: int = 1,
    severity: int = 5,
    occurrence: int = 3,
    detection: int = 4,
    process_step: str = "Layup",
    component: str = "Ply Stack",
    function: str = "Transfer load",
    failure_mode: str = "Ply misalignment",
    effect: str = "Reduced strength",
    cause: str = "Operator error",
    current_control: str = "Visual inspection",
) -> dict:
    """Return a single valid FMEA row as a dict."""
    return {
        "ID": id_val,
        "Process_Step": process_step,
        "Component": component,
        "Function": function,
        "Failure_Mode": failure_mode,
        "Effect": effect,
        "Severity": severity,
        "Cause": cause,
        "Occurrence": occurrence,
        "Current_Control": current_control,
        "Detection": detection,
    }


def _make_df(*rows: dict) -> pd.DataFrame:
    """Build a DataFrame from one or more row dicts."""
    return pd.DataFrame(list(rows))


# ---------------------------------------------------------------------------
# TC-01 — RPN calculation: 9 × 3 × 4 = 108
# ---------------------------------------------------------------------------

def test_tc01_rpn_calculation():
    """RPN must equal Severity × Occurrence × Detection (9 × 3 × 4 = 108)."""
    df = _make_df(_make_row(severity=9, occurrence=3, detection=4))
    validate_input(df)
    result = calculate_rpn(df)
    assert result.loc[0, "RPN"] == 108, (
        f"Expected RPN=108, got {result.loc[0, 'RPN']}"
    )


# ---------------------------------------------------------------------------
# TC-02 — Severity = 9 triggers Flag_High_Severity and Flag_Action_Priority_H
# ---------------------------------------------------------------------------

def test_tc02_severity_9_triggers_flags():
    """Severity ≥ 9 must set Flag_High_Severity=True and Flag_Action_Priority_H=True."""
    # Use low O/D so RPN stays below 200 — the Severity rule must do the work
    df = _make_df(_make_row(severity=9, occurrence=2, detection=2))
    validate_input(df)
    df = calculate_rpn(df)   # RPN = 9 × 2 × 2 = 36
    df = flag_critical(df)

    assert df.loc[0, "Flag_High_Severity"], (
        "Flag_High_Severity should be True for Severity=9"
    )
    assert df.loc[0, "Flag_Action_Priority_H"], (
        "Flag_Action_Priority_H should be True for Severity=9 (safety override)"
    )
    # RPN = 36 — below 100 threshold, so Flag_High_RPN must be False
    assert not df.loc[0, "Flag_High_RPN"], (
        "Flag_High_RPN should be False when RPN=36 (< 100)"
    )


# ---------------------------------------------------------------------------
# TC-03 — Severity = 1 (with low O/D) triggers no flags
# ---------------------------------------------------------------------------

def test_tc03_low_severity_no_flags():
    """All-low scores (S=1, O=1, D=1 → RPN=1) must trigger zero flags."""
    df = _make_df(_make_row(severity=1, occurrence=1, detection=1))
    validate_input(df)
    df = calculate_rpn(df)    # RPN = 1
    df = flag_critical(df)

    assert not df.loc[0, "Flag_High_RPN"], "Flag_High_RPN should be False (RPN=1)"
    assert not df.loc[0, "Flag_High_Severity"], "Flag_High_Severity should be False (S=1)"
    assert not df.loc[0, "Flag_Action_Priority_H"], "Flag_Action_Priority_H should be False (S=1, RPN=1)"


# ---------------------------------------------------------------------------
# TC-04 — Missing required column raises ValueError
# ---------------------------------------------------------------------------

def test_tc04_missing_column_raises():
    """DataFrame missing 'Severity' column must raise ValueError."""
    row = _make_row(severity=5, occurrence=3, detection=4)
    del row["Severity"]   # remove required column
    df = pd.DataFrame([row])

    with pytest.raises(ValueError, match="Missing required column"):
        validate_input(df)


# ---------------------------------------------------------------------------
# TC-05 — Flag_High_RPN triggers when RPN > 100
# ---------------------------------------------------------------------------

def test_tc05_high_rpn_flag():
    """RPN > 100 must set Flag_High_RPN=True; RPN exactly = 100 must not."""
    # RPN = 5 × 5 × 5 = 125 → should flag
    df_high = _make_df(_make_row(severity=5, occurrence=5, detection=5))
    validate_input(df_high)
    df_high = calculate_rpn(df_high)
    df_high = flag_critical(df_high)
    assert df_high.loc[0, "Flag_High_RPN"], "Flag_High_RPN should be True for RPN=125"

    # RPN = 4 × 5 × 5 = 100 → boundary: > 100 rule means exactly 100 should NOT flag
    df_boundary = _make_df(_make_row(severity=4, occurrence=5, detection=5))
    validate_input(df_boundary)
    df_boundary = calculate_rpn(df_boundary)
    df_boundary = flag_critical(df_boundary)
    assert not df_boundary.loc[0, "Flag_High_RPN"], "Flag_High_RPN should be False for RPN=100 (rule is > 100)"


# ---------------------------------------------------------------------------
# TC-06 — Flag_Action_Priority_H triggers on RPN ≥ 200 alone
# ---------------------------------------------------------------------------

def test_tc06_action_priority_h_high_rpn():
    """RPN ≥ 200 alone (without Severity ≥ 9) must set Flag_Action_Priority_H=True."""
    # S=8 (below 9), O=5, D=5 → RPN = 200
    df = _make_df(_make_row(severity=8, occurrence=5, detection=5))
    validate_input(df)
    df = calculate_rpn(df)    # RPN = 200
    df = flag_critical(df)

    assert df.loc[0, "Flag_Action_Priority_H"], (
        "Flag_Action_Priority_H should be True when RPN=200 (threshold is ≥ 200)"
    )
    assert not df.loc[0, "Flag_High_Severity"], (
        "Flag_High_Severity should be False (Severity=8)"
    )


# ---------------------------------------------------------------------------
# TC-07 — Risk_Tier assignment
# ---------------------------------------------------------------------------

def test_tc07_risk_tier_assignment():
    """Red/Yellow/Green tiers must be assigned per RULE 4 thresholds."""
    rows = [
        _make_row(id_val=1, severity=8, occurrence=5, detection=4),   # RPN=160 → Red
        _make_row(id_val=2, severity=9, occurrence=1, detection=1),   # RPN=9, S=9 → Red (safety)
        _make_row(id_val=3, severity=5, occurrence=4, detection=4),   # RPN=80 → Yellow
        _make_row(id_val=4, severity=2, occurrence=3, detection=3),   # RPN=18 → Green
    ]
    df = _make_df(*rows)
    validate_input(df)
    df = calculate_rpn(df)
    df = flag_critical(df)
    df = rank_by_rpn(df)

    tier_map = dict(zip(df["ID"], df["Risk_Tier"]))
    assert tier_map[1] == "Red",    f"ID=1 (RPN=160) expected Red, got {tier_map[1]}"
    assert tier_map[2] == "Red",    f"ID=2 (S=9, RPN=9) expected Red, got {tier_map[2]}"
    assert tier_map[3] == "Yellow", f"ID=3 (RPN=80) expected Yellow, got {tier_map[3]}"
    assert tier_map[4] == "Green",  f"ID=4 (RPN=18) expected Green, got {tier_map[4]}"


# ---------------------------------------------------------------------------
# TC-08 — rank_by_rpn sorts descending by RPN
# ---------------------------------------------------------------------------

def test_tc08_ranking_order():
    """rank_by_rpn must return rows sorted RPN descending."""
    rows = [
        _make_row(id_val=1, severity=2, occurrence=2, detection=2),   # RPN=8
        _make_row(id_val=2, severity=8, occurrence=4, detection=5),   # RPN=160
        _make_row(id_val=3, severity=5, occurrence=4, detection=3),   # RPN=60
    ]
    df = _make_df(*rows)
    validate_input(df)
    df = calculate_rpn(df)
    df = flag_critical(df)
    df = rank_by_rpn(df)

    rpn_values = df["RPN"].tolist()
    assert rpn_values == sorted(rpn_values, reverse=True), (
        f"Expected descending RPN order, got {rpn_values}"
    )
    assert df.loc[0, "ID"] == 2, "Highest RPN row (ID=2, RPN=160) should be first"


# ---------------------------------------------------------------------------
# TC-09 — run_pipeline end-to-end
# ---------------------------------------------------------------------------

def test_tc09_run_pipeline_end_to_end():
    """run_pipeline must produce correct RPN, flags, tier, and sort order."""
    rows = [
        _make_row(id_val=1, severity=9, occurrence=4, detection=3),   # RPN=108, S=9 → Red
        _make_row(id_val=2, severity=3, occurrence=2, detection=2),   # RPN=12 → Green
    ]
    df = _make_df(*rows)
    result = run_pipeline(df)

    # RPN values
    rpn_map = dict(zip(result["ID"], result["RPN"]))
    assert rpn_map[1] == 108, f"Expected RPN=108 for ID=1, got {rpn_map[1]}"
    assert rpn_map[2] == 12,  f"Expected RPN=12 for ID=2, got {rpn_map[2]}"

    # ID=1 should be first (highest RPN)
    assert result.loc[0, "ID"] == 1, "ID=1 (RPN=108) should rank first"

    # Flags for ID=1
    row1 = result[result["ID"] == 1].iloc[0]
    assert row1["Flag_High_RPN"],          "ID=1 should have Flag_High_RPN=True"
    assert row1["Flag_High_Severity"],     "ID=1 should have Flag_High_Severity=True (S=9)"
    assert row1["Flag_Action_Priority_H"], "ID=1 should have Flag_Action_Priority_H=True"
    assert row1["Risk_Tier"] == "Red",     "ID=1 should be Red tier"

    # All clear for ID=2
    row2 = result[result["ID"] == 2].iloc[0]
    assert not row2["Flag_High_RPN"],          "ID=2 should have no flags"
    assert not row2["Flag_High_Severity"],     "ID=2 should have no severity flag"
    assert not row2["Flag_Action_Priority_H"], "ID=2 should have no action priority flag"
    assert row2["Risk_Tier"] == "Green",           "ID=2 should be Green tier"


# ---------------------------------------------------------------------------
# TC-10 — validate_input rejects empty DataFrame
# ---------------------------------------------------------------------------

def test_tc10_empty_dataframe_raises():
    """validate_input must raise ValueError for an empty DataFrame."""
    df = pd.DataFrame()
    with pytest.raises(ValueError, match="empty"):
        validate_input(df)


# ---------------------------------------------------------------------------
# TC-11 — validate_input rejects out-of-range S/O/D scores
# ---------------------------------------------------------------------------

def test_tc11_out_of_range_scores_raise():
    """Severity=11 (above max) must raise ValueError."""
    df = _make_df(_make_row(severity=11, occurrence=3, detection=4))
    with pytest.raises(ValueError, match="out-of-range"):
        validate_input(df)


# ---------------------------------------------------------------------------
# TC-12 — flag_critical raises KeyError if RPN column missing
# ---------------------------------------------------------------------------

def test_tc12_flag_critical_missing_rpn():
    """flag_critical must raise KeyError if called before calculate_rpn."""
    df = _make_df(_make_row())
    # Deliberately skip calculate_rpn
    with pytest.raises(KeyError, match="RPN"):
        flag_critical(df)


# ---------------------------------------------------------------------------
# TC-13 — rank_by_rpn raises KeyError if upstream columns missing
# ---------------------------------------------------------------------------

def test_tc13_rank_by_rpn_missing_columns():
    """rank_by_rpn must raise KeyError if called before flag_critical."""
    df = _make_df(_make_row())
    validate_input(df)
    df = calculate_rpn(df)
    # Deliberately skip flag_critical
    with pytest.raises(KeyError):
        rank_by_rpn(df)


# ---------------------------------------------------------------------------
# Integer-only S/O/D validation (Check 3b)
# ---------------------------------------------------------------------------

def _valid_df():
    """Minimal valid FMEA DataFrame for integer-validation tests."""
    return pd.DataFrame([{
        "ID": 1, "Process_Step": "Stamping", "Component": "Panel",
        "Function": "Structural support", "Failure_Mode": "Crack",
        "Effect": "Part failure", "Severity": 8,
        "Cause": "Over-stress", "Occurrence": 3,
        "Current_Control": "Visual inspection", "Detection": 4,
    }])


def _valid_df_float_scores():
    """Valid FMEA DataFrame with S/O/D stored as float64 dtype (numeric but not integer)."""
    df = _valid_df()
    for col in ("Severity", "Occurrence", "Detection"):
        df[col] = df[col].astype(float)
    return df


def _valid_df_object_scores():
    """Valid FMEA DataFrame with S/O/D stored as object dtype (allows mixed types)."""
    df = _valid_df()
    for col in ("Severity", "Occurrence", "Detection"):
        df[col] = df[col].astype(object)
    return df


def test_float_severity_rejected():
    """float64 Severity column (e.g. 8.5) must be rejected even when in-range."""
    df = _valid_df_float_scores()
    df.loc[0, "Severity"] = 8.5
    with pytest.raises(ValueError, match="integer"):
        validate_input(df)


def test_float_occurrence_rejected():
    """float64 Occurrence column (e.g. 3.2) must be rejected even when in-range."""
    df = _valid_df_float_scores()
    df.loc[0, "Occurrence"] = 3.2
    with pytest.raises(ValueError, match="integer"):
        validate_input(df)


def test_float_detection_rejected():
    """float64 Detection column (e.g. 4.9) must be rejected even when in-range."""
    df = _valid_df_float_scores()
    df.loc[0, "Detection"] = 4.9
    with pytest.raises(ValueError, match="integer"):
        validate_input(df)


def test_boolean_score_rejected():
    """Boolean Severity value (True) must be rejected — bool is a subclass of int."""
    df = _valid_df_object_scores()
    df.loc[0, "Severity"] = True
    with pytest.raises(ValueError, match="integer"):
        validate_input(df)


def test_numeric_string_score_rejected():
    """String '8' in a Severity column must be rejected (not numeric dtype)."""
    df = _valid_df()
    df["Severity"] = df["Severity"].astype(object)
    df.loc[0, "Severity"] = "8"
    with pytest.raises(ValueError):
        validate_input(df)


def test_bool_dtype_column_rejected():
    """A column with dtype=bool must be rejected — it is not integer."""
    df = _valid_df()
    df["Severity"] = df["Severity"].astype(bool)
    with pytest.raises(ValueError, match="integer"):
        validate_input(df)


# ---------------------------------------------------------------------------
# Task 2: Required text field and ID validation (Check 5 & Check 6)
# ---------------------------------------------------------------------------

def test_null_process_step_rejected():
    df = _valid_df()
    df.loc[0, "Process_Step"] = None
    with pytest.raises(ValueError, match="Process_Step"):
        validate_input(df)

def test_null_id_rejected():
    df = _valid_df()
    df.loc[0, "ID"] = None
    with pytest.raises(ValueError, match="ID"):
        validate_input(df)

def test_non_integer_id_rejected():
    df = _valid_df()
    df["ID"] = df["ID"].astype(object)
    df.loc[0, "ID"] = "ABC"
    with pytest.raises(ValueError, match="ID"):
        validate_input(df)

def test_float_id_rejected():
    """Float IDs must be rejected — 1.5 is not a valid integer ID."""
    df = _valid_df()
    df["ID"] = df["ID"].astype(float)
    df.loc[0, "ID"] = 1.5
    with pytest.raises(ValueError, match="ID"):
        validate_input(df)

def test_bool_id_rejected():
    """Boolean IDs must be rejected."""
    df = _valid_df()
    df["ID"] = df["ID"].astype(object)
    df.loc[0, "ID"] = True
    with pytest.raises(ValueError, match="ID"):
        validate_input(df)

def test_duplicate_ids_rejected():
    df = _valid_df()
    df2 = _valid_df()
    combined = pd.concat([df, df2], ignore_index=True)
    with pytest.raises(ValueError, match="duplicate"):
        validate_input(combined)

def test_null_failure_mode_rejected():
    df = _valid_df()
    df.loc[0, "Failure_Mode"] = None
    with pytest.raises(ValueError, match="Failure_Mode"):
        validate_input(df)

def test_null_effect_rejected():
    df = _valid_df()
    df.loc[0, "Effect"] = None
    with pytest.raises(ValueError, match="Effect"):
        validate_input(df)


# ---------------------------------------------------------------------------
# Task 11: Pydantic v2 schema layer tests
# ---------------------------------------------------------------------------


def test_fmea_row_valid():
    row = FMEARow(
        ID=1, Process_Step="Stamping", Component="Panel",
        Function="Structural support", Failure_Mode="Crack",
        Effect="Part failure", Severity=8,
        Cause="Over-stress", Occurrence=3,
        Current_Control="Visual inspection", Detection=4,
    )
    assert row.RPN == 96


def test_fmea_row_rejects_float_severity():
    with pytest.raises(pydantic.ValidationError):
        FMEARow(
            ID=1, Process_Step="Stamping", Component="Panel",
            Function="Structural support", Failure_Mode="Crack",
            Effect="Part failure", Severity=8.5,
            Cause="Over-stress", Occurrence=3,
            Current_Control="Visual inspection", Detection=4,
        )


def test_fmea_row_rejects_out_of_range():
    with pytest.raises(pydantic.ValidationError):
        FMEARow(
            ID=1, Process_Step="Stamping", Component="Panel",
            Function="Structural support", Failure_Mode="Crack",
            Effect="Part failure", Severity=11,
            Cause="Over-stress", Occurrence=3,
            Current_Control="Visual inspection", Detection=4,
        )


def test_fmea_dataset_rejects_duplicate_ids():
    row1 = FMEARow(ID=1, Process_Step="Stamping", Component="Panel", Function="F",
                   Failure_Mode="Crack", Effect="E", Severity=8, Cause="C",
                   Occurrence=3, Current_Control="Ctrl", Detection=4)
    row2 = FMEARow(ID=1, Process_Step="Welding", Component="Bracket", Function="F",
                   Failure_Mode="Warp", Effect="E", Severity=5, Cause="C",
                   Occurrence=2, Current_Control="Ctrl", Detection=3)
    with pytest.raises(pydantic.ValidationError, match="duplicate"):
        FMEADataset(rows=[row1, row2])
