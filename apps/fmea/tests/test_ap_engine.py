"""
tests/test_ap_engine.py
Representative unit tests for fmea_app/ap_engine.py (W03-1).

This suite proves the AP engine two ways: (1) representative lookups and the
table's structural invariants (W03-1), and (2) an exhaustive, cell-by-cell
match against an **independent** transcription of the published AIAG-VDA AP
table (W03-2). The reference grid in PART 2 is written by hand from the
standard's published layout and classified into bands by its own code, so a
match confirms the engine — it is not the engine checked against itself.

Test coverage:
    AP-01  Severity dominance: higher S never lowers AP at fixed O,D (and high S
           alone does NOT force High — a rare, well-detected S=10 is Low)
    AP-02  Severity 1 → Low for every O/D combination
    AP-03  Representative High / Medium / Low lookups
    AP-04  Band boundaries resolve to the correct cell
    AP-05  Monotonic non-decreasing in S, O, and D (the table's defining property)
    AP-06  calculate_ap appends a correct "AP" column without mutating input
    AP-07  Out-of-range scores raise ValueError
    AP-08  calculate_ap raises KeyError when a score column is missing
    AP-09  Engine matches the published table for all 1000 S/O/D combinations
    AP-10  Named published reference cases (severity- and detection-dominant)

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
    rank_by_ap,
)

ALL_SCORES = range(1, 11)


# ---------------------------------------------------------------------------
# AP-01 — Severity dominance (handbook example)
# ---------------------------------------------------------------------------

def test_ap01_severity_dominates_but_does_not_auto_escalate():
    """Severity is emphasized first, but high severity alone is not 'always High'.

    AIAG-VDA gives severity the most weight: at a fixed Occurrence and Detection,
    raising Severity never lowers the AP. But the handbook does NOT make every
    high-severity failure High — a Severity-10 failure that is rare (O=2) and
    adequately detected (D=2) is Low (RPN would be 40), because there is little
    occurrence/detection left to act on.
    """
    # Severity dominance at fixed (O, D): S=10 ≥ S=5.
    assert AP_ORDER[action_priority(10, 4, 7)] >= AP_ORDER[action_priority(5, 4, 7)]
    assert action_priority(10, 4, 7) == HIGH and action_priority(5, 4, 7) == MEDIUM
    # But high severity does not auto-escalate when rare + detectable.
    assert action_priority(10, 2, 2) == LOW


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
        (9, 5, 1, MEDIUM),    # S 9-10 / O 4-5 / D 1 — handbook drops this to M
        (9, 1, 1, LOW),       # S 9-10 / O 1 / D 1 — rare + reliably detected
        (10, 1, 10, LOW),     # S 9-10 / O 1 / D 7-10 — rare: Low even if undetectable
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
    # Detection band edges 7 and 10 agree for an S 9-10 / O 1 cell (→ Low; the
    # whole S9-10/O1 row is Low in the handbook regardless of detection).
    assert action_priority(9, 1, 7) == action_priority(9, 1, 10) == LOW


# ---------------------------------------------------------------------------
# AP-05 — Monotonicity (defining property of the published AP table)
# ---------------------------------------------------------------------------

def test_ap05_monotonic_non_decreasing_in_each_factor():
    """Raising any one of S, O, D (others fixed) never lowers the AP.

    Monotonicity is a *necessary* structural property of the genuine AIAG-VDA
    table, but it is NOT sufficient to prove correctness: a row shifted by one
    occurrence band can still be monotonic (an earlier transcription error in the
    S9-10 block was exactly that, and this check did not catch it). Cell values
    are pinned by the handbook transcription in AP-09/AP-11 instead.
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
            "Occurrence": [10, 10, 4],
            "Detection": [10, 10, 5],
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


