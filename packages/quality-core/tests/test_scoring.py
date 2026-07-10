"""
tests/test_scoring.py
Tests for quality_core/scoring.py — the shared scalar risk scorers (W05-3a).

These exercise the promoted AP table + `action_priority` and the `rpn` product
directly (not via the FMEA app's re-export shim) so the `quality_core.scoring`
coverage gate stands on its own tests, mirroring io/schema. They lock the
published AIAG-VDA lookups (representative cells + the monotonicity invariant that
guards against transcription error) and the fail-loud out-of-range contract.
"""

from __future__ import annotations

import pytest
from quality_core.scoring import (
    AP_ORDER,
    HIGH,
    LOW,
    MEDIUM,
    action_priority,
    rpn,
)

ALL_SCORES = range(1, 11)


# --- action_priority: representative published lookups -------------------------


@pytest.mark.parametrize(
    ("severity", "occurrence", "detection", "expected"),
    [
        (10, 10, 10, HIGH),   # worst case
        (9, 5, 1, MEDIUM),    # S 9-10 / O 4-5 / D 1 — handbook drops this to M
        (9, 1, 1, LOW),       # S 9-10 / O 1 / D 1 — rare + reliably detected
        (10, 1, 10, LOW),     # S 9-10 / O 1 / D 7-10 — rare: Low even if undetectable
        (10, 2, 2, LOW),      # high severity does not auto-escalate when rare + detectable
        (8, 7, 1, MEDIUM),    # S 7-8 / O 6-7 / D 1
        (5, 10, 1, MEDIUM),   # S 4-6 / O 8-10 / D 1
        (5, 5, 6, LOW),       # S 4-6 / O 4-5 / D 5-6
        (3, 10, 10, MEDIUM),  # S 2-3 / O 8-10 / D 7-10
        (3, 6, 10, LOW),      # S 2-3 / O 6-7 / D 7-10
    ],
)
def test_representative_lookups(severity: int, occurrence: int, detection: int, expected: str) -> None:
    assert action_priority(severity, occurrence, detection) == expected


@pytest.mark.parametrize("occurrence", list(ALL_SCORES))
@pytest.mark.parametrize("detection", list(ALL_SCORES))
def test_severity_one_is_always_low(occurrence: int, detection: int) -> None:
    """Severity 1 (no discernible effect) → Low for any O and D."""
    assert action_priority(1, occurrence, detection) == LOW


def test_every_combination_returns_a_valid_level() -> None:
    # Sweeps the whole 1–10 cube → exercises every severity/occurrence/detection
    # band branch, and proves the table is total.
    for s in ALL_SCORES:
        for o in ALL_SCORES:
            for d in ALL_SCORES:
                assert action_priority(s, o, d) in (HIGH, MEDIUM, LOW)


def test_monotonic_non_decreasing_in_each_dimension() -> None:
    # The published table never *lowers* AP when a single rating rises (Severity,
    # Occurrence, or Detection). This structural invariant catches transcription
    # errors a handful of spot-checks would miss.
    for s in ALL_SCORES:
        for o in ALL_SCORES:
            for d in ALL_SCORES:
                base = AP_ORDER[action_priority(s, o, d)]
                if s < 10:
                    assert AP_ORDER[action_priority(s + 1, o, d)] >= base
                if o < 10:
                    assert AP_ORDER[action_priority(s, o + 1, d)] >= base
                if d < 10:
                    assert AP_ORDER[action_priority(s, o, d + 1)] >= base


@pytest.mark.parametrize(
    ("severity", "occurrence", "detection", "bad"),
    [
        (0, 5, 5, "Severity"),
        (11, 5, 5, "Severity"),
        (5, 0, 5, "Occurrence"),
        (5, 11, 5, "Occurrence"),
        (5, 5, 0, "Detection"),
        (5, 5, 11, "Detection"),
    ],
)
def test_action_priority_rejects_out_of_range(
    severity: int, occurrence: int, detection: int, bad: str
) -> None:
    with pytest.raises(ValueError, match=f"{bad} score .* out of range"):
        action_priority(severity, occurrence, detection)


# --- rpn -----------------------------------------------------------------------


def test_rpn_is_product_of_sod() -> None:
    assert rpn(8, 4, 5) == 160
    assert rpn(1, 1, 1) == 1
    assert rpn(10, 10, 10) == 1000


@pytest.mark.parametrize(
    ("severity", "occurrence", "detection", "bad"),
    [
        (0, 5, 5, "Severity"),
        (5, 11, 5, "Occurrence"),
        (5, 5, 0, "Detection"),
    ],
)
def test_rpn_rejects_out_of_range(
    severity: int, occurrence: int, detection: int, bad: str
) -> None:
    with pytest.raises(ValueError, match=f"{bad} score .* out of range"):
        rpn(severity, occurrence, detection)
