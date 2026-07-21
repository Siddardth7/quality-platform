"""
secom_app/selection.py
SECOM signal-selection screen — which sensor columns are amenable to SPC/capability.

There is no AIAG/quality-standard table for "which sensor signals to chart"; this
is a data-screening step, not a published standard. Three filters run in order
(first failing rule wins the reported ``reason`` — see SME resolutions, `.pipeline`
issue #65, and ``apps/secom/docs/ASSUMPTIONS_LOG.md`` for source citations):

  1. Missingness floor (``MIN_NON_MISSING``, default 100 non-missing values).
     Anchored to AIAG SPC's capability sample-size guidance (~100 individual
     points). No imputation: retained signals are analyzed on present values only.
  2. Zero-variance drop (definitional): a signal with no variation on its present
     values (including an all-NaN column) is undefined for a control chart or
     Cp/Cpk (Cp = (USL-LSL)/6*sigma is undefined at sigma=0).
  3. Near-zero-variance (NZV) drop: ``freq_ratio >= NZV_FREQ_RATIO`` AND
     ``percent_unique <= NZV_PERCENT_UNIQUE`` (Kuhn & Johnson, *Applied Predictive
     Modeling*, 2013, Section 3.5 / ``caret::nearZeroVar``). This is a third-party
     reproduction, NOT a quality standard.

Spec limits (USL/LSL) are deliberately out of scope here (SECOM ships none) —
this module selects signals *suitable for* capability, it does not compute Cp/Cpk
or fabricate limits. That decision is deferred to a later capability issue.
"""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

__all__ = [
    "SelectionCriteria",
    "select_signals",
    "MIN_NON_MISSING",
    "NZV_FREQ_RATIO",
    "NZV_PERCENT_UNIQUE",
]

#: OQ1 (SME-locked): keep a signal only with at least this many present values.
#: Anchored to AIAG SPC capability sample-size guidance (~100 individual points).
MIN_NON_MISSING = 100

#: OQ2 (SME-locked): caret::nearZeroVar defaults (Kuhn & Johnson, 2013, Sec. 3.5).
#: Third-party heuristic reproduction, not a quality standard.
NZV_FREQ_RATIO = 19.0
NZV_PERCENT_UNIQUE = 0.10


@dataclass(frozen=True)
class SelectionCriteria:
    min_non_missing: int = MIN_NON_MISSING
    nzv_freq_ratio: float = NZV_FREQ_RATIO
    nzv_percent_unique: float = NZV_PERCENT_UNIQUE


def _freq_ratio(present: pd.Series) -> float:
    """Ratio of the most-common present value's count to the 2nd-most-common's.

    ``inf`` if there is only one distinct present value (the zero-variance check
    upstream already drops that case, but this stays well-defined regardless).
    """
    counts = present.value_counts()
    if len(counts) < 2:
        return float("inf")
    return float(counts.iloc[0] / counts.iloc[1])


def _percent_unique(present: pd.Series) -> float:
    """Fraction of present values that are distinct (n_distinct / n_present)."""
    n_present = len(present)
    if n_present == 0:
        return 0.0
    return float(present.nunique() / n_present)


def select_signals(
    features: pd.DataFrame,
    criteria: SelectionCriteria = SelectionCriteria(),
) -> pd.DataFrame:
    """First-pass screen for SPC/capability-amenable signals.

    Returns an audit table, one row per input signal, so every inclusion/exclusion
    is explainable: ``[signal, n_present, missing_frac, n_distinct, variance,
    freq_ratio, percent_unique, status, reason]``. ``status`` is ``"keep"`` or
    ``"drop"``; ``reason`` names the first failing rule
    (``"too_missing"`` | ``"constant"`` | ``"near_zero_variance"`` | ``"ok"``).
    Pure; no imputation.
    """
    n_rows = len(features)
    rows: list[dict[str, object]] = []
    for signal in features.columns:
        col = features[signal]
        present = col.dropna()
        n_present = int(len(present))
        missing_frac = float((n_rows - n_present) / n_rows) if n_rows else 0.0
        n_distinct = int(present.nunique())
        variance = float(present.var(ddof=1)) if n_present >= 2 else 0.0
        freq_ratio = _freq_ratio(present)
        percent_unique = _percent_unique(present)

        if n_present < criteria.min_non_missing:
            status, reason = "drop", "too_missing"
        elif variance == 0.0:
            status, reason = "drop", "constant"
        elif (
            freq_ratio >= criteria.nzv_freq_ratio
            and percent_unique <= criteria.nzv_percent_unique
        ):
            status, reason = "drop", "near_zero_variance"
        else:
            status, reason = "keep", "ok"

        rows.append(
            {
                "signal": signal,
                "n_present": n_present,
                "missing_frac": missing_frac,
                "n_distinct": n_distinct,
                "variance": variance,
                "freq_ratio": freq_ratio,
                "percent_unique": percent_unique,
                "status": status,
                "reason": reason,
            }
        )

    return pd.DataFrame(rows)
