"""Tests for msa_app/gage_rr_engine.py — Gage R&R computation (W08-2).

Drives the compute_gage_rr() function and all internal helpers with:
- Happy paths (standard AIAG studies): a reference test against the AIAG MSA
  4th-ed "study case 1" canonical 10x3x3 dataset (raw values from a public
  reproduction of the manual; published EV/AV/GRR/ndc asserted), plus a
  synthetic 3x2x2 "Example B" study, hand-computed end to end (see
  .pipeline/spec.md).
- Verdict matrix (coverage of all Accept/Marginal/Reject paths).
- Edge cases (unbalanced data, NaN/inf, zero tolerance, empty data).
- K1/K2/K3 constant lookup and formula verification.
- Balance detection.
"""

from __future__ import annotations

import io
from pathlib import Path

import numpy as np
import pandas as pd
import pytest
from msa_app.gage_rr_engine import (
    _K1,
    _K2,
    _K3,
    _average_and_range_method,
    _compute_ndc,
    _compute_verdict,
    _k_constant,
    compute_gage_rr,
)
from msa_app.schema import load_gage_study_csv

_AIAG_REFERENCE_STUDY_CSV = (
    Path(__file__).resolve().parents[1] / "data" / "aiag_reference_study.csv"
)

# --- Fixtures ----------------------------------------------------------------


@pytest.fixture
def balanced_10_3_3() -> pd.DataFrame:
    """AIAG recommended 10 parts × 3 appraisers × 3 trials study."""
    data = []
    np.random.seed(42)
    for part in [f"P{i:02d}" for i in range(1, 11)]:
        part_mean = 10.0 + np.random.normal(0, 0.05)
        for appraiser in ["A", "B", "C"]:
            appraiser_bias = np.random.normal(0, 0.02)
            for trial in [1, 2, 3]:
                measurement = (
                    part_mean
                    + appraiser_bias
                    + np.random.normal(0, 0.01)
                )
                data.append({
                    "part": part,
                    "appraiser": appraiser,
                    "trial": trial,
                    "measurement": measurement,
                })
    return pd.DataFrame(data)


@pytest.fixture
def balanced_3_2_3() -> pd.DataFrame:
    """Minimal balanced study: 3 parts × 2 appraisers × 3 trials."""
    data = []
    np.random.seed(123)
    for part in ["P1", "P2", "P3"]:
        part_mean = 10.0 + np.random.normal(0, 0.05)
        for appraiser in ["X", "Y"]:
            appraiser_bias = np.random.normal(0, 0.02)
            for trial in [1, 2, 3]:
                measurement = (
                    part_mean
                    + appraiser_bias
                    + np.random.normal(0, 0.01)
                )
                data.append({
                    "part": part,
                    "appraiser": appraiser,
                    "trial": trial,
                    "measurement": measurement,
                })
    return pd.DataFrame(data)


@pytest.fixture
def identical_measurements() -> pd.DataFrame:
    """All measurements identical (edge case)."""
    data = []
    for part in ["P1", "P2"]:
        for appraiser in ["A", "B"]:
            for trial in [1, 2]:
                data.append({
                    "part": part,
                    "appraiser": appraiser,
                    "trial": trial,
                    "measurement": 10.0,
                })
    return pd.DataFrame(data)


# --- K1/K2/K3 Constant Tests --------------------------------------------------


def test_k_constant_exact_values():
    """Verify K1/K2/K3 constants match AIAG MSA 4th Edition (primary-source verified)."""
    assert _k_constant(_K1, 2, "trials") == 0.8862
    assert _k_constant(_K1, 3, "trials") == 0.5908
    assert _k_constant(_K2, 2, "appraisers") == 0.7071
    assert _k_constant(_K2, 3, "appraisers") == 0.5231
    assert _k_constant(_K3, 2, "parts") == 0.7071
    assert _k_constant(_K3, 3, "parts") == 0.5231
    assert _k_constant(_K3, 4, "parts") == 0.4467
    assert _k_constant(_K3, 5, "parts") == 0.4030
    assert _k_constant(_K3, 6, "parts") == 0.3742
    assert _k_constant(_K3, 7, "parts") == 0.3534
    assert _k_constant(_K3, 8, "parts") == 0.3375
    assert _k_constant(_K3, 9, "parts") == 0.3249
    assert _k_constant(_K3, 10, "parts") == 0.3146


