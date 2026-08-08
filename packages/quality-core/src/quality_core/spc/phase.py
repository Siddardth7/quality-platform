"""Phase I/II control-limit freezing (W10-1, #141).

Phase I is retrospective: a baseline is screened, assignable-cause points are
excluded, and limits are recomputed on what remains. Phase II freezes those
limits and applies them to future data — the limits no longer move with new
points. This module reuses `control_charts.compute_xbar_r/_s/_imr` on the
retained baseline rather than reimplementing any limit math.

Promoted out of `spc_app.spc_engine` by audit A12 (#205, PR 2 of 3) so the shared
core owns the Phase I/II freezing; `spc_app.spc_engine.phase` now re-exports it,
leaving existing SPC callers unchanged. Moved verbatim apart from import paths.
"""

from __future__ import annotations

from collections.abc import Sequence
from datetime import UTC, datetime
from typing import TypedDict

from quality_core.spc.constants import (
    IMR_D2,
    MIN_BASELINE_INDIVIDUALS,
    MIN_BASELINE_SUBGROUPS,
    XBAR_R_CONSTANTS,
    XBAR_S_CONSTANTS,
)
from quality_core.spc.control_charts import compute_imr, compute_xbar_r, compute_xbar_s


class ExcludedPoint(TypedDict):
    index: int
    cause: str


class FrozenLimits(TypedDict):
    chart_type: str
    n: int
    center_line: float
    sigma_hat: float
    sigma_method: str
    unbiasing_constant: float
    ucl_x: float
    lcl_x: float
    dispersion_center: float
    ucl_disp: float
    lcl_disp: float
    baseline_subgroup_count: int
    excluded: list[ExcludedPoint]
    phase_i_range: tuple[str, str] | None
    frozen_at: str
    baseline_adequate: bool
    baseline_note: str


def freeze_xbar_r(
    baseline: list[list[float]],
    *,
    excluded: Sequence[ExcludedPoint] = (),
    phase_i_range: tuple[str, str] | None = None,
    frozen_at: str | None = None,
) -> FrozenLimits:
    retained = _drop_excluded(baseline, excluded)
    result = compute_xbar_r(retained)
    subgroup_size = len(retained[0])
    d2 = XBAR_R_CONSTANTS[subgroup_size]["d2"]

    return _package(
        chart_type="xbar_r",
        n=subgroup_size,
        center_line=result["xbarbar"],
        sigma_hat=result["sigma_hat"],
        sigma_method="Rbar/d2",
        unbiasing_constant=d2,
        ucl_x=result["ucl_x"],
        lcl_x=result["lcl_x"],
        dispersion_center=result["rbar"],
        ucl_disp=result["ucl_r"],
        lcl_disp=result["lcl_r"],
        baseline_count=len(retained),
        min_floor=MIN_BASELINE_SUBGROUPS,
        excluded=excluded,
        phase_i_range=phase_i_range,
        frozen_at=frozen_at,
        unit="subgroups",
    )


def freeze_xbar_s(
    baseline: list[list[float]],
    *,
    excluded: Sequence[ExcludedPoint] = (),
    phase_i_range: tuple[str, str] | None = None,
    frozen_at: str | None = None,
) -> FrozenLimits:
    retained = _drop_excluded(baseline, excluded)
    result = compute_xbar_s(retained)
    subgroup_size = len(retained[0])
    c4 = XBAR_S_CONSTANTS[subgroup_size]["c4"]

    return _package(
        chart_type="xbar_s",
        n=subgroup_size,
        center_line=result["xbarbar"],
        sigma_hat=result["sigma_hat"],
        sigma_method="Sbar/c4",
        unbiasing_constant=c4,
        ucl_x=result["ucl_x"],
        lcl_x=result["lcl_x"],
        dispersion_center=result["sbar"],
        ucl_disp=result["ucl_s"],
        lcl_disp=result["lcl_s"],
        baseline_count=len(retained),
        min_floor=MIN_BASELINE_SUBGROUPS,
        excluded=excluded,
        phase_i_range=phase_i_range,
        frozen_at=frozen_at,
        unit="subgroups",
    )


