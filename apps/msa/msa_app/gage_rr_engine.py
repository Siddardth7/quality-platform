"""Gage R&R computation — Average-and-Range method (AIAG MSA, 4th Edition).

This module implements the core Gage R&R (Repeatability & Reproducibility) analysis
using the Average-and-Range method per AIAG MSA standards. It computes Equipment
Variation (EV), Appraiser Variation (AV), %GRR, number of distinct categories (ndc),
and an AIAG verdict (Accept/Marginal/Reject) for crossed gage studies.

All formulas and thresholds are verified against AIAG MSA (4th Edition) and documented
in the ASSUMPTIONS_LOG. See apps/msa/docs/ASSUMPTIONS_LOG.md for standards references.
"""

from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd

__all__ = [
    "compute_gage_rr",
]

# K1/K2/K3 constants for the Average-and-Range method (AIAG MSA, 4th Edition,
# Gage R&R report form / Appendix C). Each K = 1/d2*, using the d2* adjustment
# for the relevant subgroup layout (not plain d2), so the K tables are used
# verbatim rather than re-deriving them from a d2 lookup.
_K1: dict[int, float] = {2: 0.8862, 3: 0.5908}  # by number of trials (r)
_K2: dict[int, float] = {2: 0.7071, 3: 0.5231}  # by number of appraisers (k)
_K3: dict[int, float] = {  # by number of parts (n)
    2: 0.7071,
    3: 0.5231,
    4: 0.4467,
    5: 0.4030,
    6: 0.3742,
    7: 0.3534,
    8: 0.3375,
    9: 0.3249,
    10: 0.3146,
}


