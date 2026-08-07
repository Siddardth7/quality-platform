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

from pathlib import Path

import msa_app.gage_rr_engine as gage_rr_engine
import numpy as np
import pandas as pd
import pytest
from msa_app.gage_rr_engine import (
    _K1,
    _K2,
    _K3,
    METHOD,
    METHOD_ANOVA,
    METHOD_NOTE,
    METHOD_NOTE_ANOVA,
    _anova_method,
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


def test_ndc_minimum_one():
    """Verify ndc is max(1, trunc(...)) per AIAG MSA 4th Ed. line 3427 when calculated < 1."""
    pv = 0.05
    grr = 0.1
    # 1.41 * (0.05 / 0.1) = 0.705 -> truncated is 0 -> AIAG max(1, 0) = 1
    assert _compute_ndc(grr, pv) == 1


# --- Verdict Logic Tests -------------------------------------------------------


def test_verdict_accept():
    """Verify ndc >= 5 AND %GRR < 10% → Accept."""
    assert _compute_verdict(ndc=5, pgrr=9.9) == "Accept"
    assert _compute_verdict(ndc=10, pgrr=5.0) == "Accept"


def test_verdict_reject_ndc_low():
    """Verify ndc < 2 → Reject."""
    assert _compute_verdict(ndc=1, pgrr=5.0) == "Reject"
    assert _compute_verdict(ndc=0, pgrr=10.0) == "Reject"


def test_verdict_reject_pgrr_high():
    """Verify %GRR > 30% → Reject."""
    assert _compute_verdict(ndc=5, pgrr=31.0) == "Reject"
    assert _compute_verdict(ndc=10, pgrr=40.0) == "Reject"


def test_verdict_reject_infinite_pgrr():
    """Verify infinite %GRR → Reject."""
    assert _compute_verdict(ndc=5, pgrr=float("inf")) == "Reject"


def test_verdict_marginal():
    """Verify everything else → Marginal."""
    assert _compute_verdict(ndc=3, pgrr=15.0) == "Marginal"
    assert _compute_verdict(ndc=2, pgrr=25.0) == "Marginal"
    assert _compute_verdict(ndc=5, pgrr=15.0) == "Marginal"


def test_verdict_uses_max_of_tolerance_and_study():
    """Verify compute_gage_rr's verdict is driven by max(%GRR_tolerance, %GRR_study).

    `_compute_verdict` itself now takes a single %GRR figure; the "more
    conservative of the two" rule lives in `compute_gage_rr()`'s call site, so
    this is asserted end to end through `compute_gage_rr()` instead of the
    former direct `_compute_verdict` unit test.
    """
    # Tight tolerance drives %GRR_tolerance well above %GRR_study --> Reject.
    results = compute_gage_rr(_EXAMPLE_B_DATA, tolerance=0.4)
    assert results["pgrr_study"] < 30
    assert results["pgrr_tolerance"] > 30
    assert results["verdict"] == "Reject"

    # The other direction, which pins max() rather than "prefer tolerance":
    # a loose tolerance puts %GRR_tolerance ~5% (an Accept figure on its own,
    # and ndc = 5 clears the ndc gate) while %GRR_study stays at 26.7%. Only
    # max() holds this at Marginal -- "prefer tolerance" would verdict Accept.
    aiag_data = load_gage_study_csv(str(_AIAG_REFERENCE_STUDY_CSV))
    results = compute_gage_rr(aiag_data, tolerance=36.69)
    assert results["pgrr_tolerance"] == pytest.approx(5.0, rel=1e-2)
    assert results["pgrr_study"] == pytest.approx(26.678, rel=1e-3)
    assert results["ndc"] == 5
    assert results["verdict"] == "Marginal"


def test_verdict_fallback_to_study():
    """Verify compute_gage_rr's verdict falls back to %GRR_study if tolerance is None."""
    results = compute_gage_rr(_EXAMPLE_B_DATA, tolerance=None)
    assert results["pgrr_tolerance"] is None
    assert results["pgrr_study"] == pytest.approx(13.9226, rel=1e-3)
    assert results["verdict"] == "Marginal"


# --- Happy Path Tests --------------------------------------------------------


def test_compute_gage_rr_balanced_study(balanced_10_3_3):
    """Verify compute_gage_rr on a standard balanced study."""
    results = compute_gage_rr(balanced_10_3_3, tolerance=1.0)

    # Check all keys are present
    expected_keys = {
        "ev",
        "av",
        "grr",
        "pev_study",
        "pav_study",
        "pgrr_study",
        "ppv_study",
        "pev_tolerance",
        "pav_tolerance",
        "pgrr_tolerance",
        "ppv_tolerance",
        "ndc",
        "verdict",
        "tv",
        "pv",
        "mean",
        "n_parts",
        "n_appraisers",
        "n_trials",
        "is_balanced",
        "method",
        "method_note",
        # ANOVA additions (#195) — always present, None under Average-and-Range.
        "interaction",
        "interaction_f",
        "interaction_significant",
    }
    assert set(results.keys()) == expected_keys
    assert results["interaction"] is None
    assert results["interaction_f"] is None
    assert results["interaction_significant"] is None

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

    %GRR_tolerance = 6 * 0.294184 / 8 * 100 = 22.0638% (AIAG study-variation basis,
    audit A07 / #190), still below %GRR_study ~= 13.92%'s complement — here
    22.06% > 13.92%, so %GRR_tolerance is the more conservative of the two (SME
    Q2 resolution: verdict uses the max of the two %GRR values when both exist).
    Either way the verdict is Marginal (22.06% is in the 10-30% band), not Accept.
    """
    results = compute_gage_rr(_EXAMPLE_B_DATA, tolerance=8.0)

    assert results["pgrr_tolerance"] == pytest.approx(22.0638, rel=1e-3)
    assert results["ndc"] == 10
    assert results["verdict"] == "Marginal"


# --- AIAG MSA 4th-ed "study case 1" reference (canonical 10x3x3 study) -------


def test_compute_gage_rr_aiag_reference_study():
    """End-to-end reference test against the AIAG MSA manual's published numbers.

    Source: AIAG MSA 4th Ed. study case 1; raw table via RTX PPAP toolbox
    reproduction (`apps/msa/data/aiag_reference_study.csv`, 10 parts x 3
    appraisers x 3 trials, deviation values). EV/AV/GRR/ndc asserted below are
    the manual's own published components for this study, not a snapshot of
    the current engine output.

    The ×6 tolerance-basis multiplier itself is primary-source verified
    (#217): AIAG MSA 4th Ed. Ch. III §B substitutes "the value of tolerance
    divided by six in the denominator ... in place of the total variation
    (TV)". The RTX form below is a numeric cross-check of that, not the
    source of the constant.

    `pgrr_tolerance` and `verdict` are engine output, not manual-published
    numbers, checked against the same source form's tolerance-basis figure:
    the RTX PPAP toolbox reproduction of this study computes
    `100 * (6.00 * SMV) / Eng. Tolerance = 100 * 1.847522 / 4.4200 = 41.80%`
    ("% Tolerance (SV/Toler)"). 41.51% here is within rel=1e-2 of that 41.80%
    (small drift from the form's d2*-by-operator arithmetic). At 41.5% (> 30%)
    the tolerance basis flags this study UNACCEPTABLE, per the source form,
    so the verdict is Reject, not Marginal — the old 6.92% figure was never a
    manual-published number, it was buggy (understated 6x) engine output.
    """
    data = load_gage_study_csv(str(_AIAG_REFERENCE_STUDY_CSV))
    results = compute_gage_rr(data, tolerance=4.42)

    assert results["ev"] == pytest.approx(0.20188, rel=1e-2)
    assert results["av"] == pytest.approx(0.22963, rel=1e-2)
    assert results["grr"] == pytest.approx(0.30576, rel=1e-2)
    assert results["ndc"] == 5
    assert results["verdict"] == "Reject"
    assert results["pgrr_tolerance"] == pytest.approx(41.5067, rel=1e-2)


# --- A07 / #190 regressions: the tolerance basis must reach the verdict ------
# 6 parts spaced 1.0 apart, 2 appraisers with a 0.02 bias, 2 trials with 0.01
# drift. With no tolerance: grr = 0.0164918, pgrr_study = 0.88%, ndc = 100,
# verdict Accept. ndc >= 5 and pgrr_study < 10 here, so only the tolerance
# criterion can hold the verdict back below — isolating the ×6 defect.

_A07_REGRESSION_DATA = pd.DataFrame([
    {
        "part": f"P{p}",
        "appraiser": a,
        "trial": t,
        "measurement": float(p) + bias + drift,
    }
    for p in range(1, 7)
    for a, bias in [("A", 0.0), ("B", 0.02)]
    for t, drift in [(1, 0.0), (2, 0.01)]
])


def test_compute_gage_rr_a07_regression_no_tolerance_baseline():
    """Baseline for the two regressions below: Accept with no tolerance supplied."""
    results = compute_gage_rr(_A07_REGRESSION_DATA, tolerance=None)

    assert results["grr"] == pytest.approx(0.0164918, rel=1e-3)
    assert results["pgrr_study"] == pytest.approx(0.88, rel=1e-2)
    assert results["ndc"] == 100
    assert results["verdict"] == "Accept"


def test_compute_gage_rr_a07_regression_tight_tolerance_not_accept():
    """A tolerance of ~0.183245 must make pgrr_tolerance ~= 54% and Reject.

    Pre-fix (bug), pgrr_tolerance was 9.0% and the verdict stayed Accept —
    the ×6 defect meant the tolerance criterion never reached the verdict.
    """
    results = compute_gage_rr(_A07_REGRESSION_DATA, tolerance=6 * 0.0164918 / 0.54)

    assert results["pgrr_tolerance"] == pytest.approx(54.0, rel=1e-2)
    assert results["verdict"] != "Accept"
    assert results["verdict"] == "Reject"


def test_compute_gage_rr_a07_regression_looser_tolerance_rejects_not_marginal():
    """A tolerance of ~0.119219 must make pgrr_tolerance ~= 83% and Reject, not Marginal.

    Pre-fix (bug), pgrr_tolerance was 13.83% (Marginal); the fixed value is
    well past the 30% reject threshold. ndc and pgrr_study are unaffected by
    the ×6 multiplier — asserted here to confirm the fix touches only the
    tolerance branch.
    """
    results = compute_gage_rr(_A07_REGRESSION_DATA, tolerance=6 * 0.0164918 / 0.83)

    assert results["pgrr_tolerance"] == pytest.approx(83.0, rel=1e-2)
    assert results["verdict"] == "Reject"
    assert results["pgrr_study"] == pytest.approx(0.88, rel=1e-2)
    assert results["ndc"] == 100


def test_compute_gage_rr_pgrr_tolerance_uses_six_sigma_multiplier():
    """Direct guard: pgrr_tolerance must be 6x, not 1x, of grr/tolerance.

    Protects against a future edit that drops `_STUDY_VARIATION_SIGMA` and
    silently reintroduces the ×6 understatement (audit A07 / #190).
    """
    tolerance = 4.42
    results = compute_gage_rr(
        load_gage_study_csv(str(_AIAG_REFERENCE_STUDY_CSV)), tolerance=tolerance
    )

    assert results["pgrr_tolerance"] == pytest.approx(
        6 * results["grr"] / tolerance * 100, rel=1e-9
    )


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
    assert _compute_verdict(ndc=5, pgrr=9.99) == "Accept"


def test_verdict_boundary_ndc_exactly_2():
    """Verify ndc = 2 (boundary) + %GRR < 10% → Marginal (not Accept)."""
    assert _compute_verdict(ndc=2, pgrr=9.0) == "Marginal"


def test_verdict_boundary_pgrr_exactly_10():
    """Verify %GRR = 10% (boundary) with ndc ≥ 5 → Marginal (not Accept)."""
    assert _compute_verdict(ndc=5, pgrr=10.0) == "Marginal"


def test_verdict_boundary_pgrr_exactly_30():
    """Verify %GRR = 30% (boundary) with ndc ≥ 2 → Marginal (not Reject)."""
    assert _compute_verdict(ndc=5, pgrr=30.0) == "Marginal"


# --- Method declaration (#194 / audit A10) -----------------------------------
# The payload must say which of AIAG's three acceptable variable-study techniques
# it ran, and what that technique cannot see. These are declarative constants, so
# the value is pinned as a literal (not via METHOD/METHOD_NOTE) — a rename or a
# reworded note has to show up as a failing test, not just a silent diff.


def test_compute_gage_rr_declares_the_average_and_range_method(balanced_10_3_3):
    """The returned payload names the technique, literally 'average_and_range'."""
    results = compute_gage_rr(balanced_10_3_3, tolerance=1.0)
    assert results["method"] == "average_and_range"
    assert METHOD == "average_and_range"
    assert results["method"] is METHOD


def test_method_note_declares_the_un_estimated_interaction(balanced_10_3_3):
    """The note must state the limitation AIAG names at Ch. III Sec. B, not just exist."""
    note = compute_gage_rr(balanced_10_3_3, tolerance=1.0)["method_note"]
    assert isinstance(note, str) and note.strip()
    assert note == METHOD_NOTE
    lowered = note.lower()
    assert "interaction" in lowered
    assert "not estimated" in lowered  # the interaction is NOT estimated
    assert "does not include" in lowered  # AIAG's own wording, Ch. III Sec. B
    assert "biased low" in lowered  # the direction of the error, not just its name
    assert "anova" in lowered  # names the method that would estimate it


def test_method_note_is_ascii_encodable():
    """PDF guard: METHOD_NOTE reaches fpdf2 (latin-1) via safe_text — no '×', no curly quotes."""
    METHOD_NOTE.encode("ascii")  # raises UnicodeEncodeError if anyone types an em-dash
    METHOD.encode("ascii")


@pytest.mark.parametrize("value", [METHOD, METHOD_NOTE])
def test_method_fields_are_not_csv_injection_vectors(value):
    """Both reach the results CSV unsanitized (engine constants, not user input)."""
    assert value[0] not in "=+-@"


def test_method_fields_are_identical_with_and_without_tolerance(balanced_10_3_3):
    """The declaration is unconditional — nobody may make it tolerance-dependent."""
    with_tol = compute_gage_rr(balanced_10_3_3, tolerance=1.0)
    without_tol = compute_gage_rr(balanced_10_3_3, tolerance=None)
    assert with_tol["pgrr_tolerance"] is not None
    assert without_tol["pgrr_tolerance"] is None  # the two runs really did differ
    assert with_tol["method"] == without_tol["method"] == "average_and_range"
    assert with_tol["method_note"] == without_tol["method_note"] == METHOD_NOTE


def test_method_declaration_is_public_api():
    """Consumers import the one source of truth instead of retyping the strings."""
    import msa_app.gage_rr_engine as engine

    assert "METHOD" in engine.__all__
    assert "METHOD_NOTE" in engine.__all__


# =============================================================================
# %EV / %AV / %GRR / %PV on both AIAG bases (#225, audit A10-c)
# =============================================================================
# Six keys were added: p{ev,av,pv}_{study,tolerance}, joining the pre-existing
# pgrr_study / pgrr_tolerance to form the family p{ev,av,grr,pv}_{study,tolerance}.
# The tolerance basis is the #190 recurrence risk: each of the four must scale its
# own numerator by _STUDY_VARIATION_SIGMA, or that figure is understated 6x.

_COMPONENTS = [("ev", "pev"), ("av", "pav"), ("grr", "pgrr"), ("pv", "ppv")]

# AIAG's OWN published figures for the canonical 10x3x3 study, transcribed from the
# completed Gage Repeatability and Reproducibility Report, Figure III-B 16
# (MSA_Reference_Manual_4th_Edition.md, SRC:3285-3311). These are the manual's
# printed values, NOT a snapshot of this engine's output -- that is what makes them
# an oracle. Raw data: apps/msa/data/aiag_reference_study.csv.
_AIAG_PUBLISHED_PERCENTAGES = {
    "pev_study": 17.62,  # SRC:3290-3292  "=17.62%"
    "pav_study": 20.04,  # SRC:3295-3297  "=20.04%"
    "pgrr_study": 26.68,  # SRC:3300-3302  "=26.68%"
    "ppv_study": 96.38,  # SRC:3304-3306  "=96.38%"
}
_AIAG_PUBLISHED_TV = 1.14610  # SRC:3310  "=1.14610" -- the shared denominator

_AIAG_TOLERANCE = 4.42


@pytest.fixture
def aiag_reference_results():
    """compute_gage_rr on the AIAG reference study at the form's own tolerance."""
    data = load_gage_study_csv(str(_AIAG_REFERENCE_STUDY_CSV))
    return compute_gage_rr(data, tolerance=_AIAG_TOLERANCE)


# --- T-1: the AIAG published oracle ------------------------------------------


def test_all_four_study_basis_percentages_match_the_aiag_published_form(
    aiag_reference_results,
):
    """Every study-basis percentage reproduces AIAG's printed value (rel=1e-3).

    Oracle: AIAG MSA 4th Ed., Figure III-B 16 "Gage Repeatability and
    Reproducibility Report" (SRC:3285-3311) -- the manual's completed form for
    this exact study. %EV 17.62, %AV 20.04, %GRR 26.68, %PV 96.38, TV 1.14610
    are AIAG's PUBLISHED numbers, transcribed from the manual, not values read
    back off this engine. A drift in any component, in TV, or in the 100x form
    of the ratio moves one of these outside rel=1e-3.
    """
    results = aiag_reference_results

    assert results["tv"] == pytest.approx(_AIAG_PUBLISHED_TV, rel=1e-3)
    for key, published in _AIAG_PUBLISHED_PERCENTAGES.items():
        assert results[key] == pytest.approx(published, rel=1e-3), key

    # AIAG's form column reads EV, AV, GRR, PV top to bottom; %PV dominates and
    # %EV is the smallest -- an ordering swap between keys would still satisfy
    # a set-wise check but not this.
    assert results["pev_study"] < results["pav_study"] < results["pgrr_study"]
    assert results["pgrr_study"] < results["ppv_study"]


# --- T-2: the tolerance basis on the same study -------------------------------


def test_all_four_tolerance_basis_percentages_on_the_aiag_reference_study(
    aiag_reference_results,
):
    """Tolerance-basis figures at tolerance=4.42 (engine output, NOT AIAG-published).

    AIAG's form reports only the study-variation column, so these four values are
    this engine's output under RULE 8's tolerance basis (100 * 6 * component /
    tolerance). They are pinned here so a silent drift is caught; the load-bearing
    check that the x6 is present per figure is T-4 below.
    """
    results = aiag_reference_results

    assert results["pev_tolerance"] == pytest.approx(27.4014, rel=1e-3)
    assert results["pav_tolerance"] == pytest.approx(31.1765, rel=1e-3)
    assert results["pgrr_tolerance"] == pytest.approx(41.5067, rel=1e-3)
    assert results["ppv_tolerance"] == pytest.approx(149.9451, rel=1e-3)


def test_ppv_tolerance_exceeds_100_percent_and_is_not_clamped(aiag_reference_results):
    """E-3: %PV vs tolerance is a ratio to a spec width, not a share of a total.

    149.95% on the reference study. A clamp at 100 (or at 30, or a min() with
    pgrr) would be a standards defect -- AIAG prints no ceiling on this figure.
    """
    assert aiag_reference_results["ppv_tolerance"] > 100.0
    assert aiag_reference_results["ppv_tolerance"] == pytest.approx(149.945, rel=1e-3)


# --- T-4: the #190 guard -- every tolerance figure routes through the x6 -------


def test_study_variation_sigma_is_six():
    """RULE 7: the 4th-edition study-variation multiplier, not the 3rd's 5.15."""
    assert gage_rr_engine._STUDY_VARIATION_SIGMA == 6.0


@pytest.mark.parametrize(("component", "prefix"), _COMPONENTS)
def test_tolerance_basis_routes_through_study_variation_sigma(
    aiag_reference_results, component, prefix
):
    """Each tolerance-basis figure is 100 * 6 * its own component / tolerance.

    The #190 guard, now per component. Parametrised so dropping the multiplier
    from ONE line fails exactly that case: a shared assertion would let three of
    the four regress unnoticed. The expected value uses a literal 6, so both
    "drop _STUDY_VARIATION_SIGMA" and "redefine it to 1.0" go red.
    """
    results = aiag_reference_results
    expected = results[component] * 6 / _AIAG_TOLERANCE * 100

    assert results[f"{prefix}_tolerance"] == pytest.approx(expected, rel=1e-9)
    # A dropped x6 lands at exactly one sixth -- assert the wrong answer is not
    # produced, so the test cannot pass by the approx window being loose.
    assert results[f"{prefix}_tolerance"] != pytest.approx(expected / 6, rel=1e-3)


@pytest.mark.parametrize(("component", "prefix"), _COMPONENTS)
def test_study_basis_is_the_plain_ratio_to_tv(aiag_reference_results, component, prefix):
    """Study basis is 100 * component / TV -- no x6 (it cancels), no tolerance."""
    results = aiag_reference_results
    expected = 100 * results[component] / results["tv"]

    assert results[f"{prefix}_study"] == pytest.approx(expected, rel=1e-9)
    # The study basis must NOT pick up the tolerance multiplier.
    assert results[f"{prefix}_study"] != pytest.approx(expected * 6, rel=1e-3)


def test_study_basis_is_independent_of_the_tolerance_supplied():
    """Supplying a tolerance may not move a study-basis figure."""
    data = load_gage_study_csv(str(_AIAG_REFERENCE_STUDY_CSV))
    without = compute_gage_rr(data, tolerance=None)
    tight = compute_gage_rr(data, tolerance=0.5)
    loose = compute_gage_rr(data, tolerance=1000.0)

    for _component, prefix in _COMPONENTS:
        key = f"{prefix}_study"
        assert tight[key] == pytest.approx(without[key], rel=1e-12), key
        assert loose[key] == pytest.approx(without[key], rel=1e-12), key
    # The two tolerance runs really did differ, so the check above is not vacuous.
    assert tight["pev_tolerance"] != pytest.approx(loose["pev_tolerance"])


# --- T-3: payload shape -------------------------------------------------------


def test_six_new_keys_are_floats_with_tolerance(aiag_reference_results):
    """All eight percentages are plain floats when a tolerance is supplied."""
    for _component, prefix in _COMPONENTS:
        assert isinstance(aiag_reference_results[f"{prefix}_study"], float)
        assert isinstance(aiag_reference_results[f"{prefix}_tolerance"], float)


# --- T-6: None propagation (E-2) ---------------------------------------------


def test_tolerance_basis_is_none_for_all_four_when_tolerance_is_none():
    """E-2: no tolerance -> four Nones, and the study four are still floats."""
    data = load_gage_study_csv(str(_AIAG_REFERENCE_STUDY_CSV))
    results = compute_gage_rr(data, tolerance=None)

    for _component, prefix in _COMPONENTS:
        assert results[f"{prefix}_tolerance"] is None, prefix
        assert isinstance(results[f"{prefix}_study"], float), prefix
        assert np.isfinite(results[f"{prefix}_study"])


# --- T-7: tv == 0 degenerate (E-1, RULE 13) ----------------------------------


def test_tv_zero_makes_all_four_study_percentages_infinite(identical_measurements):
    """E-1: TV == 0 -> every study-basis ratio is 0/0 -> inf, verdict Reject.

    inf (not nan, not 0.0) is the pinned convention: nan sails silently through
    _fmt_pct and 0.0 would read as "no variation consumed".
    """
    results = compute_gage_rr(identical_measurements, tolerance=1.0)

    assert results["tv"] == 0
    for _component, prefix in _COMPONENTS:
        value = results[f"{prefix}_study"]
        assert np.isinf(value), prefix
        assert value > 0, prefix  # +inf, not -inf
        assert not np.isnan(value), prefix
    assert results["verdict"] == "Reject"


def test_tv_zero_still_gives_finite_zero_tolerance_percentages(identical_measurements):
    """The tolerance basis has no degenerate case: 0 * 6 / tol == 0, not inf."""
    results = compute_gage_rr(identical_measurements, tolerance=1.0)

    for _component, prefix in _COMPONENTS:
        assert results[f"{prefix}_tolerance"] == 0.0, prefix


# --- T-8: av == 0 (E-4, RULE 14) ---------------------------------------------


_AV_CLAMPED_DATA = pd.DataFrame([
    {"part": "P1", "appraiser": "A", "trial": 1, "measurement": 10.0},
    {"part": "P1", "appraiser": "A", "trial": 2, "measurement": 10.5},
    {"part": "P1", "appraiser": "B", "trial": 1, "measurement": 10.1},
    {"part": "P1", "appraiser": "B", "trial": 2, "measurement": 10.15},
    {"part": "P2", "appraiser": "A", "trial": 1, "measurement": 10.0},
    {"part": "P2", "appraiser": "A", "trial": 2, "measurement": 10.5},
    {"part": "P2", "appraiser": "B", "trial": 1, "measurement": 10.1},
    {"part": "P2", "appraiser": "B", "trial": 2, "measurement": 10.15},
])


def test_av_clamped_to_zero_gives_zero_percentages_not_none_or_inf():
    """E-4 / RULE 14: a clamped AV**2 yields %AV == 0.0 on both bases."""
    results = compute_gage_rr(_AV_CLAMPED_DATA, tolerance=1.0)

    assert results["av"] == 0.0
    assert results["pav_study"] == 0.0
    assert results["pav_tolerance"] == 0.0
    # Distinguishable from the two other ways a percentage can be "missing".
    assert results["pav_study"] is not None
    assert results["pav_tolerance"] is not None
    assert np.isfinite(results["pav_study"])
    # %EV is non-zero here (this fixture's parts are identical, so PV and %PV are
    # legitimately 0 too), proving 0.0 above is AV's own value rather than a
    # whole-payload collapse.
    assert results["pev_study"] > 0
    assert results["pev_tolerance"] > 0


# --- T-5: verdict invariance (D-6, the hard invariant) ------------------------
# The six new figures are reporting-only. Every verdict literal below was captured
# by running the PRE-CHANGE engine (origin/test, gage_rr_engine.py before #225)
# over the same seven studies x ten tolerances, then re-run against this branch:
# 70 cases, zero deltas. They are pinned as literals, not re-derived, so a future
# edit that lets a new percentage reach _compute_verdict shows up here.

_VERDICT_STUDIES = {
    "balanced_10_3_3": "balanced_10_3_3",
    "balanced_3_2_3": "balanced_3_2_3",
    "identical_tv0": "identical_measurements",
}

_PRE_CHANGE_VERDICTS = [
    ("balanced_10_3_3", None, "Marginal"),
    ("balanced_10_3_3", 0.001, "Reject"),
    ("balanced_10_3_3", 0.05, "Reject"),
    ("balanced_10_3_3", 0.4, "Marginal"),
    ("balanced_10_3_3", 1.0, "Marginal"),
    ("balanced_10_3_3", 1000.0, "Marginal"),
    ("balanced_3_2_3", None, "Marginal"),
    ("balanced_3_2_3", 0.001, "Reject"),
    ("balanced_3_2_3", 0.5, "Marginal"),
    ("balanced_3_2_3", 1000.0, "Marginal"),
    ("identical_tv0", None, "Reject"),
    ("identical_tv0", 1.0, "Reject"),
    ("identical_tv0", 1000.0, "Reject"),
    ("example_b", None, "Marginal"),
    ("example_b", 0.4, "Reject"),
    ("example_b", 4.42, "Reject"),
    ("example_b", 8.0, "Marginal"),
    ("example_b", 1000.0, "Marginal"),
    ("a07_regression", None, "Accept"),
    ("a07_regression", 0.001, "Reject"),
    ("a07_regression", 0.4, "Marginal"),
    ("a07_regression", 0.5, "Marginal"),
    ("a07_regression", 1.0, "Accept"),
    ("a07_regression", 1000.0, "Accept"),
    ("av_zero", None, "Reject"),
    ("av_zero", 1.0, "Reject"),
    ("av_zero", 1000.0, "Reject"),
    ("aiag_reference", None, "Marginal"),
    ("aiag_reference", 0.5, "Reject"),
    ("aiag_reference", 4.42, "Reject"),
    ("aiag_reference", 8.0, "Marginal"),
    ("aiag_reference", 36.69, "Marginal"),
    ("aiag_reference", 1000.0, "Marginal"),
]


def _verdict_study(name: str, request) -> pd.DataFrame:
    if name in _VERDICT_STUDIES:
        return request.getfixturevalue(_VERDICT_STUDIES[name])
    if name == "example_b":
        return _EXAMPLE_B_DATA
    if name == "a07_regression":
        return _A07_REGRESSION_DATA
    if name == "av_zero":
        return _AV_CLAMPED_DATA
    return load_gage_study_csv(str(_AIAG_REFERENCE_STUDY_CSV))


@pytest.mark.parametrize(("study", "tolerance", "expected"), _PRE_CHANGE_VERDICTS)
def test_verdict_is_unchanged_by_the_new_percentages(study, tolerance, expected, request):
    """D-6: no input produces a different verdict than the pre-#225 engine did."""
    results = compute_gage_rr(_verdict_study(study, request), tolerance=tolerance)
    assert results["verdict"] == expected


@pytest.mark.parametrize(("study", "tolerance", "expected"), _PRE_CHANGE_VERDICTS)
def test_verdict_still_driven_only_by_ndc_and_the_worse_pgrr(
    study, tolerance, expected, request
):
    """The verdict is reproducible from ndc + max(%GRR) alone.

    Direct statement of "the six new figures are reporting-only": recomputing the
    verdict from only the two pre-existing inputs must reproduce the payload's
    verdict for every case. If %EV/%AV/%PV ever leaked into the decision, one of
    these cases would diverge.
    """
    results = compute_gage_rr(_verdict_study(study, request), tolerance=tolerance)
    pgrr = (
        max(results["pgrr_tolerance"], results["pgrr_study"])
        if results["pgrr_tolerance"] is not None
        else results["pgrr_study"]
    )
    assert _compute_verdict(results["ndc"], pgrr) == results["verdict"] == expected


# --- Boundary: the tolerance basis crossing AIAG's 10 / 30 bands --------------
# The breaking point sits AT the band edge, not mid-window: these pin that the
# x6-scaled %GRR-tolerance is what the bands are applied to.


@pytest.mark.parametrize(
    ("target_pgrr_tolerance", "expected_verdict"),
    [
        (9.99, "Accept"),  # just inside Accept
        (10.01, "Marginal"),  # one hundredth past the 10% edge
        (29.99, "Marginal"),  # just inside Marginal
        (30.01, "Reject"),  # one hundredth past the 30% edge
    ],
)
def test_tolerance_band_edges_are_crossed_by_the_six_sigma_scaled_figure(
    target_pgrr_tolerance, expected_verdict
):
    """A tolerance chosen to land %GRR-tolerance a hair either side of a band edge.

    _A07_REGRESSION_DATA has ndc = 100 and %GRR-study = 0.88%, so the study basis
    can never move these verdicts -- only the tolerance figure can. Without the
    x6 the same tolerances would give one sixth of the target and every case would
    verdict Accept.
    """
    grr = 0.0164918
    tolerance = 6 * grr / (target_pgrr_tolerance / 100)
    results = compute_gage_rr(_A07_REGRESSION_DATA, tolerance=tolerance)

    assert results["pgrr_tolerance"] == pytest.approx(target_pgrr_tolerance, rel=1e-3)
    assert results["verdict"] == expected_verdict


# =============================================================================
# ANOVA method (crossed, with interaction) — #195
# =============================================================================
# The oracle is AIAG MSA 4th Ed. Table A 4 (ANOVA table) / Table A 5 / III-B 8-10
# for the canonical 10x3x3 study in apps/msa/data/aiag_reference_study.csv. Every
# published sigma/percentage/F/ndc value below is transcribed from the manual, not
# read back off this engine — that is what makes it an acceptance gate. Verified by
# the Team Lead against MSA_Reference_Manual_4th_Edition.md lines ~5340-5364.


# --- A-1: the published ANOVA oracle -----------------------------------------


def test_anova_oracle_matches_the_aiag_published_table_a4_a5():
    """ANOVA on the canonical study reproduces AIAG's published Table A 4 / A 5.

    Oracle (manual, NOT engine output):
      EV sigma 0.199933  AV sigma 0.226838  GRR sigma 0.302373  PV sigma 1.042327
      TV 1.085 (manual prints TV to 3 dp; the sigmas to 6)
      %EV 18.4  %AV 20.9  %GRR 27.9  %PV 96.0
      F(interaction) 0.434  ->  pooled (not significant)  ->  INT = 0  ->  ndc 4
    A 6x error, a dropped interaction term, or the unpooled model each move one of
    these out of tolerance.
    """
    data = load_gage_study_csv(str(_AIAG_REFERENCE_STUDY_CSV))
    results = compute_gage_rr(data, tolerance=4.42, method="anova")

    # sigma components — manual gives 6 dp, assert tightly
    assert results["ev"] == pytest.approx(0.199933, rel=2e-4)
    assert results["av"] == pytest.approx(0.226838, rel=2e-4)
    assert results["grr"] == pytest.approx(0.302373, rel=2e-4)
    assert results["pv"] == pytest.approx(1.042327, rel=2e-4)
    # TV is printed to 3 dp in the manual (1.085); assert to that grain, not 6 dp.
    assert results["tv"] == pytest.approx(1.085, abs=1e-3)

    # interaction: F = 0.434 < F_crit, so the manual pools it to exactly 0.
    assert results["interaction_f"] == pytest.approx(0.434, abs=1e-3)
    assert results["interaction_significant"] is False
    assert results["interaction"] == 0.0

    # study-basis percentages (manual 1 dp)
    assert results["pev_study"] == pytest.approx(18.4, abs=0.1)
    assert results["pav_study"] == pytest.approx(20.9, abs=0.1)
    assert results["pgrr_study"] == pytest.approx(27.9, abs=0.1)
    assert results["ppv_study"] == pytest.approx(96.0, abs=0.1)

    assert results["ndc"] == 4
    assert results["method"] == "anova"
    assert results["method"] is METHOD_ANOVA


# --- A-2: agreement on a no-interaction study --------------------------------


def test_anova_and_average_and_range_agree_on_the_no_interaction_study():
    """Both methods report the same %GRR to within rounding on the canonical study.

    The canonical study has F(interaction)=0.434 (pooled), i.e. no significant
    interaction, so the two methods should agree. AIAG's OWN Table III-B 9 prints
    26.7 (Average-and-Range) vs 27.9 (ANOVA) for this exact study — a 1.2-point
    spread it attributes to the range vs ANOVA estimator, not to a hidden
    interaction. So "within rounding" here means within that published ~1.2-point
    gap; a 1.5-point absolute ceiling is the tolerance chosen, and it is still far
    tighter than any method-level bug (a dropped interaction term, a 6x error)
    would produce.
    """
    data = load_gage_study_csv(str(_AIAG_REFERENCE_STUDY_CSV))
    anova = compute_gage_rr(data, method="anova")
    avg_range = compute_gage_rr(data, method="average_and_range")

    assert anova["interaction_significant"] is False  # no interaction to diverge on
    delta = abs(anova["pgrr_study"] - avg_range["pgrr_study"])
    assert delta < 1.5, delta
    # And the gap really is the manual's ~1.2 points, not a coincidental zero.
    assert delta == pytest.approx(1.18, abs=0.2)


# --- A-3: the headline acceptance test — induced interaction diverges --------
# 6 parts x 3 appraisers x 3 trials. One (part=P3, appraiser=C) cell is offset by a
# fixed +1.2 that NO other cell sees — a genuine part x appraiser interaction, not a
# main effect. Big enough vs MS_e to trip the F-test at df_AxP=10, df_e=36.

_INDUCED_INTERACTION_DATA = pd.DataFrame([
    {
        "part": f"P{p}",
        "appraiser": a,
        "trial": t,
        "measurement": (
            float(p)
            + (0.01 if t == 2 else 0.0)
            + (0.02 if t == 3 else 0.0)
            + (1.2 if (p == 3 and a == "C") else 0.0)
        ),
    }
    for p in range(1, 7)
    for a in ["A", "B", "C"]
    for t in [1, 2, 3]
])


def test_anova_reports_higher_pgrr_than_average_and_range_under_real_interaction():
    """With a genuine interaction, ANOVA diverges from Average-and-Range and reports
    the higher (correct) %GRR — the issue's headline acceptance criterion.

    This is the negative-control-bearing test: if ANOVA's GRR drops the + INT^2 term
    (i.e. becomes sqrt(EV^2 + AV^2) like Average-and-Range), the divergence collapses
    and this test fails. Proven load-bearing by mutation in the tester report.
    """
    anova = compute_gage_rr(_INDUCED_INTERACTION_DATA, method="anova")
    avg_range = compute_gage_rr(_INDUCED_INTERACTION_DATA, method="average_and_range")

    # The interaction is genuinely significant — otherwise the test proves nothing.
    assert anova["interaction_significant"] is True
    assert anova["interaction"] > 0.0

    # ANOVA carries the interaction into GRR; Average-and-Range cannot see it and so
    # understates %GRR. ANOVA must report the HIGHER figure.
    assert anova["pgrr_study"] > avg_range["pgrr_study"]
    # Concretely (pins the direction and magnitude, not just the inequality):
    assert anova["pgrr_study"] == pytest.approx(15.12, abs=0.1)
    assert avg_range["pgrr_study"] == pytest.approx(5.62, abs=0.1)
    # Average-and-Range does not estimate the interaction at all.
    assert avg_range["interaction"] is None


# --- A-4: unknown method ------------------------------------------------------


def test_anova_unknown_method_raises():
    """An unrecognised method= value raises ValueError naming the two supported ones."""
    with pytest.raises(ValueError, match="Unknown method: 'bogus'"):
        compute_gage_rr(_EXAMPLE_B_DATA, method="bogus")


# --- A-5: shared validation path (unbalanced still raises under anova) --------


def test_anova_unbalanced_data_still_raises():
    """method='anova' routes through the SAME balance check as Average-and-Range."""
    data = pd.DataFrame([
        {"part": "P1", "appraiser": "A", "trial": 1, "measurement": 10.0},
        {"part": "P1", "appraiser": "A", "trial": 2, "measurement": 10.02},
        {"part": "P1", "appraiser": "A", "trial": 3, "measurement": 10.01},
        {"part": "P1", "appraiser": "B", "trial": 1, "measurement": 10.01},
        {"part": "P1", "appraiser": "B", "trial": 2, "measurement": 10.03},
        {"part": "P2", "appraiser": "A", "trial": 1, "measurement": 10.1},
        {"part": "P2", "appraiser": "A", "trial": 2, "measurement": 10.12},
        {"part": "P2", "appraiser": "A", "trial": 3, "measurement": 10.11},
        {"part": "P2", "appraiser": "B", "trial": 1, "measurement": 10.11},
        {"part": "P2", "appraiser": "B", "trial": 2, "measurement": 10.13},
    ])
    with pytest.raises(ValueError, match="unbalanced"):
        compute_gage_rr(data, method="anova")


# --- A-6: minimum-size boundary (df_AxP=1, df_e=4) ---------------------------


def test_anova_minimum_size_study_completes():
    """The smallest valid design (2 parts x 2 appraisers x 2 trials) does not error.

    df_interaction=(2-1)(2-1)=1, df_equipment=2*2*(2-1)=4 — the smallest F-distribution
    degrees of freedom this domain allows; scipy.stats.f.ppf must handle them.
    """
    data = pd.DataFrame([
        {"part": p, "appraiser": a, "trial": t, "measurement": base + 0.01 * t}
        for p, base in [("P1", 10.0), ("P2", 11.0)]
        for a in ["A", "B"]
        for t in [1, 2]
    ])
    results = compute_gage_rr(data, method="anova")

    assert results["n_parts"] == 2
    assert results["n_appraisers"] == 2
    assert results["n_trials"] == 2
    assert results["interaction_significant"] in (True, False)
    assert np.isfinite(results["grr"])


# --- A-7: METHOD_ANOVA / METHOD_NOTE_ANOVA reach the payload ------------------


def test_anova_method_constants_reach_the_payload():
    """method='anova' populates method / method_note with the ANOVA constants."""
    results = compute_gage_rr(_EXAMPLE_B_DATA, method="anova")
    assert results["method"] == METHOD_ANOVA == "anova"
    assert results["method"] is METHOD_ANOVA
    assert results["method_note"] is METHOD_NOTE_ANOVA
    note = results["method_note"].lower()
    assert "interaction" in note
    assert "pooled" in note
    assert "0.05" in note  # the documented convention is stated in the note
    # ASCII guard: the note flows into the latin-1 PDF exporter like METHOD_NOTE.
    METHOD_NOTE_ANOVA.encode("ascii")


def test_default_method_is_still_average_and_range():
    """Omitting method= must not change behaviour — the default stays Average-and-Range."""
    default = compute_gage_rr(_EXAMPLE_B_DATA)
    explicit = compute_gage_rr(_EXAMPLE_B_DATA, method="average_and_range")
    assert default["method"] is METHOD
    assert default["method_note"] is METHOD_NOTE
    assert default["interaction"] is None
    assert default["interaction_significant"] is None
    assert default["interaction_f"] is None
    # default == explicit average_and_range, key by key
    assert default == explicit


# --- A-8: MS_e == 0 branch (perfectly repeatable gage) -----------------------
# Zero within-cell spread makes MS_e = 0 and the F ratio undefined; the engine
# takes its `else` arm. Two fixtures exercise both sides of the ternary inside it.

_PERFECT_NO_INTERACTION = pd.DataFrame([
    {"part": f"P{p}", "appraiser": a, "trial": t, "measurement": float(p) + off}
    for p in range(1, 4)
    for a, off in [("A", 0.0), ("B", 0.5)]
    for t in [1, 2]
])

_PERFECT_WITH_INTERACTION = pd.DataFrame([
    {
        "part": f"P{p}",
        "appraiser": a,
        "trial": t,
        "measurement": float(p) + (1.0 if (p == 2 and a == "B") else 0.0),
    }
    for p in range(1, 4)
    for a in ["A", "B"]
    for t in [1, 2]
])


def test_anova_perfectly_repeatable_no_interaction_pools():
    """MS_e = 0 with a pure appraiser main effect: interaction not significant, F = 0."""
    results = compute_gage_rr(_PERFECT_NO_INTERACTION, method="anova")
    assert results["interaction_significant"] is False
    assert results["interaction_f"] == 0.0
    assert results["interaction"] == 0.0


def test_anova_perfectly_repeatable_with_interaction_is_significant():
    """MS_e = 0 with a real single-cell offset: interaction significant, F = inf."""
    results = compute_gage_rr(_PERFECT_WITH_INTERACTION, method="anova")
    assert results["interaction_significant"] is True
    assert np.isinf(results["interaction_f"])
    assert results["interaction"] > 0.0


# --- A-9: the floating-point cancellation floor (the coder's one deviation) ---
# SS_AxP = SS_cells - SS_parts - SS_appraiser is a difference of large nearly-equal
# sums. On a study with NO interaction and MS_e = 0, it leaves a tiny positive
# residue. This fixture's residue is ~1.2e-14, above 0 but below the floor
# (1e-12 * SS_total ~ 1.8e-10). Without the guard, `ss_interaction > 0` would flip a
# perfectly repeatable gage to the non-additive model. With it, the study stays
# pooled. Proven load-bearing by mutation in the tester report.

_CANCELLATION_RESIDUE_DATA = pd.DataFrame([
    {
        "part": f"P{pi}",
        "appraiser": a,
        "trial": t,
        "measurement": pv + (0.341 if a == "A" else 1.174),
    }
    for pi, pv in enumerate(
        [8.013, 5.822, 0.941, 4.331, 4.791, 1.597, 7.346], start=1
    )
    for a in ["A", "B"]
    for t in [1, 2]
])


def test_anova_cancellation_floor_keeps_a_repeatable_gage_pooled():
    """A no-interaction, perfectly repeatable study must NOT be flagged significant
    by a sub-floor SS_AxP cancellation residue.

    Guards `_SS_CANCELLATION_FLOOR`: the residue here is positive (~1e-14) but far
    below the floor, so the raw `ss_interaction > 0` test would report a spurious
    significant interaction. The floor holds interaction_significant at False.
    """
    results = compute_gage_rr(_CANCELLATION_RESIDUE_DATA, method="anova")
    assert results["interaction_significant"] is False
    assert results["interaction"] == 0.0
    assert results["interaction_f"] == 0.0


# --- A-10: negative-variance clamps (Appendix A: set negative components to 0) --


def test_anova_pv_clamped_to_zero_when_variance_negative():
    """PV^2 = (MS_parts - MS_pool)/(k r) goes negative when parts are identical;
    the clamp reports PV = 0.0, not a negative or NaN.

    Parts share one mean (PV -> 0) while appraiser B is biased +0.5 (AV > 0), so
    PV = 0 is that component's own clamp, not a whole-payload collapse.
    """
    data = pd.DataFrame([
        {"part": p, "appraiser": a, "trial": t, "measurement": m + off}
        for p in ["P1", "P2", "P3"]
        for a, off in [("A", 0.0), ("B", 0.5)]
        for t, m in [(1, 9.95), (2, 10.05)]
    ])
    results = compute_gage_rr(data, method="anova")
    assert results["pv"] == 0.0
    assert results["av"] > 0.0  # isolates the clamp to PV
    assert results["ev"] > 0.0
    assert np.isfinite(results["pv"])


def test_anova_av_clamped_to_zero_when_variance_negative():
    """AV^2 = (MS_appraiser - MS_pool)/(n r) goes negative under large within-cell
    noise; the clamp reports AV = 0.0, with PV still positive (parts well separated).
    """
    data = pd.DataFrame([
        {"part": p, "appraiser": a, "trial": t, "measurement": base + d}
        for pi, p in enumerate(["P1", "P2", "P3"])
        for base in [10.0 + pi * 5.0]
        for a in ["A", "B"]
        for t, d in [(1, -3.0), (2, 3.0)]
    ])
    results = compute_gage_rr(data, method="anova")
    assert results["av"] == 0.0
    assert results["pv"] > 0.0  # isolates the clamp to AV
    assert results["ev"] > 0.0
    assert np.isfinite(results["av"])


# --- A-11: _anova_method returns raw 1-sigma units (no baked-in x6) -----------


def test_anova_method_helper_returns_raw_sigma_tuple():
    """_anova_method returns (ev, av, pv, interaction, interaction_f, significant)
    in raw 1-sigma units — the same convention as _average_and_range_method (no x6).
    """
    data = load_gage_study_csv(str(_AIAG_REFERENCE_STUDY_CSV))
    ev, av, pv, interaction, interaction_f, significant = _anova_method(data)
    assert ev == pytest.approx(0.199933, rel=2e-4)  # raw sigma, not 6*sigma
    assert av == pytest.approx(0.226838, rel=2e-4)
    assert pv == pytest.approx(1.042327, rel=2e-4)
    assert interaction == 0.0
    assert significant is False
    assert interaction_f == pytest.approx(0.434, abs=1e-3)