def test_k_constant_off_table_raises():
    """Verify sizes outside the published K tables raise ValueError (no clamp/extrapolate)."""
    with pytest.raises(ValueError, match="No AIAG K constant"):
        _k_constant(_K3, 11, "parts")
    with pytest.raises(ValueError, match="No AIAG K constant"):
        _k_constant(_K2, 4, "appraisers")
    with pytest.raises(ValueError, match="No AIAG K constant"):
        _k_constant(_K1, 4, "trials")


# --- ndc Computation Tests ---------------------------------------------------


def test_ndc_computation_standard():
    """Verify ndc = trunc(1.41 × (PV / GRR)) against the synthetic Example B study."""
    pv = 2.0924
    grr = 0.294184
    assert _compute_ndc(grr, pv) == 10


def test_ndc_clamping_upper():
    """Verify ndc clamped to 100."""
    pv = 10.0
    grr = 0.01
    assert _compute_ndc(grr, pv) == 100  # Would be 1410 without clamping


def test_ndc_truncation():
    """Verify ndc truncates toward zero (not floor/round)."""
    pv = 0.1
    grr = 0.1
    assert _compute_ndc(grr, pv) == 1  # trunc(1.41 * 1) = 1


def test_ndc_zero_grr():
    """Verify ndc = 0 if GRR <= 0."""
    assert _compute_ndc(0, 1.0) == 0
    assert _compute_ndc(-0.1, 1.0) == 0


def test_ndc_zero_pv():
    """Verify ndc = 0 if PV <= 0."""
    assert _compute_ndc(0.1, 0) == 0
    assert _compute_ndc(0.1, -0.1) == 0


# --- Verdict Logic Tests -------------------------------------------------------


def test_verdict_accept():
    """Verify ndc >= 5 AND %GRR < 10% → Accept."""
    assert _compute_verdict(ndc=5, pgrr_tolerance=9.9, pgrr_study=9.0) == "Accept"
    assert _compute_verdict(ndc=10, pgrr_tolerance=5.0, pgrr_study=5.0) == "Accept"


def test_verdict_reject_ndc_low():
    """Verify ndc < 2 → Reject."""
    assert _compute_verdict(ndc=1, pgrr_tolerance=5.0, pgrr_study=5.0) == "Reject"
    assert _compute_verdict(ndc=0, pgrr_tolerance=10.0, pgrr_study=10.0) == "Reject"


def test_verdict_reject_pgrr_high():
    """Verify %GRR > 30% → Reject."""
    assert _compute_verdict(ndc=5, pgrr_tolerance=31.0, pgrr_study=31.0) == "Reject"
    assert _compute_verdict(ndc=10, pgrr_tolerance=40.0, pgrr_study=40.0) == "Reject"


def test_verdict_reject_infinite_pgrr():
    """Verify infinite %GRR → Reject."""
    assert _compute_verdict(ndc=5, pgrr_tolerance=float("inf"), pgrr_study=100.0) == "Reject"


def test_verdict_marginal():
    """Verify everything else → Marginal."""
    assert _compute_verdict(ndc=3, pgrr_tolerance=15.0, pgrr_study=15.0) == "Marginal"
    assert _compute_verdict(ndc=2, pgrr_tolerance=25.0, pgrr_study=25.0) == "Marginal"
    assert _compute_verdict(ndc=5, pgrr_tolerance=15.0, pgrr_study=15.0) == "Marginal"


def test_verdict_uses_tolerance_if_available():
    """Verify verdict prefers %GRR_tolerance over %GRR_study."""
    # If tolerance is very strict (high %), but study is lenient (low %)
    assert (
        _compute_verdict(ndc=5, pgrr_tolerance=35.0, pgrr_study=5.0)
        == "Reject"  # Uses tolerance
    )


def test_verdict_fallback_to_study():
    """Verify verdict falls back to %GRR_study if tolerance is None."""
    assert (
        _compute_verdict(ndc=5, pgrr_tolerance=None, pgrr_study=9.0)
        == "Accept"
    )
    assert (
        _compute_verdict(ndc=5, pgrr_tolerance=None, pgrr_study=15.0)
        == "Marginal"
    )


