"""Control chart rule detection.

Promoted verbatim out of `spc_app.spc_engine.rule_detection` (audit A12, #205) so
SECOM and the future API detect run-rule violations with the same code the SPC app
does; `spc_app.spc_engine.rule_detection` re-exports it.
"""

from __future__ import annotations

from typing import Mapping

#: Chart types on which Western Electric / Nelson run-rules are statistically
#: valid (Shewhart charts — independent points). Keyed on the same display
#: strings the Control Charts page selector already uses (`CHART_OPTIONS` in
#: `spc_app/pages/control_charts.py`).
#:
#: DELIBERATELY INDEPENDENT of `quality_core.spc.constants.SPCChart` — do NOT
#: derive one from the other (#205, SME-confirmed). They answer different
#: questions: `SPCChart` is "charts we can render", this is "charts where WE/
#: Nelson run-rules are statistically valid". They are equal only by coincidence
#: today; the day an EWMA/CUSUM key enters `SPCChart`, deriving would silently
#: validate run-rules on autocorrelated points — the exact defect
#: `detect_violations` exists to prevent (see its docstring below).
SHEWHART_CHART_TYPES: frozenset[str] = frozenset(
    {"Xbar-R", "Xbar-S", "I-MR", "p", "c", "u"}
)

#: Zone/limit test labels, keyed by test (see `_zone_violations`).
WE_LABELS: Mapping[str, str] = {
    "beyond_3s": "Western Electric Rule 1",
    "two_of_three": "Western Electric Rule 2",
    "four_of_five": "Western Electric Rule 3",
    "run_same_side": "Western Electric Rule 4",
}
NELSON_LABELS: Mapping[str, str] = {
    "beyond_3s": "Nelson Rule 1",
    "two_of_three": "Nelson Rule 5",
    "four_of_five": "Nelson Rule 6",
    "run_same_side": "Nelson Rule 2",
}


def detect_violations(
    chart_type: str,
    points: list[float],
    cl: float,
    sigma: float,
    rule_set: str,
) -> list[dict[str, int | str]]:
    """Run WE/Nelson rules ONLY for Shewhart chart types.

    EWMA/CUSUM points are autocorrelated by construction, so WE/Nelson run-rules
    are statistically invalid on them (see docs/ASSUMPTIONS_LOG.md RULE 15) —
    those charts signal only on their own limit / decision-interval crossings.
    Returns [] for any non-Shewhart chart_type and for a non-positive sigma;
    never raises.
    """
    if chart_type not in SHEWHART_CHART_TYPES or sigma <= 0:
        return []
    if rule_set == "Nelson":
        return detect_nelson_violations(points, cl=cl, sigma=sigma)
    return detect_we_violations(points, cl=cl, sigma=sigma)


def detect_we_violations(points: list[float], cl: float, sigma: float) -> list[dict[str, int | str]]:
    if sigma <= 0:
        raise ValueError("sigma must be positive")

    centered = [point - cl for point in points]
    return _zone_violations(centered, sigma, WE_LABELS, run_length=8)


def detect_nelson_violations(points: list[float], cl: float, sigma: float) -> list[dict[str, int | str]]:
    if sigma <= 0:
        raise ValueError("sigma must be positive")

    centered = [point - cl for point in points]
    violations = _zone_violations(centered, sigma, NELSON_LABELS, run_length=9)

    for end_index in range(5, len(points)):
        window = points[end_index - 5 : end_index + 1]
        if _is_strictly_monotonic(window):
            violations.append(_violation(end_index, "Nelson Rule 3"))

    for end_index in range(13, len(points)):
        window = points[end_index - 13 : end_index + 1]
        if _is_alternating(window):
            violations.append(_violation(end_index, "Nelson Rule 4"))

    for end_index in range(14, len(centered)):
        window = centered[end_index - 14 : end_index + 1]
        if all(abs(value) < sigma for value in window):
            violations.append(_violation(end_index, "Nelson Rule 7"))

    for end_index in range(7, len(centered)):
        window = centered[end_index - 7 : end_index + 1]
        if all(abs(value) > sigma for value in window) and any(value > 0 for value in window) and any(
            value < 0 for value in window
        ):
            violations.append(_violation(end_index, "Nelson Rule 8"))

    return violations


def _zone_violations(
    centered: list[float],
    sigma: float,
    labels: Mapping[str, str],
    run_length: int,
) -> list[dict[str, int | str]]:
    """Beyond-3sigma, 2-of-3-beyond-2sigma, 4-of-5-beyond-1sigma, and
    `run_length`-in-a-row-same-side, shared by both the Western Electric and
    Nelson rule sets (they differ only in labels and run length).
    """
    violations: list[dict[str, int | str]] = []

    for index, value in enumerate(centered):
        if abs(value) > (3.0 * sigma):
            violations.append(_violation(index, labels["beyond_3s"]))

    for end_index in range(2, len(centered)):
        window = centered[end_index - 2 : end_index + 1]
        if _count_same_side(window, 2.0 * sigma, 2):
            violations.append(_violation(end_index, labels["two_of_three"]))

    for end_index in range(4, len(centered)):
        window = centered[end_index - 4 : end_index + 1]
        if _count_same_side(window, 1.0 * sigma, 4):
            violations.append(_violation(end_index, labels["four_of_five"]))

    for end_index in range(run_length - 1, len(centered)):
        window = centered[end_index - (run_length - 1) : end_index + 1]
        if all(value > 0 for value in window) or all(value < 0 for value in window):
            violations.append(_violation(end_index, labels["run_same_side"]))

    return violations


def _count_same_side(window: list[float], threshold: float, minimum_count: int) -> bool:
    positive_hits = sum(value > threshold for value in window)
    negative_hits = sum(value < -threshold for value in window)
    return positive_hits >= minimum_count or negative_hits >= minimum_count


def _violation(index: int, rule: str) -> dict[str, int | str]:
    return {"index": index, "rule": rule}


def _is_strictly_monotonic(window: list[float]) -> bool:
    deltas = [current - previous for previous, current in zip(window, window[1:])]
    return all(delta > 0 for delta in deltas) or all(delta < 0 for delta in deltas)


def _is_alternating(window: list[float]) -> bool:
    deltas = [current - previous for previous, current in zip(window, window[1:])]
    if any(delta == 0 for delta in deltas):
        return False
    signs = [delta > 0 for delta in deltas]
    return all(left != right for left, right in zip(signs, signs[1:]))
