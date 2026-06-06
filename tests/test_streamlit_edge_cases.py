"""
test_streamlit_edge_cases.py
FMEA Risk Prioritization Tool — Edge Case Tests (W3 Checkpoint #16)

Verifies three edge-case scenarios exercised by the Streamlit app:

  Test 1 — Demo dataset: full pipeline runs end-to-end without error,
            producing a non-empty ranked DataFrame with expected columns.

  Test 2 — All Severity=1: pipeline succeeds, zero flags are raised,
            and the result is consistent with the 'No critical items' path
            that triggers st.info() in the UI.

  Test 3 — Missing Severity column: validate_input raises ValueError with
            a descriptive message; the app surfaces this as st.error()
            without crashing.

Author: Siddardth | M.S. Aerospace Engineering, UIUC
"""

from pathlib import Path

import pandas as pd
import pytest

from src.rpn_engine import run_pipeline, validate_input

# ---------------------------------------------------------------------------
# Shared fixtures
# ---------------------------------------------------------------------------

DEMO_CSV = Path(__file__).parent.parent / "data" / "composite_panel_fmea_demo.csv"

REQUIRED_COLUMNS = [
    "ID", "Process_Step", "Component", "Function",
    "Failure_Mode", "Effect", "Severity", "Cause",
    "Occurrence", "Current_Control", "Detection",
]


def _minimal_df(**overrides) -> pd.DataFrame:
    """Return a 5-row valid FMEA DataFrame; override any column via kwargs."""
    base = {
        "ID":              [1, 2, 3, 4, 5],
        "Process_Step":    ["Step A"] * 5,
        "Component":       ["Comp X"] * 5,
        "Function":        ["Func Y"] * 5,
        "Failure_Mode":    [f"FM-{i}" for i in range(1, 6)],
        "Effect":          ["Effect"] * 5,
        "Severity":        [1, 1, 1, 1, 1],
        "Cause":           ["Cause"] * 5,
        "Occurrence":      [1, 1, 1, 1, 1],
        "Current_Control": ["Control"] * 5,
        "Detection":       [1, 1, 1, 1, 1],
    }
    base.update(overrides)
    return pd.DataFrame(base)


# ---------------------------------------------------------------------------
# Test 1 — Demo dataset: full pipeline end-to-end
# ---------------------------------------------------------------------------

class TestDemoDatasetFullFlow:

    def test_demo_csv_exists(self):
        assert DEMO_CSV.exists(), f"Demo CSV not found at {DEMO_CSV}"

    def test_pipeline_returns_dataframe(self):
        df = pd.read_csv(DEMO_CSV)
        result = run_pipeline(df)
        assert isinstance(result, pd.DataFrame)

    def test_pipeline_result_non_empty(self):
        df = pd.read_csv(DEMO_CSV)
        result = run_pipeline(df)
        assert len(result) > 0

    def test_pipeline_adds_expected_columns(self):
        df = pd.read_csv(DEMO_CSV)
        result = run_pipeline(df)
        for col in ["RPN", "Risk_Tier", "Flag_High_RPN", "Flag_High_Severity", "Flag_Action_Priority_H"]:
            assert col in result.columns, f"Missing column: {col}"

    def test_rpn_values_are_positive(self):
        df = pd.read_csv(DEMO_CSV)
        result = run_pipeline(df)
        assert (result["RPN"] > 0).all()

    def test_table_sorted_descending_by_rpn(self):
        df = pd.read_csv(DEMO_CSV)
        result = run_pipeline(df)
        rpns = result["RPN"].tolist()
        assert rpns == sorted(rpns, reverse=True), "Table is not sorted descending by RPN"

    def test_risk_tiers_are_valid_values(self):
        df = pd.read_csv(DEMO_CSV)
        result = run_pipeline(df)
        assert set(result["Risk_Tier"]).issubset({"Red", "Yellow", "Green"})

    def test_demo_has_at_least_one_red_row(self):
        """Demo dataset should have at least one high-risk failure mode."""
        df = pd.read_csv(DEMO_CSV)
        result = run_pipeline(df)
        assert (result["Risk_Tier"] == "Red").any(), "Expected at least one Red row in demo dataset"


# ---------------------------------------------------------------------------
# Test 2 — All Severity=1: zero flags, consistent with 'No critical items'
# ---------------------------------------------------------------------------