# --- Happy Path Tests --------------------------------------------------------


def test_compute_gage_rr_balanced_study(balanced_10_3_3):
    """Verify compute_gage_rr on a standard balanced study."""
    results = compute_gage_rr(balanced_10_3_3, tolerance=1.0)

    # Check all keys are present
    expected_keys = {
        "ev",
        "av",
        "grr",
        "pgrr_study",
        "pgrr_tolerance",
        "ndc",
        "verdict",
        "tv",
        "pv",
        "mean",
        "n_parts",
        "n_appraisers",
        "n_trials",
        "is_balanced",
    }
    assert set(results.keys()) == expected_keys

    # Check types
    assert isinstance(results["ev"], float) and results["ev"] >= 0
    assert isinstance(results["av"], float) and results["av"] >= 0
    assert isinstance(results["grr"], float) and results["grr"] > 0
    assert isinstance(results["pgrr_study"], float)
    assert isinstance(results["pgrr_tolerance"], float)
    assert isinstance(results["ndc"], int) and 0 <= results["ndc"] <= 100
    assert results["verdict"] in ["Accept", "Marginal", "Reject"]
    assert isinstance(results["mean"], float)
    assert results["n_parts"] == 10
    assert results["n_appraisers"] == 3
    assert results["n_trials"] == 3
    assert results["is_balanced"] is True

    # Verify formulas: GRR = sqrt(EV^2 + AV^2)
    expected_grr = np.sqrt(results["ev"] ** 2 + results["av"] ** 2)
    assert abs(results["grr"] - expected_grr) < 1e-9


def test_compute_gage_rr_minimal_study(balanced_3_2_3):
    """Verify compute_gage_rr on a minimal (3 parts × 2 appraisers × 3 trials) study."""
    results = compute_gage_rr(balanced_3_2_3, tolerance=0.5)

    assert results["n_parts"] == 3
    assert results["n_appraisers"] == 2
    assert results["n_trials"] == 3
    assert results["is_balanced"] is True
    assert results["verdict"] in ["Accept", "Marginal", "Reject"]


def test_compute_gage_rr_no_tolerance():
    """Verify ndc/verdict are still computed (from PV/GRR) when tolerance is not provided."""
    data = pd.DataFrame([
        {"part": "P1", "appraiser": "A", "trial": 1, "measurement": 10.0},
        {"part": "P1", "appraiser": "A", "trial": 2, "measurement": 10.02},
        {"part": "P1", "appraiser": "B", "trial": 1, "measurement": 10.01},
        {"part": "P1", "appraiser": "B", "trial": 2, "measurement": 10.03},
        {"part": "P2", "appraiser": "A", "trial": 1, "measurement": 10.1},
        {"part": "P2", "appraiser": "A", "trial": 2, "measurement": 10.12},
        {"part": "P2", "appraiser": "B", "trial": 1, "measurement": 10.11},
        {"part": "P2", "appraiser": "B", "trial": 2, "measurement": 10.13},
    ])

    results = compute_gage_rr(data, tolerance=None)

    assert results["pgrr_tolerance"] is None
    # ndc is computed from PV/GRR unconditionally — no longer forced to 0 (defect #6).
    assert results["ndc"] > 0
    assert results["verdict"] in ["Accept", "Marginal", "Reject"]  # Based on study variation


# --- Worked Example B (synthetic 3 parts x 2 appraisers x 2 trials) ----------
# See .pipeline/spec.md "Worked numerical example" section B for hand arithmetic.

_EXAMPLE_B_DATA = pd.DataFrame([
    {"part": "P1", "appraiser": "A", "trial": 1, "measurement": 2.0},
    {"part": "P1", "appraiser": "A", "trial": 2, "measurement": 2.2},
    {"part": "P1", "appraiser": "B", "trial": 1, "measurement": 2.5},
    {"part": "P1", "appraiser": "B", "trial": 2, "measurement": 2.5},
    {"part": "P2", "appraiser": "A", "trial": 1, "measurement": 4.0},
    {"part": "P2", "appraiser": "A", "trial": 2, "measurement": 4.2},
    {"part": "P2", "appraiser": "B", "trial": 1, "measurement": 4.5},
    {"part": "P2", "appraiser": "B", "trial": 2, "measurement": 4.5},
    {"part": "P3", "appraiser": "A", "trial": 1, "measurement": 6.0},
    {"part": "P3", "appraiser": "A", "trial": 2, "measurement": 6.2},
    {"part": "P3", "appraiser": "B", "trial": 1, "measurement": 6.5},
    {"part": "P3", "appraiser": "B", "trial": 2, "measurement": 6.5},
])


