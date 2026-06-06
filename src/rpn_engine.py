"""
rpn_engine.py
FMEA Risk Prioritization Tool — Core Logic Layer

Functions:
    validate_input(df)   — schema + type + range check; raises ValueError on failure
    calculate_rpn(df)    — adds RPN = Severity × Occurrence × Detection column
    flag_critical(df)    — applies AIAG FMEA-4 flags (High RPN, High Severity, Action Priority)
    rank_by_rpn(df)      — sorts DataFrame descending by RPN; adds Risk_Tier column

Engineering reference: AIAG FMEA-4 (4th Edition) + AIAG/VDA FMEA Handbook (5th Edition, 2019)
See docs/ASSUMPTIONS_LOG.md for every threshold decision.

Author: Siddardth | M.S. Aerospace Engineering, UIUC
"""

import numpy as np
import pandas as pd
import pydantic as _pydantic

from src.schema import FMEADataset, FMEARow

# ---------------------------------------------------------------------------
# Constants — all thresholds sourced from ASSUMPTIONS_LOG.md
# ---------------------------------------------------------------------------

REQUIRED_COLUMNS = [
    "ID",
    "Process_Step",
    "Component",
    "Function",
    "Failure_Mode",
    "Effect",
    "Severity",
    "Cause",
    "Occurrence",
    "Current_Control",
    "Detection",
]

SCORE_COLUMNS = ["Severity", "Occurrence", "Detection"]

SCORE_MIN = 1
SCORE_MAX = 10

# RULE 1 — ASSUMPTIONS_LOG.md: RPN > 100 requires corrective action (AIAG FMEA-4)
RPN_HIGH_THRESHOLD = 100

# RULE 2 — ASSUMPTIONS_LOG.md: Severity ≥ 9 is safety-critical regardless of RPN
SEVERITY_HIGH_THRESHOLD = 9

# RULE 3 — ASSUMPTIONS_LOG.md: Action Priority H = RPN ≥ 200 OR Severity ≥ 9
RPN_ACTION_PRIORITY_H_THRESHOLD = 200

# RULE 4 — ASSUMPTIONS_LOG.md: Risk tiers for color coding
RPN_RED_THRESHOLD = 100     # RPN > 100 OR Severity ≥ 9 → Red
RPN_YELLOW_MIN = 50         # RPN 50–100 AND Severity < 9 → Yellow
                            # RPN < 50  AND Severity < 9 → Green


# ---------------------------------------------------------------------------
# validate_input
# ---------------------------------------------------------------------------

def validate_input(df: pd.DataFrame) -> None:
    """
    Validate an FMEA input DataFrame against the required schema.
    Delegates to Pydantic FMEARow/FMEADataset models as the source of truth.
    Raises ValueError (not pydantic.ValidationError) to preserve the public interface.

    Checks performed:
      1. DataFrame is not empty (≥ 1 row)
      2. All required columns are present
      3–6. Delegated to Pydantic: S/O/D strict integer type, range [1,10],
           ID non-null/integer/unique, required text fields non-null.

    Parameters
    ----------
    df : pd.DataFrame
        Raw FMEA data loaded from CSV or Excel.

    Raises
    ------
    ValueError
        Descriptive message identifying the first validation failure found.

    Returns
    -------
    None
        Returns silently if all checks pass.

    Examples
    --------
    >>> import pandas as pd
    >>> from src.rpn_engine import validate_input
    >>> df = pd.read_csv('data/composite_panel_fmea_demo.csv')
    >>> validate_input(df)   # no error → valid
    """
    # --- Check 1: at least one row ---
    if df.empty:
        raise ValueError(
            "Input DataFrame is empty. "
            "FMEA file must contain at least one data row."
        )

    # --- Check 2: required columns present ---
    missing_cols = [col for col in REQUIRED_COLUMNS if col not in df.columns]
    if missing_cols:
        raise ValueError(
            f"Missing required column(s): {missing_cols}. "
            f"Expected columns: {REQUIRED_COLUMNS}"
        )

    # --- Pydantic validation (Checks 3–6) ---
    # Range-violation field names (Severity, Occurrence, Detection)
    _RANGE_FIELDS = {"severity", "occurrence", "detection"}

    try:
        rows = [FMEARow(**row) for row in df[REQUIRED_COLUMNS].to_dict(orient="records")]
        FMEADataset(rows=rows)
    except _pydantic.ValidationError as exc:
        first = exc.errors()[0]
        field = " -> ".join(str(loc) for loc in first["loc"]) or "<dataset>"
        msg = first["msg"]
        # Detect range violations for S/O/D — Pydantic says "less than or equal to"
        # or "greater than or equal to"; we must preserve "out-of-range" in message
        # so existing tests that match on that string keep passing.
        field_lower = field.lower().split(" -> ")[-1]
        if field_lower in _RANGE_FIELDS and (
            "less than or equal" in msg or "greater than or equal" in msg
        ):
            raise ValueError(
                f"Column '{field}' contains out-of-range values. "
                f"Valid range is {SCORE_MIN}–{SCORE_MAX} (AIAG FMEA-4 scale). "
                f"Check your data against the template at data/fmea_input_template.csv."
            ) from exc
        raise ValueError(
            f"Validation error in column '{field}': {msg}. "
            f"Check your data against the template at data/fmea_input_template.csv."
        ) from exc


# ---------------------------------------------------------------------------
# calculate_rpn
# ---------------------------------------------------------------------------

