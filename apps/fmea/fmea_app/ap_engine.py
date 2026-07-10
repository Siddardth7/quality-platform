"""
ap_engine.py
FMEA Risk Prioritization Tool — AIAG-VDA Action Priority (AP) Logic Layer.

The scalar AP scoring — the published AIAG/VDA 2019 lookup table and
``action_priority`` — now lives in ``quality_core.scoring`` so the whole platform
shares one standards-correct scorer (promoted W05-3a). This module re-exports that
scalar API for backward compatibility and adds the pandas DataFrame layers
(``calculate_ap``, ``rank_by_ap``) that the FMEA app uses.

Engineering reference: AIAG/VDA FMEA Handbook (1st Edition, 2019), Action Priority
(AP) table for DFMEA and PFMEA; see docs/FMEA_methodology_notes.md §4 and
docs/ASSUMPTIONS_LOG.md for the citation and the structural checks.

Author: Siddardth | M.S. Aerospace Engineering, UIUC
"""

from __future__ import annotations

import pandas as pd

# Re-export the shared scalar scoring API (the AP table + action_priority now live
# in quality_core.scoring). Existing `from fmea_app.ap_engine import ...` callers
# keep working unchanged.
from quality_core.scoring import (
    AP_ORDER,
    BASIS_AP,
    BASIS_RPN,
    HIGH,
    LOW,
    MEDIUM,
    SCORE_MAX,
    SCORE_MIN,
    action_priority,
    rpn,
)

__all__ = [
    "AP_ORDER",
    "BASIS_AP",
    "BASIS_RPN",
    "HIGH",
    "LOW",
    "MEDIUM",
    "SCORE_MAX",
    "SCORE_MIN",
    "action_priority",
    "calculate_ap",
    "rank_by_ap",
    "rpn",
]


# ---------------------------------------------------------------------------
# calculate_ap — DataFrame layer
# ---------------------------------------------------------------------------

def calculate_ap(df: pd.DataFrame) -> pd.DataFrame:
    """Add an ``AP`` column (High/Medium/Low) to the FMEA DataFrame.

    AP is the AIAG/VDA 2019 replacement for RPN-based prioritization. Run
    ``validate_input(df)`` (from ``rpn_engine``) first; this assumes
    Severity/Occurrence/Detection are present, and raises a clear ValueError via
    the shared ``action_priority`` band lookup if any value is out of range. The
    original DataFrame is not modified.
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

    AP is a 3-level ordinal, so ties within a level are broken by the same
    secondary keys the RPN ranker uses — RPN, then Severity, then ID — to keep
    ordering stable. Raises KeyError if the ``AP`` column is missing.
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
