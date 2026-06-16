"""
tests/test_ap_engine.py
Representative unit tests for fmea_app/ap_engine.py (W03-1).

Scope here is the AP *engine* — that the scalar lookup and the vectorized
column behave correctly on representative combinations and respect the table's
structural invariants. Exhaustive cell-by-cell validation against the full
published AIAG-VDA table is W03-2 (test_ap_published_table or similar).

Test coverage:
    AP-01  Severity dominance: S=10, O=2, D=2 → High (the handbook's own example)
    AP-02  Severity 1 → Low for every O/D combination
    AP-03  Representative High / Medium / Low lookups
    AP-04  Band boundaries resolve to the correct cell
    AP-05  Monotonic non-decreasing in S, O, and D (the table's defining property)
    AP-06  calculate_ap appends a correct "AP" column without mutating input
    AP-07  Out-of-range scores raise ValueError
    AP-08  calculate_ap raises KeyError when a score column is missing

Run with:
    pytest apps/fmea -k action_priority -q
"""

from itertools import product

import pandas as pd
import pytest

from fmea_app.ap_engine import (
    AP_ORDER,
    HIGH,
    LOW,
    MEDIUM,
    action_priority,
    calculate_ap,
)

ALL_SCORES = range(1, 11)


# ---------------------------------------------------------------------------
# AP-01 — Severity dominance (handbook example)
# ---------------------------------------------------------------------------

def test_ap01_severity_dominates_rare_detectable_safety_failure():
    """S=10 stays High even when rare (O=2) and detectable (D=2).

    This is the canonical AIAG-VDA example of why AP replaces RPN: RPN would
    score this 10*2*2=40 and bury it, but a safety failure must be High.
    """
    assert action_priority(10, 2, 2) == HIGH


# ---------------------------------------------------------------------------
# AP-02 — Severity 1 is always Low
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("occurrence", list(ALL_SCORES))
@pytest.mark.parametrize("detection", list(ALL_SCORES))
def test_ap02_action_priority_severity_one_always_low(occurrence, detection):
    """Severity 1 (no discernible effect) → Low for any O and D."""
    assert action_priority(1, occurrence, detection) == LOW


# ---------------------------------------------------------------------------
# AP-03 — Representative High / Medium / Low lookups
# ---------------------------------------------------------------------------

@pytest.mark.parametrize(
    ("severity", "occurrence", "detection", "expected"),
    [
        (10, 10, 10, HIGH),   # worst case
        (9, 5, 1, HIGH),      # S 9-10 / O 4-5 / D 1
        (9, 1, 1, LOW),       # S 9-10 / O 1 / D 1 — rare + reliably detected
        (8, 7, 1, MEDIUM),    # S 7-8 / O 6-7 / D 1
        (5, 10, 1, MEDIUM),   # S 4-6 / O 8-10 / D 1
        (5, 5, 6, LOW),       # S 4-6 / O 4-5 / D 5-6
        (3, 10, 10, MEDIUM),  # S 2-3 / O 8-10 / D 7-10
        (3, 6, 10, LOW),      # S 2-3 / O 6-7 / D 7-10
    ],
)
def test_ap03_representative_lookups(severity, occurrence, detection, expected):
    assert action_priority(severity, occurrence, detection) == expected


# ---------------------------------------------------------------------------
# AP-04 — Band boundaries resolve correctly
# ---------------------------------------------------------------------------

def test_ap04_band_boundaries_share_a_cell():
    """Every score inside a band maps to the same AP as its band-mates."""
    # Severity band 7-8 with O band 4-5 and D band 2-4 → Medium throughout.
    for s, o, d in product((7, 8), (4, 5), (2, 3, 4)):
        assert action_priority(s, o, d) == MEDIUM
    # Detection band edges 7 and 10 agree for an S 9-10 / O 1 cell (→ High).
    assert action_priority(9, 1, 7) == action_priority(9, 1, 10) == HIGH


# ---------------------------------------------------------------------------
# AP-05 — Monotonicity (defining property of the published AP table)
# ---------------------------------------------------------------------------

def test_ap05_monotonic_non_decreasing_in_each_factor():
    """Raising any one of S, O, D (others fixed) never lowers the AP.

    This is the structural invariant of the genuine AIAG-VDA table and the
    strongest guard against a transcription error in _AP_GRID.
    """
    for s, o, d in product(ALL_SCORES, ALL_SCORES, ALL_SCORES):
        base = AP_ORDER[action_priority(s, o, d)]
        if s < 10:
            assert AP_ORDER[action_priority(s + 1, o, d)] >= base
        if o < 10:
            assert AP_ORDER[action_priority(s, o + 1, d)] >= base
        if d < 10:
            assert AP_ORDER[action_priority(s, o, d + 1)] >= base


# ---------------------------------------------------------------------------
# AP-06 — calculate_ap column behavior
# ---------------------------------------------------------------------------

def test_ap06_calculate_ap_appends_column_without_mutating_input():
    df = pd.DataFrame(
        {
            "Severity": [10, 1, 7],
            "Occurrence": [2, 10, 4],
            "Detection": [2, 10, 5],
        }
    )
    result = calculate_ap(df)

    assert list(result["AP"]) == [HIGH, LOW, MEDIUM]
    assert "AP" not in df.columns          # original untouched
    assert result is not df                # returns a copy


# ---------------------------------------------------------------------------
# AP-07 — Out-of-range scores raise ValueError
# ---------------------------------------------------------------------------

@pytest.mark.parametrize(
    ("severity", "occurrence", "detection"),
    [(0, 5, 5), (11, 5, 5), (5, 0, 5), (5, 11, 5), (5, 5, 0), (5, 5, 11)],
)
def test_ap07_out_of_range_raises_valueerror(severity, occurrence, detection):
    with pytest.raises(ValueError, match="out of range"):
        action_priority(severity, occurrence, detection)


# ---------------------------------------------------------------------------
# AP-08 — calculate_ap requires the score columns
# ---------------------------------------------------------------------------

def test_ap08_calculate_ap_missing_column_raises_keyerror():
    df = pd.DataFrame({"Severity": [5], "Occurrence": [5]})  # no Detection
    with pytest.raises(KeyError, match="Detection"):
        calculate_ap(df)