def test_compute_gage_rr_example_b_no_tolerance():
    """End-to-end assertion against the spec's synthetic Example B, no tolerance."""
    results = compute_gage_rr(_EXAMPLE_B_DATA, tolerance=None)

    assert results["ev"] == pytest.approx(0.088620, rel=1e-3)
    assert results["av"] == pytest.approx(0.280515, rel=1e-3)
    assert results["grr"] == pytest.approx(0.294184, rel=1e-3)
    assert results["pv"] == pytest.approx(2.092400, rel=1e-3)
    assert results["tv"] == pytest.approx(2.112981, rel=1e-3)
    assert results["pgrr_study"] == pytest.approx(13.9226, rel=1e-3)
    assert results["pgrr_tolerance"] is None
    assert results["ndc"] == 10
    assert results["verdict"] == "Marginal"


def test_compute_gage_rr_example_b_with_tolerance():
    """Example B with tolerance=8.0 exercises the pgrr_tolerance branch.

    %GRR_tolerance ~= 3.68% (would be Accept alone), but %GRR_study ~= 13.92% is
    the more conservative of the two (SME Q2 resolution: verdict uses the max of
    the two %GRR values when both exist), so the verdict is Marginal, not Accept.
    """
    results = compute_gage_rr(_EXAMPLE_B_DATA, tolerance=8.0)

    assert results["pgrr_tolerance"] == pytest.approx(3.6773, rel=1e-3)
    assert results["ndc"] == 10
    assert results["verdict"] == "Marginal"


# --- AIAG MSA 4th-ed "study case 1" reference (canonical 10x3x3 study) -------


def test_compute_gage_rr_aiag_reference_study():
    """End-to-end reference test against the AIAG MSA manual's published numbers.

    Source: AIAG MSA 4th Ed. study case 1; raw table via RTX PPAP toolbox
    reproduction (`apps/msa/data/aiag_reference_study.csv`, 10 parts x 3
    appraisers x 3 trials, deviation values). EV/AV/GRR/ndc/verdict asserted
    below are the manual's own published components for this study, not a
    snapshot of the current engine output.
    """
    data = load_gage_study_csv(str(_AIAG_REFERENCE_STUDY_CSV))
    results = compute_gage_rr(data, tolerance=4.42)

    assert results["ev"] == pytest.approx(0.20188, rel=1e-2)
    assert results["av"] == pytest.approx(0.22963, rel=1e-2)
    assert results["grr"] == pytest.approx(0.30576, rel=1e-2)
    assert results["ndc"] == 5
    assert results["verdict"] == "Marginal"
    assert results["pgrr_tolerance"] == pytest.approx(6.92, rel=1e-2)


def test_compute_gage_rr_from_list_of_dicts():
    """Verify compute_gage_rr accepts list of dicts."""
    data_list = [
        {"part": "P1", "appraiser": "A", "trial": 1, "measurement": 10.0},
        {"part": "P1", "appraiser": "A", "trial": 2, "measurement": 10.02},
        {"part": "P1", "appraiser": "B", "trial": 1, "measurement": 10.01},
        {"part": "P1", "appraiser": "B", "trial": 2, "measurement": 10.03},
        {"part": "P2", "appraiser": "A", "trial": 1, "measurement": 10.1},
        {"part": "P2", "appraiser": "A", "trial": 2, "measurement": 10.12},
        {"part": "P2", "appraiser": "B", "trial": 1, "measurement": 10.11},
        {"part": "P2", "appraiser": "B", "trial": 2, "measurement": 10.13},
    ]

    results = compute_gage_rr(data_list, tolerance=1.0)
    assert results["n_parts"] == 2
    assert results["n_appraisers"] == 2


# --- Edge Case Tests ---------------------------------------------------------


