"""
secom_app/doe_screening.py
SECOM observational univariate effect screen (W11-1, #72).

**This is a screening ANALYSIS of association, NOT a designed experiment.**
SECOM is observational process-monitoring data — factor (sensor) levels are
passively recorded, never set or randomized. A real DOE screening *design*
(fractional factorial, Plackett-Burman, etc.) requires manipulated factor
levels, which SECOM cannot provide. There is no fabricated factor level, no
randomization, and no causal claim anywhere in this module: `screen_signals`
reports how far each kept signal's mean shifts between the FAIL and PASS
groups, in pooled-SD units, with a significance flag — an association signal,
not a proven cause of any failure (same posture as the W09-5 association
Pareto in `yield_dppm.py`).

SME resolutions (`.pipeline/spec.md`, locked 2026-07-24), each labelled:

- **Q1 (SME-set, parametric):** per candidate signal, on PRESENT values only
  (never imputed, split independently by label): `effect` is Cohen's d
  (Cohen 1988) — ``(mean_fail - mean_pass) / pooled_sd``, sign preserved as
  the direction of association (FAIL minus PASS). `p_value` is Welch's
  two-sample t-test (Welch 1947, `scipy.stats.ttest_ind(..., equal_var=False)`),
  chosen because the FAIL (~104) and PASS (~1463) groups are very unequal in
  size and variance.
- **Q2 (SME-set, screening convention):** `q_value` is the
  Benjamini-Hochberg FDR-adjusted p-value (Benjamini & Hochberg 1995,
  `scipy.stats.false_discovery_control(..., method="bh")`) across the tested
  candidate set; `significant` = ``q_value < ALPHA``. `ALPHA = 0.05` is a
  **screening convention, NOT a quality-standard threshold** — there is no
  AIAG/published quality-standard table for this analysis, same posture as
  `selection.py`'s NZV heuristic.
- **Q3 (SME-set, no new selection):** candidate factors are exactly the
  `select_signals()` "keep" rows (`audit.loc[audit["status"] == "keep",
  "signal"]`, same access as `yield_dppm.py:121`) — no Pareto-ranked subset,
  no new factor set invented.
- **Q4 (SME-set, engine-only):** no Streamlit page. Series precedent is
  engine-only (W09-1..W09-4); this issue asks for an "analysis / report",
  not a "view".

No statistic is re-derived by hand here — `scipy.stats` supplies the
t-distribution and FDR math (Cohen's d itself is definitional arithmetic on
means/pooled-SD, not a distributional computation).

**Applied In:** RULE 14 in `apps/secom/docs/ASSUMPTIONS_LOG.md`.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd
from scipy import stats

from secom_app.ingest import FAIL, PASS, SecomDataset

__all__ = ["ScreeningResult", "screen_signals", "ALPHA", "MIN_GROUP_N", "SCREEN_COLUMNS"]

SCREEN_COLUMNS = [
    "signal",
    "n_pass",
    "n_fail",
    "mean_pass",
    "mean_fail",
    "effect",  # Cohen's d (FAIL minus PASS, pooled-SD units); sign = direction
    "p_value",  # Welch two-sample t-test
    "q_value",  # Benjamini-Hochberg FDR-adjusted p across the candidate set
    "significant",  # bool: q_value < ALPHA
]

#: Screening convention (BH-FDR), NOT a quality-standard threshold.
ALPHA = 0.05

#: Per-group present-value floor below which an effect/test is undefined.
MIN_GROUP_N = 2

_METHOD = "welch_t + cohens_d, BH-FDR"


@dataclass(frozen=True)
class ScreeningResult:
    alpha: float
    method: str  # names the exact analysis, e.g. "welch_t + cohens_d, BH-FDR"
    n_candidates: int  # candidate factors screened
    n_significant: int
    table: pd.DataFrame  # columns = SCREEN_COLUMNS, ranked by |effect| desc, tie -> signal asc


def _empty_result(alpha: float) -> ScreeningResult:
    return ScreeningResult(
        alpha=alpha,
        method=_METHOD,
        n_candidates=0,
        n_significant=0,
        table=pd.DataFrame(columns=SCREEN_COLUMNS),
    )


def screen_signals(
    dataset: SecomDataset,
    audit: pd.DataFrame,
    alpha: float = ALPHA,
) -> ScreeningResult:
    """Observational univariate effect screen of pass/fail on candidate signals.

    NOT a designed experiment, NOT causal. Candidates are the "keep" rows of
    `audit` (`select_signals()` output). Present values only, split
    independently per label — never imputed. A candidate with fewer than
    `MIN_GROUP_N` present values in either group, or zero pooled variance,
    gets `effect`/`p_value`/`q_value` = NaN and `significant = False`, and is
    excluded from the Benjamini-Hochberg input so it doesn't dilute the
    correction. Ranked by `|effect|` descending, ties broken by `signal`
    ascending; NaN-effect rows sort last.
    """
    candidates = audit.loc[audit["status"] == "keep", "signal"]
    if candidates.empty:
        return _empty_result(alpha)

    pass_mask = dataset.labels == PASS
    fail_mask = dataset.labels == FAIL

    rows: list[dict[str, object]] = []
    p_values: list[float] = []
    p_value_positions: list[int] = []
    for signal in candidates:
        pass_values = dataset.features.loc[pass_mask, signal].dropna()
        fail_values = dataset.features.loc[fail_mask, signal].dropna()
        n_pass, n_fail = int(len(pass_values)), int(len(fail_values))
        mean_pass = float(pass_values.mean()) if n_pass else float("nan")
        mean_fail = float(fail_values.mean()) if n_fail else float("nan")

        effect: float = float("nan")
        p_value: float = float("nan")
        if n_pass >= MIN_GROUP_N and n_fail >= MIN_GROUP_N:
            var_pass = float(pass_values.var(ddof=1))
            var_fail = float(fail_values.var(ddof=1))
            pooled_sd = float(
                np.sqrt(((n_pass - 1) * var_pass + (n_fail - 1) * var_fail) / (n_pass + n_fail - 2))
            )
            if pooled_sd > 0.0:
                effect = (mean_fail - mean_pass) / pooled_sd
                p_value = float(
                    stats.ttest_ind(fail_values, pass_values, equal_var=False).pvalue
                )

        row: dict[str, object] = {
            "signal": signal,
            "n_pass": n_pass,
            "n_fail": n_fail,
            "mean_pass": mean_pass,
            "mean_fail": mean_fail,
            "effect": effect,
            "p_value": p_value,
        }
        if not np.isnan(p_value):
            p_value_positions.append(len(rows))
            p_values.append(p_value)
        rows.append(row)

    q_values = np.full(len(rows), float("nan"))
    if p_values:
        q_values[p_value_positions] = stats.false_discovery_control(p_values, method="bh")

    for row, q_value in zip(rows, q_values, strict=True):
        row["q_value"] = float(q_value)
        row["significant"] = bool(q_value < alpha) if not np.isnan(q_value) else False

    table = pd.DataFrame(rows, columns=SCREEN_COLUMNS)
    table = table.assign(_abs_effect=table["effect"].abs()).sort_values(
        by=["_abs_effect", "signal"], ascending=[False, True], na_position="last"
    )
    table = table.drop(columns="_abs_effect").reset_index(drop=True)

    return ScreeningResult(
        alpha=alpha,
        method=_METHOD,
        n_candidates=len(rows),
        n_significant=int(table["significant"].sum()),
        table=table,
    )
