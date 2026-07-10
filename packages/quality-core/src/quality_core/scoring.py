"""
scoring.py
Shared, standards-correct scalar risk scoring for the Quality Platform.

Two pure functions the whole platform can share (SPC, FMEA, the future Control
Plan): ``rpn`` (the classic Severity × Occurrence × Detection product) and
``action_priority`` (the AIAG/VDA 2019 Action Priority lookup). Promoted out of
the FMEA app (W05-3a) so `quality_core` can score without importing an app — the
FMEA app's pandas layers (`calculate_ap`, `rank_by_ap`) now re-export and compose
these. Mirrors how `quality_core.io` and `quality_core.schema` consolidate shared
logic.

The AIAG/VDA FMEA Handbook (2019) replaced RPN with **Action Priority (AP)**: a
published lookup that maps each Severity × Occurrence × Detection combination to a
High / Medium / Low priority for action, with Severity dominant (emphasis order
S → O → D) but *not* auto-escalating. The table below is transcribed band-for-band
from that standard; `tests/test_scoring.py` checks it against an independent
transcription and published worked examples, and the table is monotonic
non-decreasing in S, O, and D by construction.
"""
from __future__ import annotations

# ---------------------------------------------------------------------------
# AP levels + shared vocabulary
# ---------------------------------------------------------------------------

HIGH = "High"
MEDIUM = "Medium"
LOW = "Low"

#: Ordinal rank for sorting/comparison (higher == more urgent).
AP_ORDER: dict[str, int] = {LOW: 0, MEDIUM: 1, HIGH: 2}

#: Prioritization basis the user can toggle between (RPN ↔ AP).
BASIS_RPN = "RPN"
BASIS_AP = "AP"

SCORE_MIN = 1
SCORE_MAX = 10

# ---------------------------------------------------------------------------
# Published AIAG-VDA 2019 Action Priority bands
# ---------------------------------------------------------------------------
# (low, high) inclusive bounds, each labelled by the standard's band string.
# Detection columns are listed high→low (worst detectability first) to match the
# column order of each grid row in _AP_GRID — do NOT reorder without reordering
# the grid tuples in lockstep.

_SEVERITY_BANDS: tuple[tuple[int, int, str], ...] = (
    (9, 10, "9-10"),
    (7, 8, "7-8"),
    (4, 6, "4-6"),
    (2, 3, "2-3"),
    (1, 1, "1"),
)

_OCCURRENCE_BANDS: tuple[tuple[int, int, str], ...] = (
    (8, 10, "8-10"),
    (6, 7, "6-7"),
    (4, 5, "4-5"),
    (2, 3, "2-3"),
    (1, 1, "1"),
)

# Detection columns, high→low (worst detectability first).
_DETECTION_BANDS: tuple[tuple[int, int, str], ...] = (
    (7, 10, "7-10"),
    (5, 6, "5-6"),
    (2, 4, "2-4"),
    (1, 1, "1"),
)

# ---------------------------------------------------------------------------
# The published Action Priority table (AIAG/VDA FMEA Handbook 2019)
# ---------------------------------------------------------------------------
# Keyed by (Severity band, Occurrence band). Each value is the row of Detection
# columns in _DETECTION_BANDS order: (D 7-10, D 5-6, D 2-4, D 1). Transcribed
# directly from the AIAG & VDA FMEA Handbook (1st Edition, 2019), "Action
# Priority (AP) for DFMEA and PFMEA". Severity is emphasized first but does NOT
# auto-escalate: a Severity 9-10 failure that is rare (O 1) is Low for every
# Detection; S 1 is Low everywhere.