def calculate_rpn(df: pd.DataFrame) -> pd.DataFrame:
    """
    Add an RPN column to the FMEA DataFrame.

    RPN = Severity × Occurrence × Detection
    Source: AIAG FMEA-4, Section 3 — Risk Priority Number

    Parameters
    ----------
    df : pd.DataFrame
        Validated FMEA DataFrame (pass through validate_input first).

    Returns
    -------
    pd.DataFrame
        Copy of input DataFrame with 'RPN' column appended.
        Original DataFrame is not modified (returns a copy).

    Examples
    --------
    >>> import pandas as pd
    >>> from src.rpn_engine import validate_input, calculate_rpn
    >>> df = pd.read_csv('data/composite_panel_fmea_demo.csv')
    >>> validate_input(df)
    >>> df_rpn = calculate_rpn(df)
    >>> df_rpn[['Severity', 'Occurrence', 'Detection', 'RPN']].head(3)
    """
    df = df.copy()
    df["RPN"] = df["Severity"] * df["Occurrence"] * df["Detection"]
    return df


# ---------------------------------------------------------------------------
# flag_critical
# ---------------------------------------------------------------------------

def flag_critical(df: pd.DataFrame) -> pd.DataFrame:
    """
    Apply AIAG FMEA-4 criticality flags to each failure mode.

    Three flag columns are added (all boolean):

    Flag_High_RPN
        True if RPN > 100. Signals that corrective action is required.
        Source: RULE 1 in docs/ASSUMPTIONS_LOG.md

    Flag_High_Severity
        True if Severity ≥ 9. Safety-critical flag — corrective action
        required regardless of Occurrence or Detection scores.
        Source: RULE 2 in docs/ASSUMPTIONS_LOG.md

    Flag_Action_Priority_H
        True if RPN ≥ 200 OR Severity ≥ 9. Simplified implementation of
        the AIAG 5th Edition Action Priority "High" tier.
        Source: RULE 3 in docs/ASSUMPTIONS_LOG.md

    Parameters
    ----------
    df : pd.DataFrame
        DataFrame with 'RPN' column (output of calculate_rpn).

    Returns
    -------
    pd.DataFrame
        Copy of input DataFrame with three flag columns appended.

    Raises
    ------
    KeyError
        If 'RPN' column is missing — run calculate_rpn first.
    """
    if "RPN" not in df.columns:
        raise KeyError(
            "'RPN' column not found. Run calculate_rpn(df) before flag_critical(df)."
        )

    df = df.copy()

    # RULE 1: RPN > 100 → Flag_High_RPN
    df["Flag_High_RPN"] = df["RPN"] > RPN_HIGH_THRESHOLD

    # RULE 2: Severity ≥ 9 → Flag_High_Severity (safety rule — independent of RPN)
    df["Flag_High_Severity"] = df["Severity"] >= SEVERITY_HIGH_THRESHOLD

    # RULE 3: Action Priority H = RPN ≥ 200 OR Severity ≥ 9
    df["Flag_Action_Priority_H"] = (
        (df["RPN"] >= RPN_ACTION_PRIORITY_H_THRESHOLD)
        | (df["Severity"] >= SEVERITY_HIGH_THRESHOLD)
    )

    return df


# ---------------------------------------------------------------------------
# rank_by_rpn
# ---------------------------------------------------------------------------

def rank_by_rpn(df: pd.DataFrame) -> pd.DataFrame:
    """
    Sort failure modes by RPN descending and assign a Risk Tier.

    Risk Tier assignment (RULE 4 in docs/ASSUMPTIONS_LOG.md):
        Red    — RPN > 100 OR Severity ≥ 9  (immediate action required)
        Yellow — RPN 50–100 AND Severity < 9 (corrective action recommended)
        Green  — RPN < 50  AND Severity < 9  (monitor; optional action)

    Parameters
    ----------
    df : pd.DataFrame
        DataFrame with 'RPN', 'Severity', 'Flag_High_RPN',
        and 'Flag_High_Severity' columns (output of flag_critical).

    Returns
    -------
    pd.DataFrame
        Copy of input DataFrame sorted by RPN descending with
        'Risk_Tier' column appended. Index is reset.

    Raises
    ------
    KeyError
        If required columns are missing — run calculate_rpn and
        flag_critical before rank_by_rpn.
    """
    required = ["RPN", "Severity", "Flag_High_RPN", "Flag_High_Severity"]
    missing = [c for c in required if c not in df.columns]
    if missing:
        raise KeyError(
            f"Missing column(s) for rank_by_rpn: {missing}. "
            "Run calculate_rpn then flag_critical first."
        )

    df = df.copy()

    # Assign Risk_Tier — RULE 4 (vectorized for performance)
    conditions = [
        (df["RPN"] > RPN_RED_THRESHOLD) | (df["Severity"] >= SEVERITY_HIGH_THRESHOLD),
        df["RPN"] >= RPN_YELLOW_MIN,
    ]
    df["Risk_Tier"] = np.select(conditions, ["Red", "Yellow"], default="Green")

    # Sort descending by RPN; stable secondary keys prevent arbitrary ordering of ties
    df = df.sort_values(
        ["RPN", "Severity", "Occurrence", "ID"],
        ascending=[False, False, False, True],
    ).reset_index(drop=True)

    return df


# ---------------------------------------------------------------------------
# Pipeline convenience function
# ---------------------------------------------------------------------------

def run_pipeline(df: pd.DataFrame) -> pd.DataFrame:
    """
    Run the full FMEA analysis pipeline in one call.

    Equivalent to:
        validate_input(df)
        df = calculate_rpn(df)
        df = flag_critical(df)
        df = rank_by_rpn(df)

    Parameters
    ----------
    df : pd.DataFrame
        Raw FMEA input DataFrame.

    Returns
    -------
    pd.DataFrame
        Fully analyzed, ranked, and flagged FMEA DataFrame.
    """
    validate_input(df)
    df = calculate_rpn(df)
    df = flag_critical(df)
    df = rank_by_rpn(df)
    return df
