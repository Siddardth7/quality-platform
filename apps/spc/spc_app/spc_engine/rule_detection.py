"""Control chart rule detection."""

from __future__ import annotations

#: Chart types on which Western Electric / Nelson run-rules are statistically
#: valid (Shewhart charts — independent points). Keyed on the same display
#: strings the Control Charts page selector already uses (`CHART_OPTIONS`).
SHEWHART_CHART_TYPES: frozenset[str] = frozenset(
    {"Xbar-R", "Xbar-S", "I-MR", "p", "c", "u"}
)


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

    violations: list[dict[str, int | str]] = []
    centered = [point - cl for point in points]

    for index, value in enumerate(centered):
        if abs(value) > (3.0 * sigma):
            violations.append(_violation(index, "Western Electric Rule 1"))

    for end_index in range(2, len(centered)):
        window = centered[end_index - 2 : end_index + 1]
        if _count_same_side(window, 2.0 * sigma, 2):
            violations.append(_violation(end_index, "Western Electric Rule 2"))

    for end_index in range(4, len(centered)):
        window = centered[end_index - 4 : end_index + 1]
        if _count_same_side(window, 1.0 * sigma, 4):
            violations.append(_violation(end_index, "Western Electric Rule 3"))

    for end_index in range(7, len(centered)):
        window = centered[end_index - 7 : end_index + 1]
        if all(value > 0 for value in window) or all(value < 0 for value in window):
            violations.append(_violation(end_index, "Western Electric Rule 4"))

    return violations


def detect_nelson_violations(points: list[float], cl: float, sigma: float) -> list[dict[str, int | str]]:
    if sigma <= 0:
        raise ValueError("sigma must be positive")

    violations = list(detect_we_violations(points, cl=cl, sigma=sigma))
    centered = [point - cl for point in points]

    for end_index in range(5, len(points)):
        window = points[end_index - 5 : end_index + 1]
        if _is_strictly_monotonic(window):
            violations.append(_violation(end_index, "Nelson Rule 5"))

    for end_index in range(13, len(points)):
        window = points[end_index - 13 : end_index + 1]
        if _is_alternating(window):
            violations.append(_violation(end_index, "Nelson Rule 6"))

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


def _count_same_side(window: list[float], threshold: float, minimum_count: int) -> bool:
    positive_hits = sum(value > threshold for value in window)
    negative_hits = sum(value < -threshold for value in window)
    return (
        (positive_hits >= minimum_count and negative_hits == 0)
        or (negative_hits >= minimum_count and positive_hits == 0)
    )


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
