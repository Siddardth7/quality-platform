"""Gage R&R computation — Average-and-Range and ANOVA methods (AIAG MSA, 4th Edition).

This module implements the core Gage R&R (Repeatability & Reproducibility) analysis
for crossed gage studies: Equipment Variation (EV), Appraiser Variation (AV), %GRR,
number of distinct categories (ndc), and an AIAG verdict (Accept/Marginal/Reject).

Two of AIAG's three acceptable variable-study techniques are available, selected by
``compute_gage_rr(..., method=...)`` and declared in the payload as ``method`` /
``method_note``:

- ``"average_and_range"`` (**the default**, unchanged) — arithmetic only, but it does
  not estimate the part x appraiser interaction (AIAG MSA 4th Ed., Ch. III Sec. B —
  "the Range and the Average and Range methods does not include this variation" [sic]).
  That interaction is absorbed into the reported components, so %GRR is biased low
  whenever it is non-zero; AIAG's own procedure states "no statistical interaction
  between appraisers and parts" as a precondition.
- ``"anova"`` (#195) — the crossed two-factor ANOVA with replication (Ch. III Sec. B,
  "Analysis of Variance (ANOVA) Method"; Appendix A, "Analysis of Variance Concepts").
  It estimates the interaction, tests it, and either pools it into repeatability or
  carries it into ``GRR = sqrt(EV^2 + AV^2 + INT^2)``. See ``_anova_method``.

All formulas and thresholds are verified against AIAG MSA (4th Edition) and documented
in the ASSUMPTIONS_LOG. See apps/msa/docs/ASSUMPTIONS_LOG.md for standards references
(RULE 1 for the method choice, RULE 17 for the ANOVA decomposition).
"""

from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd
from scipy import stats

