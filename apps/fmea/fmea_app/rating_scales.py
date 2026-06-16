"""
rating_scales.py
FMEA Risk Prioritization Tool — data-driven S/O/D rating scales (W03-4)

The 1–10 anchor descriptions for Severity, Occurrence, and Detection used to
live only in the docs. This module makes them **data**: the AIAG FMEA-4 default
scale ships as ``data/rating_scales.json`` and is loaded/validated here, and a
user may supply a custom 1–10 scale (e.g. a company-specific PFMEA rubric) that
goes through the same validation.

These scales are *reference* tables — they tell the analyst what a given score
means. They do not change the RPN/AP math (S/O/D are still integers 1–10); they
document the meaning behind each number. Thresholds and their AIAG citations in
``rpn_engine`` / ``ap_engine`` / ``docs/ASSUMPTIONS_LOG.md`` are unaffected.

Public API:
    RatingScaleSet                 — validated container for the three scales
    load_default_scales()          — load the bundled AIAG FMEA-4 default
    load_scales_from_mapping(obj)  — validate a parsed dict (custom scale)
    load_scales_from_json(text)    — parse + validate raw JSON text/bytes

Author: Siddardth | M.S. Aerospace Engineering, UIUC
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pandas as pd
import pydantic

#: The bundled AIAG FMEA-4 default scale, kept as data (not constants).
DEFAULT_SCALES_PATH = Path(__file__).resolve().parent.parent / "data" / "rating_scales.json"

#: The three factors a scale must define, in display order.
FACTORS = ("severity", "occurrence", "detection")

_REQUIRED_RATINGS = set(range(1, 11))


class RatingScaleSet(pydantic.BaseModel):
    """A complete set of S/O/D rating scales.

    Each factor maps every integer rating 1–10 to a non-empty description.
    Validation rejects scales that omit a rating, add out-of-range ratings, or
    leave a description blank — so a malformed custom upload fails loudly rather
    than silently shadowing part of the scale.
    """

    name: str = "Custom"
    source: str = ""
    severity: dict[int, str]
    occurrence: dict[int, str]
    detection: dict[int, str]

    @pydantic.field_validator("severity", "occurrence", "detection")
    @classmethod
    def _complete_1_to_10(cls, value: dict[int, str], info: pydantic.ValidationInfo) -> dict[int, str]:
        keys = set(value)
        if keys != _REQUIRED_RATINGS:
            missing = sorted(_REQUIRED_RATINGS - keys)
            extra = sorted(keys - _REQUIRED_RATINGS)
            raise ValueError(
                f"'{info.field_name}' scale must define ratings 1–10 exactly "
                f"(missing={missing or 'none'}, unexpected={extra or 'none'})."
            )
        blanks = sorted(r for r, desc in value.items() if not str(desc).strip())
        if blanks:
            raise ValueError(
                f"'{info.field_name}' scale has blank description(s) for rating(s) {blanks}."
            )
        return value

    def to_frame(self, factor: str) -> pd.DataFrame:
        """Return a rating 10→1 DataFrame for one factor, ready for display."""
        scale = getattr(self, factor)
        return pd.DataFrame(
            {"Score": list(range(10, 0, -1)), "Meaning": [scale[r] for r in range(10, 0, -1)]}
        )


def _build(obj: dict[str, Any], *, default_name: str) -> RatingScaleSet:
    payload = dict(obj)
    payload.setdefault("name", default_name)
    try:
        return RatingScaleSet(**payload)
    except pydantic.ValidationError as exc:
        first = exc.errors()[0]
        loc = " → ".join(str(x) for x in first.get("loc", [])) or "<scale>"
        raise ValueError(f"Invalid rating scale ({loc}): {first.get('msg', 'validation error')}") from exc


def load_default_scales() -> RatingScaleSet:
    """Load the bundled AIAG FMEA-4 default rating scales from data/."""
    with DEFAULT_SCALES_PATH.open(encoding="utf-8") as fh:
        return _build(json.load(fh), default_name="AIAG FMEA-4 (default)")


def load_scales_from_mapping(obj: dict[str, Any]) -> RatingScaleSet:
    """Validate an already-parsed mapping into a RatingScaleSet (custom scale)."""
    if not isinstance(obj, dict):
        raise ValueError("Custom rating scale must be a JSON object with severity/occurrence/detection keys.")
    return _build(obj, default_name="Custom")


def load_scales_from_json(text: str | bytes) -> RatingScaleSet:
    """Parse raw JSON (e.g. an uploaded file) and validate it as a custom scale."""
    try:
        parsed = json.loads(text)
    except (json.JSONDecodeError, UnicodeDecodeError) as exc:
        raise ValueError(f"Could not parse rating-scale JSON: {exc}") from exc
    return load_scales_from_mapping(parsed)