def test_compute_gage_rr_empty_data():
    """Verify empty data raises ValueError."""
    with pytest.raises(ValueError, match="at least one measurement"):
        compute_gage_rr(pd.DataFrame(), tolerance=1.0)


def test_compute_gage_rr_missing_columns():
    """Verify missing required columns raises ValueError."""
    data = pd.DataFrame({"part": ["P1"], "appraiser": ["A"]})  # missing trial, measurement
    with pytest.raises(ValueError, match="Missing required columns"):
        compute_gage_rr(data, tolerance=1.0)


def test_compute_gage_rr_single_part():
    """Verify single part raises ValueError."""
    data = pd.DataFrame([
        {"part": "P1", "appraiser": "A", "trial": 1, "measurement": 10.0},
        {"part": "P1", "appraiser": "A", "trial": 2, "measurement": 10.02},
        {"part": "P1", "appraiser": "B", "trial": 1, "measurement": 10.01},
        {"part": "P1", "appraiser": "B", "trial": 2, "measurement": 10.03},
    ])
    with pytest.raises(ValueError, match="at least 2 parts"):
        compute_gage_rr(data, tolerance=1.0)


def test_compute_gage_rr_single_appraiser():
    """Verify single appraiser raises ValueError."""
    data = pd.DataFrame([
        {"part": "P1", "appraiser": "A", "trial": 1, "measurement": 10.0},
        {"part": "P1", "appraiser": "A", "trial": 2, "measurement": 10.02},
        {"part": "P2", "appraiser": "A", "trial": 1, "measurement": 10.1},
        {"part": "P2", "appraiser": "A", "trial": 2, "measurement": 10.12},
    ])
    with pytest.raises(ValueError, match="at least 2 appraisers"):
        compute_gage_rr(data, tolerance=1.0)


def test_compute_gage_rr_single_trial():
    """Verify single trial per (part, appraiser) raises ValueError."""
    data = pd.DataFrame([
        {"part": "P1", "appraiser": "A", "trial": 1, "measurement": 10.0},
        {"part": "P1", "appraiser": "B", "trial": 1, "measurement": 10.01},
        {"part": "P2", "appraiser": "A", "trial": 1, "measurement": 10.1},
        {"part": "P2", "appraiser": "B", "trial": 1, "measurement": 10.11},
    ])
    with pytest.raises(ValueError, match="at least 2 trials"):
        compute_gage_rr(data, tolerance=1.0)


def test_compute_gage_rr_nan_measurements():
    """Verify NaN measurements raise ValueError."""
    data = pd.DataFrame([
        {"part": "P1", "appraiser": "A", "trial": 1, "measurement": 10.0},
        {"part": "P1", "appraiser": "A", "trial": 2, "measurement": np.nan},
        {"part": "P1", "appraiser": "B", "trial": 1, "measurement": 10.01},
        {"part": "P1", "appraiser": "B", "trial": 2, "measurement": 10.03},
        {"part": "P2", "appraiser": "A", "trial": 1, "measurement": 10.1},
        {"part": "P2", "appraiser": "A", "trial": 2, "measurement": 10.12},
        {"part": "P2", "appraiser": "B", "trial": 1, "measurement": 10.11},
        {"part": "P2", "appraiser": "B", "trial": 2, "measurement": 10.13},
    ])
    with pytest.raises(ValueError, match="NaN"):
        compute_gage_rr(data, tolerance=1.0)


def test_compute_gage_rr_inf_measurements():
    """Verify inf measurements raise ValueError."""
    data = pd.DataFrame([
        {"part": "P1", "appraiser": "A", "trial": 1, "measurement": 10.0},
        {"part": "P1", "appraiser": "A", "trial": 2, "measurement": float("inf")},
        {"part": "P1", "appraiser": "B", "trial": 1, "measurement": 10.01},
        {"part": "P1", "appraiser": "B", "trial": 2, "measurement": 10.03},
        {"part": "P2", "appraiser": "A", "trial": 1, "measurement": 10.1},
        {"part": "P2", "appraiser": "A", "trial": 2, "measurement": 10.12},
        {"part": "P2", "appraiser": "B", "trial": 1, "measurement": 10.11},
        {"part": "P2", "appraiser": "B", "trial": 2, "measurement": 10.13},
    ])
    with pytest.raises(ValueError, match="infinite"):
        compute_gage_rr(data, tolerance=1.0)


