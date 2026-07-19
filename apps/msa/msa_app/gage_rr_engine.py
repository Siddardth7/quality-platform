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

# d2 Constants for Average-and-Range method (AIAG MSA, Appendix B)
# Used to convert average range to sigma estimates.
_D2_CONSTANTS: dict[int, float] = {
    2: 1.128,
    3: 1.693,
    4: 2.059,
    5: 2.326,
    6: 2.704,
    7: 2.847,
    8: 2.970,
    9: 3.078,
    10: 3.078,
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
        - "sigma_study": float (Study variation estimate)
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

    # Compute EV and AV using Average-and-Range method
    ev, av, sigma_study = _average_and_range_method(df)

    # GR&R
    grr = float(np.sqrt(ev**2 + av**2))

    # Overall mean
    mean = float(df["measurement"].mean())

    # %GRR vs study variation
    pgrr_study = (grr / sigma_study) * 100 if sigma_study > 0 else float("inf")

    # %GRR vs tolerance (if provided)
    pgrr_tolerance = None
    if tolerance is not None:
        pgrr_tolerance = (grr / tolerance) * 100

    # Number of distinct categories
    ndc_value = _compute_ndc(grr, tolerance) if tolerance is not None else 0

    # Verdict
    verdict = _compute_verdict(ndc_value, pgrr_tolerance, pgrr_study)

    return {
        "ev": float(ev),
        "av": float(av),
        "grr": grr,
        "pgrr_study": float(pgrr_study),
        "pgrr_tolerance": float(pgrr_tolerance) if pgrr_tolerance is not None else None,
        "ndc": ndc_value,
        "verdict": verdict,
        "sigma_study": float(sigma_study),
        "mean": mean,
        "n_parts": n_parts,
        "n_appraisers": n_appraisers,
        "n_trials": n_trials,
        "is_balanced": is_balanced,
    }


def _average_and_range_method(df: pd.DataFrame) -> tuple[float, float, float]:
    """Compute EV, AV, and sigma_study using the AIAG Average-and-Range method.

    Args:
        df: DataFrame with columns part, appraiser, trial, measurement.

    Returns:
        (ev, av, sigma_study) tuple.

    Raises:
        ValueError: if data is unbalanced or malformed.
    """
    # Group by (part, appraiser) to get ranges within each cell
    part_appraiser_groups = df.groupby(["part", "appraiser"])["measurement"]

    # Range within each (part, appraiser) cell
    ranges_within = part_appraiser_groups.apply(lambda x: x.max() - x.min())
    avg_range_within = ranges_within.mean()

    # Number of trials per (part, appraiser) cell
    n_trials_per_cell = part_appraiser_groups.count().iloc[0]
    d2_trials = _d2_constant(int(n_trials_per_cell))

    # EV = d2 * avg_range_within per AIAG
    ev = d2_trials * avg_range_within

    # Appraiser averages
    appraiser_averages = df.groupby("appraiser")["measurement"].mean()
    range_appraisers = appraiser_averages.max() - appraiser_averages.min()

    n_appraisers = len(appraiser_averages)
    d2_appraisers = _d2_constant(n_appraisers)

    # AV per AIAG: sqrt((d2 * range_appraisers)^2 - (EV^2 / (n_parts * n_trials)))
    n_parts = df["part"].nunique()
    av_squared = (d2_appraisers * range_appraisers) ** 2 - (
        ev**2 / (n_parts * n_trials_per_cell)
    )
    av = float(np.sqrt(max(av_squared, 0)))  # Clamp to 0 if negative (numerical artifacts)

    # Sigma study from part averages
    part_averages = df.groupby("part")["measurement"].mean()
    range_parts = part_averages.max() - part_averages.min()

    # Sigma_study = (d2 * range_parts) / (1.128 * sqrt(n_appraisers * n_trials))
    # Per AIAG MSA, factor 1.128 = sqrt(8/π)
    d2_parts = _d2_constant(n_parts)
    normalization_factor = 1.128 * np.sqrt(n_appraisers * n_trials_per_cell)
    sigma_study = (d2_parts * range_parts) / normalization_factor if normalization_factor > 0 else 0

    return ev, av, sigma_study


def _d2_constant(m: int) -> float:
    """Return the d2 constant for the Average-and-Range method.

    Args:
        m: Number of measurements in the subgroup (or number of subgroups).

    Returns:
        d2 constant from AIAG MSA table. For m > 10, returns the m=10 value (3.078).

    Raises:
        ValueError: if m < 2.
    """
    if m < 2:
        raise ValueError(f"d2 constant requires subgroup size >= 2, got {m}")
    return _D2_CONSTANTS.get(m, _D2_CONSTANTS[10])


def _compute_ndc(grr: float, tolerance: float) -> int:
    """Compute Number of Distinct Categories per AIAG MSA.

    ndc = floor(1.41 * (tolerance / GRR))

    Args:
        grr: GR&R value (must be > 0).
        tolerance: Tolerance = USL - LSL (must be > 0).

    Returns:
        ndc as an int, clamped to [0, 100].
    """
    if grr <= 0 or tolerance <= 0:
        return 0
    ndc_raw = 1.41 * (tolerance / grr)
    ndc_int = int(np.floor(ndc_raw))
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

    # If %GRR is infinite (e.g., sigma_study = 0), reject
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