# ===========================================================================
# PART 2 — Exhaustive match against the published AIAG-VDA AP table (W03-2)
# ===========================================================================
#
# Independent transcription of the AIAG & VDA FMEA Handbook (1st Edition, 2019),
# "Action Priority (AP) for DFMEA and PFMEA" table (verified against both copies
# in the handbook — DFMEA p.70-71 and PFMEA p.116-117). Each severity band holds
# a 5×4 grid:
#   rows    = Occurrence band, listed high→low:  8-10, 6-7, 4-5, 2-3, 1
#   columns = Detection band,  listed worst→best: D 7-10, D 5-6, D 2-4, D 1
# Letters: H = High, M = Medium, L = Low.
#
# This is deliberately NOT imported from ap_engine — it is a second, hand-typed
# copy of the handbook table, and the band classifier below (_published_ap)
# re-derives bands with its own threshold logic rather than reusing the engine's
# lookup. So AP-09 catches an engine/grid error even if both stay monotonic
# (which is how the original S9-10 row-shift slipped past monotonicity alone).

_PUBLISHED_AP_TABLE: dict[str, list[list[str]]] = {
    #          D7-10  D5-6  D2-4  D1
    "9-10": [
        ["H", "H", "H", "H"],   # O 8-10
        ["H", "H", "H", "H"],   # O 6-7
        ["H", "H", "H", "M"],   # O 4-5
        ["H", "M", "L", "L"],   # O 2-3
        ["L", "L", "L", "L"],   # O 1
    ],
    "7-8": [
        ["H", "H", "H", "H"],   # O 8-10
        ["H", "H", "H", "M"],   # O 6-7
        ["H", "M", "M", "M"],   # O 4-5
        ["M", "M", "L", "L"],   # O 2-3
        ["L", "L", "L", "L"],   # O 1
    ],
    "4-6": [
        ["H", "H", "M", "M"],   # O 8-10
        ["M", "M", "M", "L"],   # O 6-7
        ["M", "L", "L", "L"],   # O 4-5
        ["L", "L", "L", "L"],   # O 2-3
        ["L", "L", "L", "L"],   # O 1
    ],
    "2-3": [
        ["M", "M", "L", "L"],   # O 8-10
        ["L", "L", "L", "L"],   # O 6-7
        ["L", "L", "L", "L"],   # O 4-5
        ["L", "L", "L", "L"],   # O 2-3
        ["L", "L", "L", "L"],   # O 1
    ],
    "1": [
        ["L", "L", "L", "L"],   # O 8-10
        ["L", "L", "L", "L"],   # O 6-7
        ["L", "L", "L", "L"],   # O 4-5
        ["L", "L", "L", "L"],   # O 2-3
        ["L", "L", "L", "L"],   # O 1
    ],
}

_LETTER_TO_AP = {"H": HIGH, "M": MEDIUM, "L": LOW}


def _published_ap(severity: int, occurrence: int, detection: int) -> str:
    """Oracle: expected AP from the hand-transcribed table, classified independently."""
    # Severity band (highest matching threshold wins).
    if severity >= 9:
        sev = "9-10"
    elif severity >= 7:
        sev = "7-8"
    elif severity >= 4:
        sev = "4-6"
    elif severity >= 2:
        sev = "2-3"
    else:
        sev = "1"
    # Occurrence row index (high→low order).
    occ_row = 0 if occurrence >= 8 else 1 if occurrence >= 6 else 2 if occurrence >= 4 else 3 if occurrence >= 2 else 4  # noqa: E501
    # Detection column index (worst→best order).
    det_col = 0 if detection >= 7 else 1 if detection >= 5 else 2 if detection >= 2 else 3
    return _LETTER_TO_AP[_PUBLISHED_AP_TABLE[sev][occ_row][det_col]]


# ---------------------------------------------------------------------------
# AP-09 — Exhaustive match for all 1000 S/O/D combinations
# ---------------------------------------------------------------------------

def test_ap09_action_priority_matches_published_table_for_every_combination():
    """Every S/O/D in 1..10 resolves to the published table's AP value."""
    mismatches = [
        (s, o, d, action_priority(s, o, d), _published_ap(s, o, d))
        for s, o, d in product(ALL_SCORES, ALL_SCORES, ALL_SCORES)
        if action_priority(s, o, d) != _published_ap(s, o, d)
    ]
    assert not mismatches, f"{len(mismatches)} cells disagree with the published table: {mismatches[:5]}"


# ---------------------------------------------------------------------------
# AP-10 — Named published reference cases (boundary / dominance behavior)
# ---------------------------------------------------------------------------

