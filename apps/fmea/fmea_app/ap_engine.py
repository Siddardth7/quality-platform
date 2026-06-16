"""
ap_engine.py
FMEA Risk Prioritization Tool — AIAG-VDA Action Priority (AP) Logic Layer

The AIAG/VDA FMEA Handbook (2019) replaced the Risk Priority Number (RPN) with
**Action Priority (AP)**: a published lookup table that maps each
Severity × Occurrence × Detection combination directly to a High / Medium / Low
priority for action. AP fixes RPN's central flaw — that two failure modes with
the same RPN can carry very different risk — by making Severity the dominant
factor (emphasis order S → O → D), not just one of three equally-weighted terms.

This module is the AP counterpart to ``rpn_engine.py``. It is pure pandas/Python
with no Streamlit dependency, mirroring the RPN engine's shape:

Functions:
    action_priority(s, o, d)  — scalar lookup: returns "High" / "Medium" / "Low"
    calculate_ap(df)          — adds an "AP" column (vectorized over rows)

Engineering reference: AIAG/VDA FMEA Handbook (1st Edition, 2019), Action Priority
(AP) table for DFMEA and PFMEA. The table below is transcribed band-for-band from
that standard; see docs/FMEA_methodology_notes.md §4 and docs/ASSUMPTIONS_LOG.md
for the full citation and the structural checks that guard against transcription
error (the published table is monotonic non-decreasing in S, O, and D).

Author: Siddardth | M.S. Aerospace Engineering, UIUC
"""

from __future__ import annotations

import pandas as pd

# ---------------------------------------------------------------------------
# AP levels
# ---------------------------------------------------------------------------

HIGH = "High"
MEDIUM = "Medium"
LOW = "Low"

#: Ordinal rank for sorting/comparison (higher == more urgent). Used by
#: rank_by_ap and the app/exports layer to order by AP; colocated here so the
#: engine owns the canonical ordering.
AP_ORDER: dict[str, int] = {LOW: 0, MEDIUM: 1, HIGH: 2}

#: Prioritization basis the user can toggle between (RPN ↔ AP). The engine owns
#: these labels so the app, UI, and exports share one vocabulary.
BASIS_RPN = "RPN"
BASIS_AP = "AP"

SCORE_MIN = 1
SCORE_MAX = 10

# ---------------------------------------------------------------------------
# Published AIAG-VDA 2019 Action Priority bands
# ---------------------------------------------------------------------------
# The standard groups the 1–10 scales into fixed bands. Order is load-bearing:
# Detection bands below are listed high→low (D 7-10, 5-6, 2-4, 1) to match the
# column order of each grid row in _AP_GRID. Do NOT reorder without reordering
# the grid tuples in lockstep.

# (low, high) inclusive bounds, each labelled by the standard's band string.
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
# columns in _DETECTION_BANDS order: (D 7-10, D 5-6, D 2-4, D 1).
#
# Read the grid as "Severity dominates": S 9-10 is almost entirely High and only
# relaxes at the lowest Occurrence/Detection; S 1 is Low everywhere. The table is
# monotonic non-decreasing in S, O, and D — enforced by a test in W03-2.