def compute_gage_rr(
    data: pd.DataFrame | list[dict],
    tolerance: float | None = None,
) -> dict[str, Any]:
    """Compute Gage R&R (Average-and-Range method) per AIAG MSA.

    Args:
        data: DataFrame or list of dicts with columns/keys: part, appraiser, trial, measurement.
        tolerance: USL - LSL (study-level tolerance). If None, %GRR is computed vs study variation only.

    Returns:
        dict with keys:
        - "ev": float (Repeatability / Equipment Variation)
        - "av": float (Reproducibility / Appraiser Variation)
        - "grr": float (GR&R = sqrt(EV^2 + AV^2))
        - "pgrr_study": float (%GRR vs study variation)
        - "pgrr_tolerance": float | None (%GRR vs tolerance; None if tolerance is None)
        - "ndc": int (Number of Distinct Categories)
        - "verdict": str ("Accept", "Marginal", or "Reject")
        - "tv": float (Total Variation = sqrt(GRR^2 + PV^2))
        - "pv": float (Part Variation)
        - "mean": float (Overall mean of all measurements)
        - "n_parts": int (Unique parts)
        - "n_appraisers": int (Unique appraisers)
        - "n_trials": int (Replications per (part, appraiser) cell; assumes balanced)
        - "is_balanced": bool (True if every (part, appraiser) pair has n_trials measurements)

    Raises:
        ValueError: if data is empty, fewer than 2 parts/appraisers/replicates, or
                    if tolerance is 0 / negative / NaN / inf.
    """
    # Convert to DataFrame if list of dicts
    if isinstance(data, list):
        df = pd.DataFrame(data)
    else:
        df = data.copy()

    # Validate input
    if df.empty:
        raise ValueError("Data must contain at least one measurement.")

    required_cols = {"part", "appraiser", "trial", "measurement"}
    if not required_cols.issubset(df.columns):
        missing = required_cols - set(df.columns)
        raise ValueError(f"Missing required columns: {missing}")

    # Ensure numeric measurement column
    df["measurement"] = pd.to_numeric(df["measurement"], errors="raise")

    # Check for NaN or inf
    if df["measurement"].isna().any():
        raise ValueError("Measurements contain NaN values.")
    if np.isinf(df["measurement"]).any():
        raise ValueError("Measurements contain infinite values.")

    # Validate tolerance
    if tolerance is not None:
        if tolerance <= 0 or not np.isfinite(tolerance):
            raise ValueError("Tolerance (USL - LSL) must be a positive finite number.")

    n_parts = df["part"].nunique()
    n_appraisers = df["appraiser"].nunique()

    if n_parts < 2:
        raise ValueError("Study must include at least 2 parts.")
    if n_appraisers < 2:
        raise ValueError("Study must include at least 2 appraisers.")

    # Check minimum replicates per (part, appraiser) pair and balance
    part_appraiser_counts = df.groupby(["part", "appraiser"]).size()
    min_replicates = part_appraiser_counts.min()
    max_replicates = part_appraiser_counts.max()

    if min_replicates < 2:
        raise ValueError("Study must include at least 2 trials per (part, appraiser) pair.")

    # Determine balance (all cells must have the same number of replicates)
    is_balanced = bool((part_appraiser_counts == part_appraiser_counts.iloc[0]).all())
    n_trials = int(part_appraiser_counts.iloc[0])  # Assumes at least one (part, appraiser) pair

    if not is_balanced:
        raise ValueError(
            f"Data is unbalanced. Average-and-Range method requires equal trials per (part, appraiser) cell. "
            f"Found {min_replicates}–{max_replicates} trials across cells."
        )

    # Compute EV, AV, and PV using Average-and-Range method
    ev, av, pv = _average_and_range_method(df)

    # GR&R
    grr = float(np.sqrt(ev**2 + av**2))

    # Total variation
    tv = float(np.sqrt(grr**2 + pv**2))

    # Overall mean
    mean = float(df["measurement"].mean())

    # %GRR vs study variation
    pgrr_study = (grr / tv) * 100 if tv > 0 else float("inf")

    # %GRR vs tolerance (if provided)
    pgrr_tolerance = None
    if tolerance is not None:
        pgrr_tolerance = (grr / tolerance) * 100

    # Number of distinct categories (independent of tolerance)
    ndc_value = _compute_ndc(grr, pv)

    # Verdict: when both %GRR-tolerance and %GRR-study exist, drive the verdict off
    # the more conservative (worse) of the two (SME resolution, W08-2 spec). ndc and
    # each %GRR are still reported individually via the return dict above.
    verdict_pgrr = max(pgrr_tolerance, pgrr_study) if pgrr_tolerance is not None else pgrr_study
    verdict = _compute_verdict(ndc_value, None, verdict_pgrr)

    return {
        "ev": float(ev),
        "av": float(av),
        "grr": grr,
        "pgrr_study": float(pgrr_study),
        "pgrr_tolerance": float(pgrr_tolerance) if pgrr_tolerance is not None else None,
        "ndc": ndc_value,
        "verdict": verdict,
        "tv": tv,
        "pv": float(pv),
        "mean": mean,
        "n_parts": n_parts,
        "n_appraisers": n_appraisers,
        "n_trials": n_trials,
        "is_balanced": is_balanced,
    }