def test_compute_gage_rr_negative_tolerance():
    """Verify negative tolerance raises ValueError."""
    data = pd.DataFrame([
        {"part": "P1", "appraiser": "A", "trial": 1, "measurement": 10.0},
        {"part": "P1", "appraiser": "A", "trial": 2, "measurement": 10.02},
        {"part": "P1", "appraiser": "B", "trial": 1, "measurement": 10.01},
        {"part": "P1", "appraiser": "B", "trial": 2, "measurement": 10.03},
        {"part": "P2", "appraiser": "A", "trial": 1, "measurement": 10.1},
        {"part": "P2", "appraiser": "A", "trial": 2, "measurement": 10.12},
        {"part": "P2", "appraiser": "B", "trial": 1, "measurement": 10.11},
        {"part": "P2", "appraiser": "B", "trial": 2, "measurement": 10.13},
    ])
    with pytest.raises(ValueError, match="positive finite"):
        compute_gage_rr(data, tolerance=-1.0)


def test_compute_gage_rr_zero_tolerance():
    """Verify zero tolerance raises ValueError."""
    data = pd.DataFrame([
        {"part": "P1", "appraiser": "A", "trial": 1, "measurement": 10.0},
        {"part": "P1", "appraiser": "A", "trial": 2, "measurement": 10.02},
        {"part": "P1", "appraiser": "B", "trial": 1, "measurement": 10.01},
        {"part": "P1", "appraiser": "B", "trial": 2, "measurement": 10.03},
        {"part": "P2", "appraiser": "A", "trial": 1, "measurement": 10.1},
        {"part": "P2", "appraiser": "A", "trial": 2, "measurement": 10.12},
        {"part": "P2", "appraiser": "B", "trial": 1, "measurement": 10.11},
        {"part": "P2", "appraiser": "B", "trial": 2, "measurement": 10.13},
    ])
    with pytest.raises(ValueError, match="positive finite"):
        compute_gage_rr(data, tolerance=0.0)


def test_compute_gage_rr_identical_measurements(identical_measurements):
    """Verify all identical measurements → TV = 0 → %GRR_study = ∞ → Reject."""
    results = compute_gage_rr(identical_measurements, tolerance=1.0)

    assert results["tv"] == 0
    assert results["pv"] == 0
    assert np.isinf(results["pgrr_study"]) or results["pgrr_study"] > 1e9
    assert results["ndc"] == 0
    assert results["verdict"] == "Reject"


def test_compute_gage_rr_unbalanced_data():
    """Verify unbalanced data (different trial counts) raises ValueError."""
    data = pd.DataFrame([
        {"part": "P1", "appraiser": "A", "trial": 1, "measurement": 10.0},
        {"part": "P1", "appraiser": "A", "trial": 2, "measurement": 10.02},
        {"part": "P1", "appraiser": "A", "trial": 3, "measurement": 10.01},  # 3 trials for A
        {"part": "P1", "appraiser": "B", "trial": 1, "measurement": 10.01},
        {"part": "P1", "appraiser": "B", "trial": 2, "measurement": 10.03},  # Only 2 trials for B
        {"part": "P2", "appraiser": "A", "trial": 1, "measurement": 10.1},
        {"part": "P2", "appraiser": "A", "trial": 2, "measurement": 10.12},
        {"part": "P2", "appraiser": "A", "trial": 3, "measurement": 10.11},
        {"part": "P2", "appraiser": "B", "trial": 1, "measurement": 10.11},
        {"part": "P2", "appraiser": "B", "trial": 2, "measurement": 10.13},
    ])
    with pytest.raises(ValueError, match="unbalanced"):
        compute_gage_rr(data, tolerance=1.0)


def test_compute_gage_rr_off_table_trials_raises():
    """Verify a study with 4 trials/cell (off the K1 table) raises ValueError."""
    data = pd.DataFrame([
        {"part": p, "appraiser": a, "trial": t, "measurement": 10.0 + 0.01 * t}
        for p in ["P1", "P2"]
        for a in ["A", "B"]
        for t in [1, 2, 3, 4]
    ])
    with pytest.raises(ValueError, match="No AIAG K constant"):
        compute_gage_rr(data, tolerance=1.0)