@pytest.mark.parametrize(
    ("severity", "occurrence", "detection", "expected", "why"),
    [
        # Severity is dominant but does NOT auto-escalate: a max-severity failure
        # that is rare (O 1) is Low for every detection, and S9-10/O2-3 is Low once
        # detection is adequate — only poor detection lifts it.
        (10, 1, 1, LOW, "S 9-10 / O 1 / D 1 — rare and reliably detected → Low"),
        (10, 1, 10, LOW, "S 9-10 / O 1 / D 7-10 — rare ⇒ Low even at max severity, no detection"),
        (10, 2, 2, LOW, "S 9-10 / O 2-3 / D 2-4 — rare + adequately detected ⇒ Low"),
        (10, 2, 10, HIGH, "S 9-10 / O 2-3 / D 7-10 — poor detection lifts the same cell to High"),
        (9, 6, 1, HIGH, "S 9-10 / O 6-7 / D 1 — High once occurrence is moderate"),
        # Detection-dominant within a fixed S/O cell: AP climbs as detection worsens.
        (7, 5, 1, MEDIUM, "S 7-8 / O 4-5 / D 1"),
        (7, 5, 7, HIGH, "S 7-8 / O 4-5 / D 7-10 — poor detection lifts to High"),
        # Occurrence-dominant within a fixed S/D cell.
        (5, 3, 10, LOW, "S 4-6 / O 2-3 / D 7-10"),
        (5, 8, 10, HIGH, "S 4-6 / O 8-10 / D 7-10 — frequent + undetected → High"),
        # Low-severity floor.
        (2, 10, 10, MEDIUM, "S 2-3 / O 8-10 / D 7-10 — worst low-severity case caps at Medium"),
    ],
)
def test_ap10_action_priority_published_reference_cases(
    severity, occurrence, detection, expected, why
):
    assert action_priority(severity, occurrence, detection) == expected, why


# ---------------------------------------------------------------------------
# AP-11 — rank_by_ap ordering
# ---------------------------------------------------------------------------

def test_ap11_rank_by_ap_orders_high_to_low_then_rpn():
    """High → Medium → Low, with RPN breaking ties inside a level (desc)."""
    df = pd.DataFrame(
        {
            "ID": [1, 2, 3, 4],
            "Severity": [2, 9, 5, 9],
            "Occurrence": [2, 8, 2, 2],
            "Detection": [2, 8, 2, 2],
            "RPN": [8, 576, 20, 36],
            "AP": [LOW, HIGH, LOW, HIGH],
        }
    )
    ranked = rank_by_ap(df)

    assert list(ranked["AP"]) == [HIGH, HIGH, LOW, LOW]
    # Within the High band, the higher-RPN row (ID 2, RPN 576) leads ID 4 (RPN 36).
    assert list(ranked[ranked["AP"] == HIGH]["ID"]) == [2, 4]
    assert list(ranked.index) == [0, 1, 2, 3]   # index reset
    assert "_ap_rank" not in ranked.columns      # temp key not leaked
    assert "_ap_rank" not in df.columns          # input not mutated


def test_ap11b_rank_by_ap_missing_column_raises_keyerror():
    with pytest.raises(KeyError, match="AP"):
        rank_by_ap(pd.DataFrame({"RPN": [1]}))


# ---------------------------------------------------------------------------
# AP-12 — Cross-check against an external peer-reviewed source
# ---------------------------------------------------------------------------

@pytest.mark.parametrize(
    ("severity", "occurrence", "detection", "expected"),
    [
        # Worked (S, O, D) -> AP rows from the PFMEA case study in
        # Pop et al., "An Intelligent Framework for Implementing AIAG-VDA FMEA and
        # Action Priority (AP) Assessment", MDPI Applied Sciences 16(5):2591 (2026),
        # Tables 2 and 3. An external corroboration independent of the handbook.
        (6, 6, 4, MEDIUM),
        (6, 4, 4, LOW),
        (6, 6, 2, MEDIUM),
        (6, 4, 2, LOW),
        (6, 4, 6, LOW),
        (7, 6, 6, HIGH),
        (7, 3, 6, MEDIUM),
        (7, 3, 4, LOW),
    ],
)
def test_ap12_matches_published_case_study(severity, occurrence, detection, expected):
    assert action_priority(severity, occurrence, detection) == expected