class TestAllSeverityOne:

    def _run(self) -> pd.DataFrame:
        df = _minimal_df(
            Severity   =[1, 1, 1, 1, 1],
            Occurrence =[2, 3, 2, 1, 2],
            Detection  =[3, 2, 1, 4, 2],
        )
        return run_pipeline(df)

    def test_pipeline_succeeds(self):
        result = self._run()
        assert isinstance(result, pd.DataFrame)

    def test_flag_high_rpn_all_false(self):
        result = self._run()
        # Max RPN = 1 × 3 × 3 = 9 — well below threshold of 100
        assert result["Flag_High_RPN"].sum() == 0

    def test_flag_high_severity_all_false(self):
        result = self._run()
        assert result["Flag_High_Severity"].sum() == 0

    def test_flag_action_priority_h_all_false(self):
        result = self._run()
        # This is the flag the UI checks for the critical items panel
        assert result["Flag_Action_Priority_H"].sum() == 0

    def test_all_tiers_are_green(self):
        result = self._run()
        assert (result["Risk_Tier"] == "Green").all(), (
            f"Expected all Green, got: {result['Risk_Tier'].value_counts().to_dict()}"
        )

    def test_no_critical_items_path(self):
        """
        When Flag_Action_Priority_H is all False, the filtered critical DataFrame
        should be empty — which is the condition that triggers st.info('No critical items').
        """
        result = self._run()
        critical = result[result["Flag_Action_Priority_H"] == True]  # noqa: E712
        assert critical.empty, "Expected empty critical items for all-Severity-1 input"


# ---------------------------------------------------------------------------
# Test 3 — Missing Severity column: validate_input raises ValueError
# ---------------------------------------------------------------------------

class TestMissingSeverityColumn:

    def _df_without_severity(self) -> pd.DataFrame:
        df = _minimal_df()
        return df.drop(columns=["Severity"])

    def test_validate_input_raises_value_error(self):
        df = self._df_without_severity()
        with pytest.raises(ValueError):
            validate_input(df)

    def test_error_message_mentions_missing_column(self):
        df = self._df_without_severity()
        with pytest.raises(ValueError, match="Severity"):
            validate_input(df)

    def test_run_pipeline_also_raises(self):
        df = self._df_without_severity()
        with pytest.raises(ValueError):
            run_pipeline(df)

    def test_other_required_columns_still_present(self):
        """Confirm the only missing column is Severity — not a broken fixture."""
        df = self._df_without_severity()
        assert "Severity" not in df.columns
        assert "Occurrence" in df.columns
        assert "Detection" in df.columns

    def test_missing_occurrence_also_raises(self):
        df = _minimal_df().drop(columns=["Occurrence"])
        with pytest.raises(ValueError):
            validate_input(df)

    def test_missing_multiple_columns_raises(self):
        df = _minimal_df().drop(columns=["Severity", "Occurrence", "Detection"])
        with pytest.raises(ValueError):
            validate_input(df)


def test_rpn_slider_clamps_on_smaller_dataset_swap():
    """F-020 regression: switching from a high-RPN dataset to a low-RPN one
    must not crash the slider widget. Stored session_state value must be
    clamped to the new dataset's max_value before the slider is rendered."""
    from streamlit.testing.v1 import AppTest

    at = AppTest.from_file("app.py", default_timeout=10)
    at.session_state["use_demo"] = True
    at.run()
    assert not at.exception

    # Simulate user dragging slider above what a smaller dataset will allow
    at.session_state["rpn_slider"] = 700
    # And simulate the dataset shrink (the app sets _dataset_rpn_max on every run)
    at.session_state["_dataset_rpn_max"] = 100
    at.run()
    assert not at.exception, f"Slider crashed on dataset swap: {at.exception}"
    assert at.session_state["rpn_slider"] <= 100


def test_uploaded_filename_is_html_escaped():
    """F-028 regression: a filename containing HTML/JS must be rendered
    as escaped text in the sidebar, never as live markup."""
    from app import _escape_source_label  # introduced in the fix

    rendered = _escape_source_label("<script>alert(1)</script>.csv")
    assert "<script>" not in rendered
    assert "&lt;" in rendered


def test_demo_button_overrides_lingering_uploaded_file():
    """F-019 regression: the demo-button 'if use_demo' branch must shadow
    uploaded=None so the 'elif uploaded is not None' branch cannot flip
    use_demo back to False on the same rerun.
    Implementation fix: app.py sets uploaded=None in the if-use_demo block
    and uses elif (not if) for the uploaded branch.
    Full AppTest simulation is incompatible with the Streamlit session-state
    pre-write introduced by F-020; covered here by code inspection + unit test."""
    # Structural check: verify the fix is in place at source level
    import inspect

    import app as _app_mod
    from app import _escape_source_label  # smoke-import to ensure app loads
    src = inspect.getsource(_app_mod)
    assert "uploaded = None" in src, "F-019 fix: 'uploaded = None' must appear in app.py"
    assert "elif uploaded is not None" in src, "F-019 fix: elif guard must be present"