_AP_GRID: dict[tuple[str, str], tuple[str, str, str, str]] = {
    # --- Severity 9-10 (very high / safety-or-regulatory) ---
    ("9-10", "8-10"): (HIGH, HIGH, HIGH, HIGH),
    ("9-10", "6-7"): (HIGH, HIGH, HIGH, HIGH),
    ("9-10", "4-5"): (HIGH, HIGH, HIGH, MEDIUM),
    ("9-10", "2-3"): (HIGH, MEDIUM, LOW, LOW),
    ("9-10", "1"): (LOW, LOW, LOW, LOW),
    # --- Severity 7-8 (high) ---
    ("7-8", "8-10"): (HIGH, HIGH, HIGH, HIGH),
    ("7-8", "6-7"): (HIGH, HIGH, HIGH, MEDIUM),
    ("7-8", "4-5"): (HIGH, MEDIUM, MEDIUM, MEDIUM),
    ("7-8", "2-3"): (MEDIUM, MEDIUM, LOW, LOW),
    ("7-8", "1"): (LOW, LOW, LOW, LOW),
    # --- Severity 4-6 (moderate) ---
    ("4-6", "8-10"): (HIGH, HIGH, MEDIUM, MEDIUM),
    ("4-6", "6-7"): (MEDIUM, MEDIUM, MEDIUM, LOW),
    ("4-6", "4-5"): (MEDIUM, LOW, LOW, LOW),
    ("4-6", "2-3"): (LOW, LOW, LOW, LOW),
    ("4-6", "1"): (LOW, LOW, LOW, LOW),
    # --- Severity 2-3 (low) ---
    ("2-3", "8-10"): (MEDIUM, MEDIUM, LOW, LOW),
    ("2-3", "6-7"): (LOW, LOW, LOW, LOW),
    ("2-3", "4-5"): (LOW, LOW, LOW, LOW),
    ("2-3", "2-3"): (LOW, LOW, LOW, LOW),
    ("2-3", "1"): (LOW, LOW, LOW, LOW),
    # --- Severity 1 (no discernible effect): Low regardless of O and D ---
    ("1", "8-10"): (LOW, LOW, LOW, LOW),
    ("1", "6-7"): (LOW, LOW, LOW, LOW),
    ("1", "4-5"): (LOW, LOW, LOW, LOW),
    ("1", "2-3"): (LOW, LOW, LOW, LOW),
    ("1", "1"): (LOW, LOW, LOW, LOW),
}


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _band_label(
    value: int, bands: tuple[tuple[int, int, str], ...], name: str
) -> str:
    """Return the band label whose inclusive [low, high] range contains ``value``.

    Raises ValueError if ``value`` falls outside the AIAG 1–10 scale.
    """
    for low, high, label in bands:
        if low <= value <= high:
            return label
    raise ValueError(
        f"{name} score {value!r} is out of range. "
        f"Valid range is {SCORE_MIN}–{SCORE_MAX} (AIAG-VDA scale)."
    )


def _detection_index(value: int) -> int:
    """Return the column index into a grid row for a Detection ``value``."""
    for idx, (low, high, _label) in enumerate(_DETECTION_BANDS):
        if low <= value <= high:
            return idx
    raise ValueError(
        f"Detection score {value!r} is out of range. "
        f"Valid range is {SCORE_MIN}–{SCORE_MAX} (AIAG-VDA scale)."
    )


# ---------------------------------------------------------------------------
# Public scalar scorers
# ---------------------------------------------------------------------------

def rpn(severity: int, occurrence: int, detection: int) -> int:
    """Return the Risk Priority Number = Severity × Occurrence × Detection.

    Pure function. Each rating must be in the AIAG 1–10 scale; raises ValueError
    otherwise so callers can't silently score out-of-range inputs.
    """
    for name, value in (("Severity", severity), ("Occurrence", occurrence), ("Detection", detection)):
        if not SCORE_MIN <= value <= SCORE_MAX:
            raise ValueError(
                f"{name} score {value!r} is out of range. "
                f"Valid range is {SCORE_MIN}–{SCORE_MAX} (AIAG-VDA scale)."
            )
    return severity * occurrence * detection


def action_priority(severity: int, occurrence: int, detection: int) -> str:
    """Return the AIAG-VDA Action Priority for one S/O/D combination.

    Pure function: same inputs always yield the same output. Looks up the
    published AIAG/VDA 2019 AP table (Severity dominant, then Occurrence, then
    Detection). Returns ``"High"``, ``"Medium"``, or ``"Low"``. Raises ValueError
    if any rating is outside the 1–10 scale.

    Examples
    --------
    >>> action_priority(10, 2, 2)   # safety-critical but rare + detectable
    'Low'
    >>> action_priority(10, 10, 10)  # worst case
    'High'
    """
    s_band = _band_label(severity, _SEVERITY_BANDS, "Severity")
    o_band = _band_label(occurrence, _OCCURRENCE_BANDS, "Occurrence")
    d_index = _detection_index(detection)
    return _AP_GRID[(s_band, o_band)][d_index]
