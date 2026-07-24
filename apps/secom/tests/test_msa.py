"""Tests for secom_app/msa.py — MSA-applicability refusal guard (W09-4, #68).

SECOM carries no part/appraiser/trial axis, so this guard must REFUSE it
(gage_rr_applicability -> applicable=False; assert_gage_rr_applicable -> raises).
Small synthetic frames only (mirrors test_charts.py discipline). Covers:

- SECOM-shaped frame (sensor_NNN columns only) -> full refusal.
- Every single-dim and two-dim partial-structure combo -> correct
  missing_dimensions subset, drives the per-dimension branch in the guard's
  generator expression.
- Full-structure frame (all three dims present) -> applicable=True, () missing.
- Empty DataFrame (no columns at all) -> treated as SECOM-like.
- assert_gage_rr_applicable: both branches (raises / returns None).
- Reuse-proof: the REAL W08 compute_gage_rr also rejects a SECOM-shaped frame,
  via the apps/msa conftest sys.path shim.
- Purity: input frame unchanged after either call.
- No math drift: module has no repeatability/reproducibility/variance-
  component computation.
"""

from __future__ import annotations

import itertools

import pandas as pd
import pytest
from msa_app.gage_rr_engine import compute_gage_rr
from secom_app.msa import (
    GAGE_RR_DIMENSIONS,
    MsaApplicability,
    assert_gage_rr_applicable,
    gage_rr_applicability,
)

_SECOM_SHAPED = pd.DataFrame(
    {
        "sensor_000": [1.0, 2.0, 3.0],
        "sensor_001": [4.0, 5.0, 6.0],
        "label": [-1, 1, -1],
        "timestamp": ["t1", "t2", "t3"],
    }
)

_FULL_STRUCTURE = pd.DataFrame(
    {
        "part": [1, 1, 2, 2],
        "appraiser": ["a", "a", "b", "b"],
        "trial": [1, 2, 1, 2],
        "measurement": [10.0, 10.1, 9.9, 10.0],
    }
)


# --- SECOM-shaped frame is refused -------------------------------------------


def test_secom_shaped_frame_is_fully_refused():
    verdict = gage_rr_applicability(_SECOM_SHAPED)

    assert isinstance(verdict, MsaApplicability)
    assert verdict.applicable is False
    assert verdict.missing_dimensions == ("part", "appraiser", "trial")
    assert "AIAG" in verdict.reason
    assert "MSA_APPLICABILITY.md" in verdict.reason


def test_empty_dataframe_treated_as_secom_like():
    verdict = gage_rr_applicability(pd.DataFrame())

    assert verdict.applicable is False
    assert verdict.missing_dimensions == ("part", "appraiser", "trial")


# --- Partial-structure combos: every single-dim and two-dim subset ----------


@pytest.mark.parametrize("present_dims", list(itertools.chain(
    itertools.combinations(GAGE_RR_DIMENSIONS, 1),
    itertools.combinations(GAGE_RR_DIMENSIONS, 2),
)))
def test_partial_structure_missing_dimensions_is_correct_subset(present_dims):
    columns = {dim: [1, 2] for dim in present_dims}
    columns["irrelevant_col"] = [9, 9]
    df = pd.DataFrame(columns)

    verdict = gage_rr_applicability(df)

    expected_missing = tuple(d for d in GAGE_RR_DIMENSIONS if d not in present_dims)
    assert verdict.applicable is False
    assert verdict.missing_dimensions == expected_missing


# --- Full-structure frame ----------------------------------------------------


def test_full_structure_frame_is_applicable_with_no_missing_dims():
    verdict = gage_rr_applicability(_FULL_STRUCTURE)

    assert verdict.applicable is True
    assert verdict.missing_dimensions == ()
    assert "AIAG" in verdict.reason
    assert "compute_gage_rr" in verdict.reason


# --- assert_gage_rr_applicable: both branches --------------------------------


def test_assert_raises_valueerror_on_secom_shaped_frame():
    with pytest.raises(ValueError, match="AIAG"):
        assert_gage_rr_applicable(_SECOM_SHAPED)


def test_assert_returns_none_on_full_structure_frame():
    assert assert_gage_rr_applicable(_FULL_STRUCTURE) is None


# --- Reuse-proof: the real W08 engine also rejects SECOM --------------------


def test_real_gage_rr_engine_also_rejects_secom_shaped_frame():
    with pytest.raises(ValueError, match="Missing required columns"):
        compute_gage_rr(_SECOM_SHAPED)


# --- Purity -------------------------------------------------------------------


def test_gage_rr_applicability_does_not_mutate_input_secom_shaped():
    before = _SECOM_SHAPED.copy(deep=True)

    gage_rr_applicability(_SECOM_SHAPED)

    pd.testing.assert_frame_equal(_SECOM_SHAPED, before)


def test_gage_rr_applicability_does_not_mutate_input_full_structure():
    before = _FULL_STRUCTURE.copy(deep=True)

    gage_rr_applicability(_FULL_STRUCTURE)

    pd.testing.assert_frame_equal(_FULL_STRUCTURE, before)


def test_assert_gage_rr_applicable_does_not_mutate_input():
    before = _SECOM_SHAPED.copy(deep=True)

    with pytest.raises(ValueError):
        assert_gage_rr_applicable(_SECOM_SHAPED)

    pd.testing.assert_frame_equal(_SECOM_SHAPED, before)


# --- No math drift: refusal only, no Gage R&R computation --------------------


def test_module_exposes_no_gage_rr_math_symbols():
    import secom_app.msa as msa_module

    forbidden_substrings = ("repeatab", "reproduc", "variance", "ev_", "av_", "ndc", "%grr", "grr_")
    public_names = [name.lower() for name in dir(msa_module) if not name.startswith("_")]

    for name in public_names:
        for forbidden in forbidden_substrings:
            assert forbidden not in name, f"{name} suggests Gage R&R math leaked into the guard"

    assert set(msa_module.__all__) == {
        "GAGE_RR_DIMENSIONS",
        "MsaApplicability",
        "gage_rr_applicability",
        "assert_gage_rr_applicable",
    }