_AP_GRID: dict[tuple[str, str], tuple[str, str, str, str]] = {
    # --- Severity 9-10 (very high / safety-or-regulatory) ---
    ("9-10", "8-10"): (HIGH, HIGH, HIGH, HIGH),
    ("9-10", "6-7"): (HIGH, HIGH, HIGH, HIGH),
    ("9-10", "4-5"): (HIGH, HIGH, HIGH, HIGH),
    ("9-10", "2-3"): (HIGH, HIGH, HIGH, MEDIUM),
    ("9-10", "1"): (HIGH, MEDIUM, LOW, LOW),
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

    Raises ValueError if ``value`` falls outside the AIAG 1–10 scale (i.e. no
    band matches), preserving the same fail-loud contract as the RPN engine's
    range validation.
    """
    for low, high, label in bands:
        if low <= value <= high:
            return label
    raise ValueError(
        f"{name} score {value!r} is out of range. "
        f"Valid range is {SCORE_MIN}–{SCORE_MAX} (AIAG-VDA scale). "
        f"Run validate_input(df) before scoring."
    )


def _detection_index(value: int) -> int:
    """Return the column index into a grid row for a Detection ``value``."""
    for idx, (low, high, _label) in enumerate(_DETECTION_BANDS):
        if low <= value <= high:
            return idx
    raise ValueError(
        f"Detection score {value!r} is out of range. "
        f"Valid range is {SCORE_MIN}–{SCORE_MAX} (AIAG-VDA scale). "
        f"Run validate_input(df) before scoring."
    )


# ---------------------------------------------------------------------------
# action_priority — scalar pure function
# ---------------------------------------------------------------------------

def action_priority(severity: int, occurrence: int, detection: int) -> str:
    """Return the AIAG-VDA Action Priority for one S/O/D combination.

    Pure function: same inputs always yield the same output, with no side
    effects. Looks up the published AIAG/VDA 2019 AP table (Severity dominant,
    then Occurrence, then Detection).

    Parameters
    ----------
    severity, occurrence, detection : int
        AIAG 1–10 ratings. Each must be in [1, 10].

    Returns
    -------
    str
        One of ``"High"``, ``"Medium"``, ``"Low"``.

    Raises
    ------
    ValueError
        If any rating is outside the 1–10 scale.

    Examples
    --------
    >>> from fmea_app.ap_engine import action_priority
    >>> action_priority(10, 2, 2)   # safety-critical even when rare + detectable
    'High'
    >>> action_priority(1, 10, 10)  # no discernible effect → never urgent
    'Low'
    """
    s_band = _band_label(severity, _SEVERITY_BANDS, "Severity")
    o_band = _band_label(occurrence, _OCCURRENCE_BANDS, "Occurrence")
    d_index = _detection_index(detection)
    return _AP_GRID[(s_band, o_band)][d_index]


# ---------------------------------------------------------------------------
# calculate_ap — DataFrame layer
# ---------------------------------------------------------------------------

def calculate_ap(df: pd.DataFrame) -> pd.DataFrame:
    """Add an ``AP`` column (High/Medium/Low) to the FMEA DataFrame.

    AP is the AIAG/VDA 2019 replacement for RPN-based prioritization. Run
    ``validate_input(df)`` (from ``rpn_engine``) first; this function assumes
    Severity/Occurrence/Detection are present and in range, and raises a clear
    ValueError via the band lookup if any value is out of range.

    Parameters
    ----------
    df : pd.DataFrame
        Validated FMEA DataFrame with ``Severity``, ``Occurrence``,
        ``Detection`` columns.

    Returns
    -------
    pd.DataFrame
        Copy of the input with an ``AP`` column appended. The original
        DataFrame is not modified.

    Raises
    ------
    KeyError
        If a score column is missing.
    ValueError
        If any S/O/D value is outside the 1–10 scale.

    Examples
    --------
    >>> import pandas as pd
    >>> from fmea_app.rpn_engine import validate_input
    >>> from fmea_app.ap_engine import calculate_ap
    >>> df = pd.read_csv('data/composite_panel_fmea_demo.csv')
    >>> validate_input(df)
    >>> calculate_ap(df)[['Severity', 'Occurrence', 'Detection', 'AP']].head(3)
    """
    missing = [c for c in ("Severity", "Occurrence", "Detection") if c not in df.columns]
    if missing:
        raise KeyError(
            f"Missing column(s) for calculate_ap: {missing}. "
            "Expected 'Severity', 'Occurrence', 'Detection'."
        )

    df = df.copy()
    df["AP"] = [
        action_priority(int(s), int(o), int(d))
        for s, o, d in zip(
            df["Severity"], df["Occurrence"], df["Detection"], strict=True
        )
    ]
    return df


# ---------------------------------------------------------------------------
# rank_by_ap — AP-basis ordering (counterpart to rpn_engine.rank_by_rpn)
# ---------------------------------------------------------------------------

def rank_by_ap(df: pd.DataFrame) -> pd.DataFrame:
    """Sort failure modes by Action Priority (High → Medium → Low), descending.

    The AP counterpart to ``rpn_engine.rank_by_rpn``. AP is a 3-level ordinal,
    so ties within a level are broken by the same secondary keys the RPN ranker
    uses — RPN, then Severity, then ID — to keep ordering stable and intuitive
    (the most severe, highest-RPN item leads its AP band).

    Parameters
    ----------
    df : pd.DataFrame
        DataFrame with an ``AP`` column (output of ``calculate_ap``).

    Returns
    -------
    pd.DataFrame
        Copy sorted by AP descending with the index reset. The temporary rank
        key is not retained.

    Raises
    ------
    KeyError
        If the ``AP`` column is missing — run ``calculate_ap`` first.
    """
    if "AP" not in df.columns:
        raise KeyError(
            "'AP' column not found. Run calculate_ap(df) before rank_by_ap(df)."
        )

    df = df.copy()
    df["_ap_rank"] = df["AP"].map(AP_ORDER)

    sort_cols = ["_ap_rank"]
    ascending = [False]
    for col, asc in (("RPN", False), ("Severity", False), ("ID", True)):
        if col in df.columns:
            sort_cols.append(col)
            ascending.append(asc)

    df = (
        df.sort_values(sort_cols, ascending=ascending)
        .drop(columns="_ap_rank")
        .reset_index(drop=True)
    )
    return df