def freeze_imr(
    baseline: list[float],
    *,
    excluded: Sequence[ExcludedPoint] = (),
    phase_i_range: tuple[str, str] | None = None,
    frozen_at: str | None = None,
) -> FrozenLimits:
    retained = _drop_excluded_1d(baseline, excluded)
    result = compute_imr(retained)

    return _package(
        chart_type="imr",
        n=1,
        center_line=result["xbar"],
        sigma_hat=result["sigma_hat"],
        sigma_method="MRbar/d2",
        unbiasing_constant=IMR_D2,
        ucl_x=result["ucl_x"],
        lcl_x=result["lcl_x"],
        dispersion_center=result["mrbar"],
        ucl_disp=result["ucl_mr"],
        lcl_disp=result["lcl_mr"],
        baseline_count=len(retained),
        min_floor=MIN_BASELINE_INDIVIDUALS,
        excluded=excluded,
        phase_i_range=phase_i_range,
        frozen_at=frozen_at,
        unit="individuals",
    )


def _require_frozen(frozen: FrozenLimits, expected_chart_type: str, n: int) -> None:
    """Guard shared by `control_charts.compute_*` when `frozen` is supplied.

    Phase II data must match the frozen baseline's chart type and subgroup size —
    limits computed for one shape cannot be legitimately applied to another.
    """
    if frozen["chart_type"] != expected_chart_type:
        raise ValueError(
            f"Frozen limits are for chart_type={frozen['chart_type']!r}, "
            f"expected {expected_chart_type!r}."
        )
    if frozen["n"] != n:
        raise ValueError(
            f"Frozen limits were computed for n={frozen['n']}, but the new data has n={n}."
        )


def _package(
    *,
    chart_type: str,
    n: int,
    center_line: float,
    sigma_hat: float,
    sigma_method: str,
    unbiasing_constant: float,
    ucl_x: float,
    lcl_x: float,
    dispersion_center: float,
    ucl_disp: float,
    lcl_disp: float,
    baseline_count: int,
    min_floor: int,
    excluded: Sequence[ExcludedPoint],
    phase_i_range: tuple[str, str] | None,
    frozen_at: str | None,
    unit: str,
) -> FrozenLimits:
    adequate = baseline_count >= min_floor
    note = (
        ""
        if adequate
        else f"Baseline has {baseline_count} {unit}; ≥{min_floor} recommended."
    )

    return {
        "chart_type": chart_type,
        "n": n,
        "center_line": float(center_line),
        "sigma_hat": float(sigma_hat),
        "sigma_method": sigma_method,
        "unbiasing_constant": float(unbiasing_constant),
        "ucl_x": float(ucl_x),
        "lcl_x": float(lcl_x),
        "dispersion_center": float(dispersion_center),
        "ucl_disp": float(ucl_disp),
        "lcl_disp": float(lcl_disp),
        "baseline_subgroup_count": baseline_count,
        "excluded": list(excluded),
        "phase_i_range": phase_i_range,
        "frozen_at": frozen_at or datetime.now(UTC).isoformat(),
        "baseline_adequate": adequate,
        "baseline_note": note,
    }


def _drop_excluded(
    baseline: list[list[float]], excluded: Sequence[ExcludedPoint]
) -> list[list[float]]:
    indices = _validate_excluded(len(baseline), excluded)
    return [row for i, row in enumerate(baseline) if i not in indices]


def _drop_excluded_1d(baseline: list[float], excluded: Sequence[ExcludedPoint]) -> list[float]:
    indices = _validate_excluded(len(baseline), excluded)
    return [value for i, value in enumerate(baseline) if i not in indices]


def _validate_excluded(baseline_len: int, excluded: Sequence[ExcludedPoint]) -> set[int]:
    indices: set[int] = set()
    for point in excluded:
        if not point["cause"].strip():
            raise ValueError("Excluded points must have a non-empty documented cause.")
        index = point["index"]
        if not (0 <= index < baseline_len):
            raise ValueError(f"Excluded index {index} is out of range for the baseline.")
        if index in indices:
            raise ValueError(f"Excluded index {index} is duplicated.")
        indices.add(index)
    return indices