__all__ = [
    "METHOD",
    "METHOD_ANOVA",
    "METHOD_NOTE",
    "METHOD_NOTE_ANOVA",
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

# AIAG MSA 4th Ed. study-variation multiplier: 6 sigma = 99.73% coverage. EV/AV/GRR/PV/TV are
# carried in bare 1-sigma units (K = 1/d2*), so the tolerance basis — a full spec width, not a
# sigma — must scale the numerator by this before dividing. (5.15 sigma / 99.0% is the older
# 3rd-edition convention; SME decision 2026-07-26 pins 6.) Primary-source verified (#217,
# 2026-07-30): AIAG MSA 4th Ed. Ch. III Sec. B — "%EV, %AV, %GRR and %PV are calculated by
# substituting the value of tolerance divided by six in the denominator ... in place of the total
# variation (TV)"; tolerance/6 in the denominator == 6*GRR/tolerance. Same section redirects to
# Ch. II Sec. D Table II-D 1 for the acceptance bands, so ONE band set (10/30) covers both the
# tolerance and study-variation bases -- see ASSUMPTIONS_LOG RULE 8.
_STUDY_VARIATION_SIGMA = 6.0

# Which of AIAG's three acceptable variable-study techniques this engine implements, and what
# that choice costs. Declared in the payload so a consumer reading JSON/CSV can tell an
# Average-and-Range %GRR from an ANOVA one. ASCII only ("x", not "×"): these strings flow into
# the PDF exporter via safe_text/fpdf2, which is latin-1.
# ponytail: plain constants, not a TypedDict return or an `interaction_estimated` flag —
# a consumer that must branch compares `method == "average_and_range"`.
METHOD = "average_and_range"
METHOD_NOTE = (
    "Average-and-Range method: the part x appraiser interaction is NOT estimated. "
    'AIAG MSA 4th Ed., Ch. III Sec. B: the Average and Range method "does not include" the '
    "operator-to-part interaction, which is therefore absorbed into the reported components; "
    "%GRR is biased low when that interaction is non-zero. ANOVA (which separates it) is "
    'available via method="anova".'
)

METHOD_ANOVA = "anova"

# Significance level for the interaction F-test (#195). AIAG MSA 4th Ed. does NOT mandate a
# significance level: Appendix A only says "In order to decrease the risk of falsely concluding
# that there is no interaction effect, choose a high significance level" (no number). 0.05 is the
# level used in the manual's own worked example: Table A 4's starred F values are footnoted as
# significant at the 0.05 level. That makes it the one value evidenced in the primary source, and it
# is adopted here as a convention, not as a standard requirement. See ASSUMPTIONS_LOG RULE 17.
# ponytail: a module constant, not a parameter — SME decision 2026-08-07 explicitly barred an
# `alpha=` argument on compute_gage_rr. One documented convention beats a knob nobody turns.
_ANOVA_ALPHA = 0.05

# Relative floor for "SS_AxP is not zero", used ONLY when MS_e == 0 leaves the F ratio undefined
# (see `_anova_method`). SS_AxP = SS_cells - SS_parts - SS_appraiser is a difference of large
# nearly-equal sums, so a study with no interaction at all still leaves a cancellation residue of
# order 1e-16 * SS_total. Treating that residue as an interaction would flip a perfectly repeatable
# gage to the non-additive model and put a noise-level term into GRR. A genuine interaction is many
# orders of magnitude above this floor. Not an AIAG figure — a floating-point guard.
_SS_CANCELLATION_FLOOR = 1e-12

METHOD_NOTE_ANOVA = (
    "ANOVA method (crossed two-factor with replication): the part x appraiser interaction IS "
    "estimated and tested. AIAG MSA 4th Ed., Ch. III Sec. B / Appendix A. When the interaction "
    'F statistic falls below its critical value "the interaction term is pooled with the '
    'equipment (error) term" and the interaction is reported as 0; when it does not, '
    "GRR = sqrt(EV^2 + AV^2 + INT^2) carries the interaction. The F-test uses alpha = 0.05, the "
    "level footnoted in the manual's own worked example (Table A 4); AIAG does not mandate a "
    "significance level. Negative variance components are set to zero, per Appendix A."
)


def compute_gage_rr(
    data: pd.DataFrame | list[dict],
    tolerance: float | None = None,
    method: str = METHOD,
) -> dict[str, Any]:
    """Compute Gage R&R per AIAG MSA (Average-and-Range by default, or ANOVA).

    Args:
        data: DataFrame or list of dicts with columns/keys: part, appraiser, trial, measurement.
        tolerance: USL - LSL (study-level tolerance). If None, the four percentages are
            computed vs study variation only. If supplied, all four (%EV, %AV, %GRR, %PV)
            are also computed on the tolerance basis, not %GRR alone.
        method: ``METHOD`` ("average_and_range", the default — unchanged behaviour) or
            ``METHOD_ANOVA`` ("anova", which additionally estimates the part x appraiser
            interaction; see `_anova_method`). Any other value raises ValueError.

    Returns:
        dict with keys:
        - "ev": float (Repeatability / Equipment Variation)
        - "av": float (Reproducibility / Appraiser Variation)
        - "grr": float (GR&R = sqrt(EV^2 + AV^2); sqrt(EV^2 + AV^2 + INT^2) under "anova")
        - "pev_study": float (%EV vs study variation, 100*EV/TV; inf if TV == 0)
        - "pav_study": float (%AV vs study variation, 100*AV/TV; inf if TV == 0)
        - "pgrr_study": float (%GRR vs study variation, 100*GRR/TV; inf if TV == 0)
        - "ppv_study": float (%PV vs study variation, 100*PV/TV; inf if TV == 0)
        - "pev_tolerance": float | None (%EV vs tolerance, 100*6*EV/tolerance;
          None if tolerance is None)
        - "pav_tolerance": float | None (%AV vs tolerance, 100*6*AV/tolerance;
          None if tolerance is None)
        - "pgrr_tolerance": float | None (%GRR vs tolerance, 100*6*GRR/tolerance;
          None if tolerance is None)
        - "ppv_tolerance": float | None (%PV vs tolerance, 100*6*PV/tolerance; may exceed
          100% and is deliberately unclamped; None if tolerance is None)
        - "ndc": int (Number of Distinct Categories)
        - "verdict": str ("Accept", "Marginal", or "Reject")
        - "tv": float (Total Variation = sqrt(GRR^2 + PV^2))
        - "pv": float (Part Variation)
        - "mean": float (Overall mean of all measurements)
        - "n_parts": int (Unique parts)
        - "n_appraisers": int (Unique appraisers)
        - "n_trials": int (Replications per (part, appraiser) cell; assumes balanced)
        - "is_balanced": bool (True if every (part, appraiser) pair has n_trials measurements)
        - "method": str (the AIAG technique used: ``METHOD`` or ``METHOD_ANOVA``)
        - "method_note": str (``METHOD_NOTE`` / ``METHOD_NOTE_ANOVA``: what the technique
          used can and cannot see — for Average-and-Range, that the part x appraiser
          interaction is not estimated, so %GRR is biased low when it is non-zero)
        - "interaction": float | None (sigma_interaction in raw sigma units, matching
          EV/AV/PV/GRR; 0.0 when the ANOVA F-test pooled it. None under "average_and_range",
          which cannot estimate it — branch on ``is not None``, not on truthiness)
        - "interaction_f": float | None (the interaction F statistic, MS_AxP / MS_e;
          None under "average_and_range")
        - "interaction_significant": bool | None (whether the F statistic exceeded its
          critical value at alpha = 0.05, i.e. whether the interaction was NOT pooled;
          None under "average_and_range")

    Raises:
        ValueError: if data is empty, fewer than 2 parts/appraisers/replicates,
                    if tolerance is 0 / negative / NaN / inf, or if `method` is
                    not one of the two supported values.
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

    # Balance is a precondition of BOTH methods, so it is checked once here, ahead of the
    # method dispatch: Average-and-Range has no d2* to look up for unequal cell sizes
    # (RULE 11), and AIAG's ANOVA table is derived "assuming a balanced two-factor
    # factorial design" (Ch. III Sec. B).
    if not is_balanced:
        raise ValueError(
            f"Data is unbalanced. This Gage R&R engine requires equal trials per (part, appraiser) cell. "
            f"Found {min_replicates}–{max_replicates} trials across cells."
        )

    # Compute EV, AV, PV (and, for ANOVA, the interaction) by the requested method.
    # GRR differs between them: Average-and-Range cannot estimate the interaction, so it has
    # no term to add; ANOVA carries INT^2 (AIAG Appendix A, Table A 2).
    interaction: float | None = None
    interaction_f: float | None = None
    interaction_significant: bool | None = None
    if method == METHOD:
        ev, av, pv = _average_and_range_method(df)
        # The module constants, not the caller's string, reach the payload: consumers
        # compare against METHOD / METHOD_ANOVA by identity as well as by value.
        method_used, method_note = METHOD, METHOD_NOTE
        grr = float(np.sqrt(ev**2 + av**2))
    elif method == METHOD_ANOVA:
        ev, av, pv, interaction, interaction_f, interaction_significant = _anova_method(df)
        method_used, method_note = METHOD_ANOVA, METHOD_NOTE_ANOVA
        grr = float(np.sqrt(ev**2 + av**2 + interaction**2))
    else:
        raise ValueError(
            f"Unknown method: {method!r}. Supported: {METHOD!r}, {METHOD_ANOVA!r}."
        )

    # Total variation
    tv = float(np.sqrt(grr**2 + pv**2))

    # Overall mean
    mean = float(df["measurement"].mean())

    # %EV / %AV / %GRR / %PV vs study variation — AIAG's 100[component/TV] form
    # (Ch. III Sec. B "Indices"; RULE 7 / RULE 16). tv == 0 implies every component is
    # 0, so each ratio is 0/0 and all four are reported as inf, matching the existing
    # %GRR behaviour (RULE 13); _compute_verdict maps a non-finite %GRR to "Reject".
    if tv > 0:
        pev_study = (ev / tv) * 100
        pav_study = (av / tv) * 100
        pgrr_study = (grr / tv) * 100
        ppv_study = (pv / tv) * 100
    else:
        pev_study = pav_study = pgrr_study = ppv_study = float("inf")

    # %EV / %AV / %GRR / %PV vs tolerance (if provided). Each figure scales its own
    # numerator by _STUDY_VARIATION_SIGMA — tolerance/6 in AIAG's denominator (RULE 8,
    # #190). Never factor the constant out of an individual line: dropping it from any
    # one of them understates that figure 6x.
    pev_tolerance = None
    pav_tolerance = None
    pgrr_tolerance = None
    ppv_tolerance = None
    if tolerance is not None:
        pev_tolerance = (ev * _STUDY_VARIATION_SIGMA / tolerance) * 100
        pav_tolerance = (av * _STUDY_VARIATION_SIGMA / tolerance) * 100
        pgrr_tolerance = (grr * _STUDY_VARIATION_SIGMA / tolerance) * 100
        ppv_tolerance = (pv * _STUDY_VARIATION_SIGMA / tolerance) * 100

    # Number of distinct categories (independent of tolerance)
    ndc_value = _compute_ndc(grr, pv)

    # Verdict: when both %GRR-tolerance and %GRR-study exist, drive the verdict off
    # the more conservative (worse) of the two (SME resolution, W08-2 spec). ndc and
    # each %GRR are still reported individually via the return dict above.
    verdict_pgrr = max(pgrr_tolerance, pgrr_study) if pgrr_tolerance is not None else pgrr_study
    verdict = _compute_verdict(ndc_value, verdict_pgrr)

    return {
        "ev": float(ev),
        "av": float(av),
        "grr": grr,
        "pev_study": float(pev_study),
        "pav_study": float(pav_study),
        "pgrr_study": float(pgrr_study),
        "ppv_study": float(ppv_study),
        "pev_tolerance": float(pev_tolerance) if pev_tolerance is not None else None,
        "pav_tolerance": float(pav_tolerance) if pav_tolerance is not None else None,
        "pgrr_tolerance": float(pgrr_tolerance) if pgrr_tolerance is not None else None,
        "ppv_tolerance": float(ppv_tolerance) if ppv_tolerance is not None else None,
        "ndc": ndc_value,
        "verdict": verdict,
        "tv": tv,
        "pv": float(pv),
        "mean": mean,
        "n_parts": n_parts,
        "n_appraisers": n_appraisers,
        "n_trials": n_trials,
        "is_balanced": is_balanced,
        "method": method_used,
        "method_note": method_note,
        "interaction": interaction,
        "interaction_f": interaction_f,
        "interaction_significant": interaction_significant,
    }


def _average_and_range_method(df: pd.DataFrame) -> tuple[float, float, float]:
    """Compute EV, AV, and PV using the AIAG Average-and-Range method.

    All three components (and GRR/TV derived from them) are reported in raw
    sigma units (K = 1/d2*). The historical 5.15/6-sigma "study variation"
    multiplier is intentionally omitted: it would multiply EV, AV, PV, GRR,
    and TV identically, so it cancels out of %GRR = GRR/TV and ndc = 1.41*PV/GRR.

    Decomposes measurement variation into repeatability and reproducibility only:
    per AIAG MSA 4th Ed., Ch. III Sec. B ("Average and Range Method"), "variation due to
    the interaction between the appraiser and the part/gage is not accounted for in the
    analysis" — that interaction is absorbed into EV/AV/PV rather than estimated.

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


def _anova_method(df: pd.DataFrame) -> tuple[float, float, float, float, float, bool]:
    """Compute EV, AV, PV and the part x appraiser interaction by the AIAG ANOVA method.

    Crossed two-factor ANOVA with replication (AIAG MSA 4th Ed., Ch. III Sec. B,
    "Analysis of Variance (ANOVA) Method"; Appendix A, "Analysis of Variance Concepts").
    With n parts, k appraisers and r trials per cell, the classical decomposition is:

        SS_total   = sum (y - grand_mean)^2                     df = nkr - 1
        SS_parts   = kr * sum (part_mean - grand_mean)^2         df = n - 1
        SS_appr    = nr * sum (appr_mean - grand_mean)^2         df = k - 1
        SS_cells   = r  * sum (cell_mean - grand_mean)^2         (cell = part x appraiser)
        SS_AxP     = SS_cells - SS_parts - SS_appr               df = (n-1)(k-1)
        SS_e       = SS_total - SS_cells                         df = nk(r-1)

    Only the interaction row gets an F-ratio — Appendix A: "The F-ratio column is calculated
    only for the interaction in a MSA ANOVA; it is determined by the mean square of
    interaction divided by mean square error." A significant interaction gives the
    non-additive model of Table A 1; a non-significant one is pooled into equipment
    (error) per Appendix A's additive model, with SS_pool = SS_e + SS_AxP over
    (nkr - n - k + 1) degrees of freedom. See ASSUMPTIONS_LOG RULE 17 for the citations.

    Like `_average_and_range_method`, all components are returned in raw 1-sigma units;
    AIAG's Table A 2 prints them as 6-sigma spreads, and this engine applies the x6
    multiplier only on the tolerance basis (`_STUDY_VARIATION_SIGMA`, RULE 8).

    Args:
        df: DataFrame with columns part, appraiser, trial, measurement. Must be balanced
            and meet the minimum study size — both are enforced by `compute_gage_rr`
            before dispatch, so every source below has at least one degree of freedom.

    Returns:
        (ev, av, pv, interaction, interaction_f, interaction_significant) tuple.
    """
    n_parts = df["part"].nunique()
    n_appraisers = df["appraiser"].nunique()
    cell_means = df.groupby(["part", "appraiser"])["measurement"].mean()
    n_trials = int(df.groupby(["part", "appraiser"]).size().iloc[0])

    grand_mean = float(df["measurement"].mean())
    ss_total = float(((df["measurement"] - grand_mean) ** 2).sum())
    part_means = df.groupby("part")["measurement"].mean()
    ss_parts = float(n_appraisers * n_trials * ((part_means - grand_mean) ** 2).sum())
    appraiser_means = df.groupby("appraiser")["measurement"].mean()
    ss_appraiser = float(n_parts * n_trials * ((appraiser_means - grand_mean) ** 2).sum())
    ss_cells = float(n_trials * ((cell_means - grand_mean) ** 2).sum())
    ss_interaction = ss_cells - ss_parts - ss_appraiser
    ss_equipment = ss_total - ss_cells

    df_parts = n_parts - 1
    df_appraiser = n_appraisers - 1
    df_interaction = df_parts * df_appraiser
    df_equipment = n_parts * n_appraisers * (n_trials - 1)

    ms_parts = ss_parts / df_parts
    ms_appraiser = ss_appraiser / df_appraiser
    ms_interaction = ss_interaction / df_interaction
    ms_equipment = ss_equipment / df_equipment

    # F-test on the interaction only (Appendix A). alpha = _ANOVA_ALPHA is a convention, not
    # an AIAG requirement — see that constant.
    if ms_equipment > 0:
        interaction_f = ms_interaction / ms_equipment
        f_critical = float(stats.f.ppf(1 - _ANOVA_ALPHA, df_interaction, df_equipment))
        interaction_significant = bool(interaction_f > f_critical)
    else:
        # A perfectly repeatable gage (zero within-cell variation) leaves MS_e = 0 and the
        # F ratio undefined. An interaction is then infinitely large relative to error, so it
        # counts as significant — but only above _SS_CANCELLATION_FLOOR, or float cancellation
        # in SS_AxP alone would flip a no-interaction study to the non-additive model.
        interaction_significant = ss_interaction > _SS_CANCELLATION_FLOOR * ss_total
        interaction_f = float("inf") if interaction_significant else 0.0

    if interaction_significant:
        # Non-additive model, Table A 1: MS_AxP is the error term for the two main effects.
        variance_equipment = ms_equipment
        variance_interaction = (ms_interaction - ms_equipment) / n_trials
        variance_appraiser = (ms_appraiser - ms_interaction) / (n_parts * n_trials)
        variance_part = (ms_parts - ms_interaction) / (n_appraisers * n_trials)
    else:
        # Additive model: "the interaction term is pooled with the equipment (error) term."
        # df_pool == n*k*r - n - k + 1 (Appendix A, footnote 85).
        ms_pooled = (ss_equipment + ss_interaction) / (df_equipment + df_interaction)
        variance_equipment = ms_pooled
        variance_interaction = 0.0
        variance_appraiser = (ms_appraiser - ms_pooled) / (n_parts * n_trials)
        variance_part = (ms_parts - ms_pooled) / (n_appraisers * n_trials)

    # "For analysis purposes, the negative variance component is set to zero" (Appendix A) —
    # every component is a difference of mean squares (or, for equipment, a difference of sums
    # of squares), so sampling variation and float cancellation can each push one below zero.
    # Same clamp the Average-and-Range AV already uses (RULE 14).
    ev = float(np.sqrt(max(variance_equipment, 0.0)))
    av = float(np.sqrt(max(variance_appraiser, 0.0)))
    pv = float(np.sqrt(max(variance_part, 0.0)))
    interaction = float(np.sqrt(max(variance_interaction, 0.0)))

    return ev, av, pv, interaction, float(interaction_f), bool(interaction_significant)


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
    """Compute Number of Distinct Categories per AIAG MSA 4th Edition (Ch. III Sec. B).

    ndc = max(1, trunc(1.41 * (PV / GRR)))

    Args:
        grr: GR&R value (must be > 0).
        pv: Part Variation (must be > 0).

    Returns:
        ndc as an int, clamped to [1, 100] for valid positive inputs, or 0 if inputs are non-positive.
    """
    if grr <= 0 or pv <= 0:
        return 0
    ndc_raw = 1.41 * (pv / grr)
    ndc_int = int(ndc_raw)  # truncate toward zero
    return max(1, min(ndc_int, 100))  # Maximum of 1 or calculated value truncated, clamped to 100


def _compute_verdict(ndc: int, pgrr: float) -> str:
    """Compute AIAG verdict based on ndc and a single %GRR figure.

    Args:
        ndc: Number of distinct categories.
        pgrr: %GRR to apply the thresholds to (callers pass whichever figure —
            or combination of %GRR-tolerance and %GRR-study — should drive the verdict).

    Returns:
        "Accept", "Marginal", or "Reject".

    Logic — the %GRR bands and the ndc >= 5 threshold are AIAG's; the ndc sub-bands are not:
    - Accept: ndc >= 5 AND %GRR < 10%
    - Marginal: (ndc 2-4) OR (10% <= %GRR <= 30%)
    - Reject: ndc < 2 OR %GRR > 30%

    AIAG MSA 4th Ed. publishes the 10/30 %GRR bands (Ch. II Sec. D, Table II-D 1) and a single
    ndc rule -- "This value should be greater than or equal to 5" (Ch. II Sec. D; repeated in
    Ch. III Sec. B). It publishes NO band between 5 and zero: the "ndc 2-4 -> Marginal" and
    "ndc < 2 -> Reject" splits below are this platform's internal design choice, not AIAG's, and
    were previously mislabelled here as "Logic (AIAG MSA)" (#223, audit A10-a -- wording only, the
    branches are unchanged). Neither split loosens AIAG: nothing under ndc = 5 returns "Accept".
    See ASSUMPTIONS_LOG RULE 9 / RULE 10.
    """
    # Hard reject conditions
    if ndc < 2:
        return "Reject"

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