def test_compute_gage_rr_off_table_appraisers_raises():
    """Verify a study with 4 appraisers (off the K2 table) raises ValueError."""
    data = pd.DataFrame([
        {"part": p, "appraiser": a, "trial": t, "measurement": 10.0 + 0.01 * t}
        for p in ["P1", "P2"]
        for a in ["A", "B", "C", "D"]
        for t in [1, 2]
    ])
    with pytest.raises(ValueError, match="No AIAG K constant"):
        compute_gage_rr(data, tolerance=1.0)


def test_compute_gage_rr_off_table_parts_raises():
    """Verify a study with 11 parts (off the K3 table) raises ValueError."""
    data = pd.DataFrame([
        {"part": f"P{p}", "appraiser": a, "trial": t, "measurement": 10.0 + 0.01 * t}
        for p in range(1, 12)
        for a in ["A", "B"]
        for t in [1, 2]
    ])
    with pytest.raises(ValueError, match="No AIAG K constant"):
        compute_gage_rr(data, tolerance=1.0)


# --- Internal Function Tests -------------------------------------------------


def test_average_and_range_method_basic(balanced_3_2_3):
    """Verify _average_and_range_method returns three non-negative floats (ev, av, pv)."""
    ev, av, pv = _average_and_range_method(balanced_3_2_3)

    assert isinstance(ev, float) and ev >= 0
    assert isinstance(av, float) and av >= 0
    assert isinstance(pv, float) and pv > 0


def test_average_and_range_method_example_b():
    """Verify _average_and_range_method against the spec's synthetic Example B."""
    ev, av, pv = _average_and_range_method(_EXAMPLE_B_DATA)

    assert ev == pytest.approx(0.088620, rel=1e-3)
    assert av == pytest.approx(0.280515, rel=1e-3)
    assert pv == pytest.approx(2.092400, rel=1e-3)


def test_average_and_range_method_av_clamped_to_zero():
    """Verify AV clamped to 0 if formula yields negative AV²."""
    # Create a scenario where EV is very large (high repeatability error).
    data = pd.DataFrame([
        {"part": "P1", "appraiser": "A", "trial": 1, "measurement": 10.0},
        {"part": "P1", "appraiser": "A", "trial": 2, "measurement": 10.5},  # Large range
        {"part": "P1", "appraiser": "B", "trial": 1, "measurement": 10.1},
        {"part": "P1", "appraiser": "B", "trial": 2, "measurement": 10.15},
        {"part": "P2", "appraiser": "A", "trial": 1, "measurement": 10.0},
        {"part": "P2", "appraiser": "A", "trial": 2, "measurement": 10.5},
        {"part": "P2", "appraiser": "B", "trial": 1, "measurement": 10.1},
        {"part": "P2", "appraiser": "B", "trial": 2, "measurement": 10.15},
    ])

    ev, av, pv = _average_and_range_method(data)

    # AV should not be negative (clamped in code)
    assert av >= 0


# --- Boundary Tests ----------------------------------------------------------


def test_verdict_boundary_ndc_exactly_5():
    """Verify ndc = 5 (boundary) + %GRR < 10% → Accept."""
    assert _compute_verdict(ndc=5, pgrr_tolerance=9.99, pgrr_study=9.99) == "Accept"


def test_verdict_boundary_ndc_exactly_2():
    """Verify ndc = 2 (boundary) + %GRR < 10% → Marginal (not Accept)."""
    assert _compute_verdict(ndc=2, pgrr_tolerance=9.0, pgrr_study=9.0) == "Marginal"


def test_verdict_boundary_pgrr_exactly_10():
    """Verify %GRR = 10% (boundary) with ndc ≥ 5 → Marginal (not Accept)."""
    assert _compute_verdict(ndc=5, pgrr_tolerance=10.0, pgrr_study=10.0) == "Marginal"


def test_verdict_boundary_pgrr_exactly_30():
    """Verify %GRR = 30% (boundary) with ndc ≥ 2 → Marginal (not Reject)."""
    assert _compute_verdict(ndc=5, pgrr_tolerance=30.0, pgrr_study=30.0) == "Marginal"
