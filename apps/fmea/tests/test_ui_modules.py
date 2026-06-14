"""
tests/test_ui_modules.py
Unit tests for pure (non-Streamlit) functions in the ui/ package.
"""
import pandas as pd
import pytest

from ui import df_content_hash
from ui.exports import _export_cache_key
from ui.filters import apply_filters

# ---------------------------------------------------------------------------
# df_content_hash
# ---------------------------------------------------------------------------

def test_df_content_hash_stable():
    """Same DataFrame produces the same hash on repeated calls."""
    df = pd.DataFrame([{"A": 1, "B": 2}])
    assert df_content_hash(df) == df_content_hash(df)


def test_df_content_hash_differs_on_different_data():
    """Different DataFrames produce different hashes."""
    df1 = pd.DataFrame([{"A": 1}])
    df2 = pd.DataFrame([{"A": 2}])
    assert df_content_hash(df1) != df_content_hash(df2)


def test_df_content_hash_index_insensitive():
    """Hash is the same regardless of DataFrame index values."""
    df1 = pd.DataFrame([{"A": 1}], index=[0])
    df2 = pd.DataFrame([{"A": 1}], index=[99])
    assert df_content_hash(df1) == df_content_hash(df2)


# ---------------------------------------------------------------------------
# apply_filters
# ---------------------------------------------------------------------------

def _make_df() -> pd.DataFrame:
    return pd.DataFrame([
        {"RPN": 200, "Severity": 9, "Process_Step": "Layup",    "Risk_Tier": "Red"},
        {"RPN": 80,  "Severity": 6, "Process_Step": "Bagging",  "Risk_Tier": "Yellow"},
        {"RPN": 20,  "Severity": 3, "Process_Step": "Autoclave","Risk_Tier": "Green"},
    ])


def test_apply_filters_rpn_min():
    df = _make_df()
    result = apply_filters(df, rpn_min=100, sev9_only=False, process_steps=["Layup", "Bagging", "Autoclave"])
    assert len(result) == 1
    assert result.iloc[0]["RPN"] == 200


def test_apply_filters_sev9_only():
    df = _make_df()
    result = apply_filters(df, rpn_min=0, sev9_only=True, process_steps=["Layup", "Bagging", "Autoclave"])
    assert len(result) == 1
    assert result.iloc[0]["Severity"] == 9


def test_apply_filters_process_steps():
    df = _make_df()
    result = apply_filters(df, rpn_min=0, sev9_only=False, process_steps=["Layup"])
    assert len(result) == 1
    assert result.iloc[0]["Process_Step"] == "Layup"


def test_apply_filters_no_filters():
    df = _make_df()
    result = apply_filters(df, rpn_min=0, sev9_only=False, process_steps=["Layup", "Bagging", "Autoclave"])
    assert len(result) == 3


def test_apply_filters_combined():
    df = _make_df()
    result = apply_filters(df, rpn_min=50, sev9_only=True, process_steps=["Layup", "Bagging"])
    assert len(result) == 1
    assert result.iloc[0]["RPN"] == 200


# ---------------------------------------------------------------------------
# _export_cache_key
# ---------------------------------------------------------------------------

def test_export_cache_key_same_inputs_same_key():
    df = pd.DataFrame([{"A": 1}])
    key1 = _export_cache_key(df, 0, False, ["Layup"], "excel")
    key2 = _export_cache_key(df, 0, False, ["Layup"], "excel")
    assert key1 == key2


def test_export_cache_key_different_data_different_key():
    df1 = pd.DataFrame([{"A": 1}])
    df2 = pd.DataFrame([{"A": 2}])
    key1 = _export_cache_key(df1, 0, False, ["Layup"], "excel")
    key2 = _export_cache_key(df2, 0, False, ["Layup"], "excel")
    assert key1 != key2


def test_export_cache_key_different_type_different_key():
    df = pd.DataFrame([{"A": 1}])
    key_xl  = _export_cache_key(df, 0, False, ["Layup"], "excel")
    key_pdf = _export_cache_key(df, 0, False, ["Layup"], "pdf")
    assert key_xl != key_pdf