def _average_and_range_method(df: pd.DataFrame) -> tuple[float, float, float]:
    """Compute EV, AV, and PV using the AIAG Average-and-Range method.

    All three components (and GRR/TV derived from them) are reported in raw
    sigma units (K = 1/d2*). The historical 5.15/6-sigma "study variation"
    multiplier is intentionally omitted: it would multiply EV, AV, PV, GRR,
    and TV identically, so it cancels out of %GRR = GRR/TV and ndc = 1.41*PV/GRR.

    Args:
        df: DataFrame with columns part, appraiser, trial, measurement.

    Returns:
        (ev, av, pv) tuple.

    Raises:
        ValueError: if data is unbalanced or malformed.
    """
    # Group by (part, appraiser) to get ranges within each cell
    part_appraiser_groups = df.groupby(["part", "appraiser"])["measurement"]

    # Range within each (part, appraiser) cell
    ranges_within = part_appraiser_groups.apply(lambda x: x.max() - x.min())
    avg_range_within = ranges_within.mean()  # Rbar

    # Number of trials per (part, appraiser) cell
    n_trials_per_cell = part_appraiser_groups.count().iloc[0]
    k1 = _k_constant(_K1, int(n_trials_per_cell), "trials")

    # EV = Rbar * K1(trials)
    ev = avg_range_within * k1

    # Appraiser averages
    appraiser_averages = df.groupby("appraiser")["measurement"].mean()
    range_appraisers = appraiser_averages.max() - appraiser_averages.min()  # Xdiff

    n_appraisers = len(appraiser_averages)
    k2 = _k_constant(_K2, n_appraisers, "appraisers")

    # AV = sqrt((Xdiff * K2)^2 - EV^2 / (n_parts * n_trials))
    n_parts = df["part"].nunique()
    av_squared = (range_appraisers * k2) ** 2 - (ev**2 / (n_parts * n_trials_per_cell))
    av = float(np.sqrt(max(av_squared, 0)))  # Clamp to 0 if negative (numerical artifacts)

    # Part variation from part averages
    part_averages = df.groupby("part")["measurement"].mean()
    range_parts = part_averages.max() - part_averages.min()  # Rp

    # PV = Rp * K3(parts)
    k3 = _k_constant(_K3, n_parts, "parts")
    pv = range_parts * k3

    return ev, av, pv


def _k_constant(table: dict[int, float], m: int, label: str) -> float:
    """Look up an AIAG K constant (K = 1/d2*) by subgroup size.

    Args:
        table: One of `_K1`, `_K2`, `_K3`.
        m: Subgroup size (number of trials, appraisers, or parts).
        label: Human-readable description of `m`, used in the error message.

    Returns:
        The K constant for `m`.

    Raises:
        ValueError: if `m` is not in the table (AIAG's published range-method
            tables do not define K values outside these sizes; extrapolating
            or clamping would be unsupported).
    """
    if m not in table:
        raise ValueError(f"No AIAG K constant for {m} {label} (supported sizes: {sorted(table)}).")
    return table[m]


def _compute_ndc(grr: float, pv: float) -> int:
    """Compute Number of Distinct Categories per AIAG MSA.

    ndc = trunc(1.41 * (PV / GRR))

    Args:
        grr: GR&R value (must be > 0).
        pv: Part Variation (must be > 0).

    Returns:
        ndc as an int, clamped to [0, 100].
    """
    if grr <= 0 or pv <= 0:
        return 0
    ndc_raw = 1.41 * (pv / grr)
    ndc_int = int(ndc_raw)  # truncate toward zero
    return max(0, min(ndc_int, 100))  # Clamp to [0, 100]


def _compute_verdict(ndc: int, pgrr_tolerance: float | None, pgrr_study: float) -> str:
    """Compute AIAG verdict based on ndc and %GRR thresholds.

    Args:
        ndc: Number of distinct categories.
        pgrr_tolerance: %GRR vs tolerance (or None if tolerance was not provided).
        pgrr_study: %GRR vs study variation.

    Returns:
        "Accept", "Marginal", or "Reject".

    Logic (AIAG MSA):
    - Accept: ndc >= 5 AND %GRR < 10%
    - Marginal: (ndc 2–4) OR (10% <= %GRR <= 30%)
    - Reject: ndc < 2 OR %GRR > 30%
    """
    # Hard reject conditions
    if ndc < 2:
        return "Reject"

    # Use %GRR_tolerance if available, else %GRR_study
    pgrr = pgrr_tolerance if pgrr_tolerance is not None else pgrr_study

    # If %GRR is infinite (e.g., TV = 0), reject
    if not np.isfinite(pgrr):
        return "Reject"

    # Accept: ndc >= 5 and %GRR < 10%
    if ndc >= 5 and pgrr < 10:
        return "Accept"

    # Reject: ndc < 2 or %GRR > 30%
    if pgrr > 30:
        return "Reject"

    # Marginal: everything else
    return "Marginal"
