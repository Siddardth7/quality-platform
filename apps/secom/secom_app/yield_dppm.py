"""
secom_app/yield_dppm.py
SECOM yield / DPPM + association Pareto of failing signals (W09-5, #69).

SME resolutions (`.pipeline/spec.md`, locked 2026-07-23), each labelled:

- **OQ1a (SME-set, events over wafer-count):** the Pareto ranks each kept
  signal by the *number of SPC special-cause violation events* landing on
  failed wafers — a signal firing 3 rules on one failed wafer counts 3. This
  matches SPC's own "special-cause hit" atom (the same unit `charts.py`
  already counts in `SignalControlChart.violations`); it is NOT a count of
  distinct failed wafers flagged.
- **OQ1b (SME-set, standard Pareto practice):** kept signals with 0
  fail-associated violations are dropped from the Pareto table entirely,
  not kept as zero rows.
- **OQ2 (SME-set, added scope):** this issue also ships a Streamlit page
  (`secom_app/pages/yield_dppm.py`) rendering this engine's typed output —
  the series' engine-only default (W09-1..W09-4) is overridden here because
  the issue title itself said "view." The page is a thin, non-gated renderer;
  all logic stays in this module.

**DPPM, not DPMO (SME red line on honesty).** SECOM carries exactly one
pass/fail verdict per wafer (unit level) — there is no defects-and-
opportunities count per unit. So `YieldSummary.dppm` is **defective units
per million (DPPM/PPM)**, industry-standard semiconductor/Six-Sigma yield
vocabulary, honestly labelled as a convention — it is **not** DPMO (defects
per million *opportunities*), which this dataset cannot support. Yield and
DPPM are definitional arithmetic (pass/total, fails/total x 1e6); there is no
acceptance threshold invented or implied here (no "yield must exceed X").

**Association Pareto, NOT root cause (SME red line).** SECOM's label is a
single wafer-level verdict; it does not attribute a failure to any signal.
`failing_signal_pareto()` reuses W09-2's SPC violation detection
(`control_charts_for_selection`, `secom_app/charts.py`) and asks only "among
failed wafers, which kept signals were most often out-of-control?" — an
association/screening signal, not a proven cause of any failure. No anomaly
or Pareto math is re-derived here beyond the cumulative-% arithmetic; this
module's only new logic is the violation -> failed-wafer-row mapping and the
count/rank/cumulative bookkeeping.

**Applied In:** RULE 12 (yield/DPPM, DPPM-not-DPMO) and RULE 13 (association
Pareto construction) in `apps/secom/docs/ASSUMPTIONS_LOG.md`.
"""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from secom_app.charts import Ruleset, control_charts_for_selection
from secom_app.ingest import FAIL, PASS, SecomDataset

__all__ = ["YieldSummary", "yield_summary", "failing_signal_pareto"]

_PARETO_COLUMNS = ["signal", "n_fail_violations", "pct", "cumulative_pct"]


@dataclass(frozen=True)
class YieldSummary:
    n_total: int
    n_pass: int
    n_fail: int
    yield_fraction: float  # n_pass / n_total
    yield_pct: float  # yield_fraction * 100.0
    dppm: float  # (n_fail / n_total) * 1_000_000.0 — defective UNITS per million


def yield_summary(labels: pd.Series) -> YieldSummary:
    """Pass/fail counts -> yield + DPPM (defective-units PPM, not DPMO).

    Takes a bare Series (not a full `SecomDataset`) so it works on any
    label subset/slice. Raises `ValueError` on an empty series (yield/DPPM
    undefined at n=0) or a label outside `{PASS, FAIL}` (mirrors
    `ingest.load_secom`'s own domain guard — a caller-built Series is not
    guaranteed to have come through it).
    """
    n_total = int(len(labels))
    if n_total == 0:
        raise ValueError("yield/DPPM undefined on an empty label series (n_total=0).")

    bad = ~labels.isin([PASS, FAIL])
    if bad.any():
        bad_values = sorted(set(labels[bad]))
        raise ValueError(
            f"labels must be in {{{PASS}, {FAIL}}}; found out-of-domain value(s): {bad_values}"
        )

    n_pass = int((labels == PASS).sum())
    n_fail = int((labels == FAIL).sum())
    yield_fraction = n_pass / n_total

    return YieldSummary(
        n_total=n_total,
        n_pass=n_pass,
        n_fail=n_fail,
        yield_fraction=yield_fraction,
        yield_pct=yield_fraction * 100.0,
        dppm=(n_fail / n_total) * 1_000_000.0,
    )


def failing_signal_pareto(
    dataset: SecomDataset,
    audit: pd.DataFrame,
    ruleset: Ruleset = "nelson",
) -> pd.DataFrame:
    """Association Pareto (NOT root cause): among failed wafers, rank kept
    signals by how often they were out-of-control, reusing W09-2 SPC
    violation detection (`control_charts_for_selection`) — no anomaly rule
    is re-derived here.

    Columns: `[signal, n_fail_violations, pct, cumulative_pct]`, ranked by
    `n_fail_violations` descending, ties broken by `signal` ascending (OQ1a:
    counts violation *events*, not distinct failed wafers). Signals with zero
    fail-associated violations are omitted (OQ1b). Returns an empty,
    correctly-columned DataFrame if there are no kept signals in `audit` or
    no kept signal has any fail-associated violation (guards the
    divide-by-zero in `pct`/`cumulative_pct`).
    """
    kept_signals = audit.loc[audit["status"] == "keep", "signal"]
    if kept_signals.empty:
        return pd.DataFrame(columns=_PARETO_COLUMNS)

    charts = control_charts_for_selection(dataset.features, audit, ruleset=ruleset)
    fail_rows = set(dataset.labels.index[dataset.labels == FAIL])

    counts: dict[str, int] = {}
    for signal, chart in charts.items():
        # ponytail: violation["index"] is positional into the present,
        # run-concatenated values charted for this signal (charts.py:146-148),
        # NOT a row label into `dataset.features`. Map back via the signal's
        # own present-value row index or a signal with interior NaNs
        # mis-attributes. Relies on charts.py charting present values in row
        # order (true today).
        original_rows = dataset.features.index[dataset.features[signal].notna()]
        n_fail_violations = sum(
            1
            for violation in chart.violations
            if original_rows[int(violation["index"])] in fail_rows
        )
        if n_fail_violations > 0:
            counts[signal] = n_fail_violations

    if not counts:
        return pd.DataFrame(columns=_PARETO_COLUMNS)

    total = sum(counts.values())
    ranked = sorted(counts.items(), key=lambda item: (-item[1], item[0]))

    cumulative = 0
    records = []
    for signal, n_fail_violations in ranked:
        cumulative += n_fail_violations
        records.append(
            {
                "signal": signal,
                "n_fail_violations": n_fail_violations,
                "pct": (n_fail_violations / total) * 100.0,
                "cumulative_pct": (cumulative / total) * 100.0,
            }
        )
    return pd.DataFrame(records, columns=_PARETO_COLUMNS)
