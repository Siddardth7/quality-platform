"""AIAG SPC chart constants.

Source: AIAG SPC Reference Manual, 4th Ed. (2005), control chart constants.

Promoted verbatim out of `spc_app.spc_engine.constants` (audit A12, #205) so every
tool shares one copy; `spc_app.spc_engine.constants` re-exports it. Values and
citations are unchanged — see `apps/spc/docs/ASSUMPTIONS_LOG.md`.
"""

from typing import Literal

# X-bar / R chart constants keyed by subgroup size.
XBAR_R_CONSTANTS = {
    2: {"A2": 1.880, "D3": 0.000, "D4": 3.267, "d2": 1.128},
    3: {"A2": 1.023, "D3": 0.000, "D4": 2.574, "d2": 1.693},
    4: {"A2": 0.729, "D3": 0.000, "D4": 2.282, "d2": 2.059},
    5: {"A2": 0.577, "D3": 0.000, "D4": 2.114, "d2": 2.326},
    6: {"A2": 0.483, "D3": 0.000, "D4": 2.004, "d2": 2.534},
    7: {"A2": 0.419, "D3": 0.076, "D4": 1.924, "d2": 2.704},
    8: {"A2": 0.373, "D3": 0.136, "D4": 1.864, "d2": 2.847},
    9: {"A2": 0.337, "D3": 0.184, "D4": 1.816, "d2": 2.970},
    10: {"A2": 0.308, "D3": 0.223, "D4": 1.777, "d2": 3.078},
}

# X-bar / S chart constants keyed by subgroup size.
XBAR_S_CONSTANTS = {
    2: {"A3": 2.659, "B3": 0.000, "B4": 3.267, "c4": 0.7979},
    3: {"A3": 1.954, "B3": 0.000, "B4": 2.568, "c4": 0.8862},
    4: {"A3": 1.628, "B3": 0.000, "B4": 2.266, "c4": 0.9213},
    5: {"A3": 1.427, "B3": 0.000, "B4": 2.089, "c4": 0.9400},
    6: {"A3": 1.287, "B3": 0.030, "B4": 1.970, "c4": 0.9515},
    7: {"A3": 1.182, "B3": 0.118, "B4": 1.882, "c4": 0.9594},
    8: {"A3": 1.099, "B3": 0.185, "B4": 1.815, "c4": 0.9650},
    9: {"A3": 1.032, "B3": 0.239, "B4": 1.761, "c4": 0.9693},
    10: {"A3": 0.975, "B3": 0.284, "B4": 1.716, "c4": 0.9727},
    11: {"A3": 0.927, "B3": 0.321, "B4": 1.679, "c4": 0.9754},
    12: {"A3": 0.886, "B3": 0.354, "B4": 1.646, "c4": 0.9776},
}

# Individuals / Moving Range chart constants for moving range size 2.
IMR_E2 = 2.660
IMR_D4 = 3.267
IMR_D2 = 1.128

# Phase I baseline minimums (see docs/ASSUMPTIONS_LOG.md RULE 11).
MIN_BASELINE_SUBGROUPS = 25  # NIST SEMATECH e-Handbook Sec 6.3.2.1 (Shewhart: >=25 samples of size 4)
MIN_BASELINE_INDIVIDUALS = 100  # Montgomery, Introduction to SQC, Ch. 6 (secondary, not NIST-quotable)

# EWMA chart defaults (see docs/ASSUMPTIONS_LOG.md RULE 12).
EWMA_DEFAULT_LAMBDA = 0.20   # NIST §6.3.2.4 (λ ≈ 0.2–0.3); Montgomery §9.2
EWMA_DEFAULT_L = 2.860       # paired with λ=0.20, Lucas & Saccucci (1990) / Montgomery Table 9.11

# Lucas & Saccucci (1990) λ/L pairings for ARL0 ≈ 370–500 (Montgomery Table 9.11).
# Do NOT use L=3 with a small λ — it inflates ARL0.
EWMA_L_BY_LAMBDA = {
    0.05: 2.615,
    0.10: 2.703,
    0.20: 2.860,
    0.25: 2.898,
    0.40: 3.054,
}

# CUSUM chart defaults (see docs/ASSUMPTIONS_LOG.md RULE 13).
CUSUM_DEFAULT_K = 0.5   # reference value = δσ/2 for a 1σ target shift — NIST §6.3.2.3
CUSUM_DEFAULT_H = 5.0   # decision interval in σ units; h≈4 or 5 — NIST §6.3.2.3; Montgomery §9.1
CUSUM_FIR_FRACTION = 0.5  # FIR/head-start = h/2 (50%) — Lucas & Crosier (1982)

# Non-normal capability + Cp/Cpk confidence intervals (see docs/ASSUMPTIONS_LOG.md RULE 14).
CAPABILITY_ALPHA = 0.05  # default two-sided significance for Cp/Cpk CIs — Montgomery Ch. 8 convention
BOXCOX_LAMBDA_CANDIDATES = (-1.0, -0.5, 0.0, 0.5, 1.0, 2.0)  # rounded λ snapped only if inside likelihood CI — NIST §6.5.2 / Box & Cox 1964
NONNORMAL_LOWER_PCTL = 0.00135  # lower capability percentile — NIST §6.1.6 (mimics −3σ)
NONNORMAL_UPPER_PCTL = 0.99865  # upper capability percentile — NIST §6.1.6 (mimics +3σ)
# Fitted-distribution percentile method (ISO 22514-2). Candidate families selected by min AIC.
PERCENTILE_FIT_CANDIDATES = ("lognorm", "weibull_min", "gamma", "johnsonsu")  # scipy.stats names; SME-locked full skew+kurtosis set, min-AIC selected
# Deterministic bootstrap for fitted-percentile Cp/Cpk CIs (Efron & Tibshirani 1993, percentile method).
BOOTSTRAP_SEED = 12345      # fixed seed → reproducible CIs (audit requirement); value arbitrary but pinned
BOOTSTRAP_RESAMPLES = 2000  # >=1000 for stable percentile CIs (Efron & Tibshirani); 2000 for tighter tails

#: SPC engine chart keys — the single home for the platform's chart vocabulary (#205 A12).
#: Promoted from controlplan_app.schema (a Literal, so mypy checks it) and consumed by
#: spc_app.control_plan_config via typing.get_args(). NOT the same vocabulary as
#: spc_app.schema.SPCChartKey (snake_case CSV keys) — see spc_app/schema.py:36-41.
SPCChart = Literal["Xbar-R", "Xbar-S", "I-MR", "p", "c", "u"]
