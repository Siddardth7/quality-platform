"""
secom_app/charts.py
SECOM signal -> existing SPC I-MR engine (W09-2, #66).

Wires SECOM sensor columns into the platform's already-tested SPC engine
(`apps/spc/spc_app/spc_engine/`, reused read-only — see `apps/secom/CLAUDE.md`
sys.path shim in `conftest.py`). This module does NOT reimplement control-limit
math or rule detection; it only adapts the SECOM data shape (NaN-preserving,
one column per sensor) into the shape the engine expects.

SME resolutions (`.pipeline/spec-66.md`, locked 2026-07-21), each labelled:

- **OQ1 (standard):** I-MR (Individuals + Moving Range, MR window 2) — SECOM is
  one reading per production run, no rational subgroup. `compute_imr` is reused
  as-is for the per-run moving-range math and its xbar.
- **OQ2 (SME-set, rigorous option):** lag-1 autocorrelation is computed per
  charted signal and attached as a diagnostic flag (`lag1_autocorr`,
  `autocorr_flag`) on a documented, sample-size-adjusted threshold. This is
  DIAGNOSTIC ONLY — it never filters, models, or gates the chart.
- **OQ3 (applied default):** normality is not checked here; deferred, as in
  W09-1's ASSUMPTIONS_LOG (no gate).
- **OQ4 (applied default):** limits are per-signal, single-pass (no Phase-I/
  Phase-II split) — each signal's control limits come from that signal's own
  present data only.
- **OQ5 (SME-set, time-faithful option):** a signal's present values are split
  into maximal contiguous (NaN-free) runs before any moving-range math, so a
  moving range is NEVER computed across a missing cell. The within-run moving
  ranges are pooled into one `mrbar` -> one `sigma_hat` -> one set of control
  limits for the signal (single UCL/LCL on the chart); a run of length 1
  contributes no moving range.
- **OQ6 (applied default):** the batch helper charts every `status=="keep"`
  signal from a `select_signals()` audit; no shortlist policy here.

#65 RED LINE (unchanged): SECOM ships no USL/LSL/tolerances. This module never
calls `compute_capability` and never produces Cp/Cpk/Pp/Ppk. Control-chart
limits (UCL/LCL from the moving range) are data-computed I-MR output, not spec
limits, and stay on the right side of that line.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Literal

import numpy as np
import pandas as pd

from spc_app.spc_engine.constants import IMR_D2, IMR_D4, IMR_E2
from spc_app.spc_engine.control_charts import ImrResult, compute_imr
from spc_app.spc_engine.rule_detection import detect_nelson_violations, detect_we_violations

__all__ = [
    "SignalControlChart",
    "control_chart_for_signal",
    "control_charts_for_selection",
    "Ruleset",
]

Ruleset = Literal["we", "nelson"]

#: OQ2 (SME-set): Bartlett's large-sample approximate 95% white-noise bound for
#: a lag-1 autocorrelation estimate (Box, Jenkins & Reinsel, *Time Series
#: Analysis*; the same diagnostic Montgomery's SPC text cites for checking the
#: I-MR independence assumption). N-dependent so it scales with each signal's
#: own present-value count rather than a single fixed cutoff.
AUTOCORR_Z = 1.96


@dataclass(frozen=True)
class SignalControlChart:
    signal: str
    n_used: int  # non-NaN points actually charted (== len(imr["values"]))
    imr: ImrResult  # reused engine result shape: limits, MR, xbar, sigma_hat
    violations: list[dict[str, int | str]]  # special-cause hits on the individuals chart
    lag1_autocorr: float  # OQ2: Pearson lag-1 autocorrelation of the charted values
    autocorr_flag: bool  # OQ2: |lag1_autocorr| exceeds the sample-size-adjusted bound


def _present_runs(arr: np.ndarray) -> list[np.ndarray]:
    """Split a 1-D float array into maximal contiguous non-NaN runs (OQ5).

    A moving range must never span a missing cell, so gaps (single or
    consecutive NaNs, at the start/end/middle of the series) split the run
    here, before any moving-range math happens downstream.
    """
    present = ~np.isnan(arr)
    runs: list[np.ndarray] = []
    start: int | None = None
    for index, is_present in enumerate(present):
        if is_present and start is None:
            start = index
        elif not is_present and start is not None:
            runs.append(arr[start:index])
            start = None
    if start is not None:
        runs.append(arr[start:])
    return runs


def _pooled_moving_ranges(runs: list[np.ndarray]) -> list[float]:
    """OQ5: moving ranges within each run only, pooled across runs.

    Reuses `compute_imr`'s own moving-range calculation per run (rather than
    re-deriving it) so the only new logic here is *which* points a moving
    range is allowed to span. A run of length 1 contributes no moving range.
    """
    pooled: list[float] = []
    for run in runs:
        if run.size >= 2:
            pooled.extend(compute_imr(run.tolist())["moving_ranges"])
    return pooled


def _lag1_autocorrelation(values: list[float]) -> float:
    """Pearson lag-1 autocorrelation of a present-value series (OQ2).

    Computed gap-spanning over the full charted (dropna) series: this is a
    diagnostic-only statistic, not a control limit, so OQ5's run-break
    requirement (which governs moving-range math) does not apply here.
    """
    arr = np.asarray(values, dtype=float)
    centered = arr - arr.mean()
    denominator = float(np.sum(centered**2))
    if denominator == 0.0:
        return 0.0
    numerator = float(np.sum(centered[:-1] * centered[1:]))
    return numerator / denominator


def control_chart_for_signal(
    features: pd.DataFrame,
    signal: str,
    ruleset: Ruleset = "nelson",
) -> SignalControlChart:
    """Run one SECOM sensor column through the existing I-MR engine (OQ1: individuals).

    Present (non-NaN) values in row/time order, moving ranges broken at gaps
    (OQ5). Raises ValueError if `signal` not in `features`, or via
    `compute_imr` if fewer than 2 present values, or via `detect_*` if
    `sigma_hat<=0` (a constant present series — already screened out by
    `select_signals`, but guarded here for standalone safety)."""
    if signal not in features.columns:
        raise ValueError(f"signal {signal!r} not found in features")

    column_arr = features[signal].to_numpy(dtype=float)
    runs = _present_runs(column_arr)
    values = np.concatenate(runs).tolist() if runs else []

    engine_imr = compute_imr(values)  # validates length; xbar unaffected by OQ5 run-breaking
    moving_ranges = _pooled_moving_ranges(runs)
    mrbar = float(np.mean(moving_ranges)) if moving_ranges else 0.0
    xbar = engine_imr["xbar"]

    # Same AIAG constants/formula compute_imr applies (control_charts.py),
    # just fed the OQ5-pooled mrbar instead of a single gap-spanning diff.
    imr: ImrResult = {
        "values": engine_imr["values"],
        "moving_ranges": moving_ranges,
        "xbar": xbar,
        "mrbar": mrbar,
        "ucl_x": xbar + (IMR_E2 * mrbar),
        "lcl_x": xbar - (IMR_E2 * mrbar),
        "ucl_mr": IMR_D4 * mrbar,
        "lcl_mr": 0.0,
        "sigma_hat": mrbar / IMR_D2,
    }

    detect = detect_nelson_violations if ruleset == "nelson" else detect_we_violations
    violations = detect(imr["values"], cl=imr["xbar"], sigma=imr["sigma_hat"])

    lag1 = _lag1_autocorrelation(imr["values"])
    autocorr_flag = abs(lag1) > (AUTOCORR_Z / math.sqrt(len(imr["values"])))

    return SignalControlChart(
        signal=signal,
        n_used=len(imr["values"]),
        imr=imr,
        violations=violations,
        lag1_autocorr=lag1,
        autocorr_flag=autocorr_flag,
    )


def control_charts_for_selection(
    features: pd.DataFrame,
    audit: pd.DataFrame,  # output of select_signals()
    ruleset: Ruleset = "nelson",
) -> dict[str, SignalControlChart]:
    """Chart every status=="keep" signal from the selection audit (OQ6: all kept).

    Consumes the #65 selection contract -> SPC engine. Order follows the audit."""
    kept_signals = audit.loc[audit["status"] == "keep", "signal"]
    return {
        signal: control_chart_for_signal(features, signal, ruleset=ruleset)
        for signal in kept_signals
    }
