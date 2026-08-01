"""Shared Quality Platform theme.

One source of truth for both apps:
- the dark amber/violet base palette + ``PLOTLY_LAYOUT`` (from the SPC dashboard)
- the RPN risk-tier semantic tokens (``TIER_HEX`` / ``TIER_RANK`` / ``TIER_RGB`` /
  ``TIER_FILL_HEX``, from FMEA)
- ``apply_theme()`` — the Streamlit CSS injector.

Pure-data tokens are re-exported eagerly from ``palette`` (no streamlit). ``apply_theme``
is loaded lazily because ``streamlit`` is an **optional extra** of this package
(``quality-core[streamlit]``): importing a token must never require it, on any install —
which also keeps the FMEA CLI export path framework-free.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from quality_core.theme.palette import (
    AMBER,
    AMBER_DARK,
    BG_CARD,
    BG_PRIMARY,
    BG_SECONDARY,
    BORDER,
    DANGER,
    FAILURE_MODE_TRUNC,
    PLOTLY_LAYOUT,
    SUCCESS,
    TEXT_PRIMARY,
    TEXT_SECONDARY,
    TIER_FILL_HEX,
    TIER_HEX,
    TIER_RANK,
    TIER_RGB,
    VIOLET,
)

if TYPE_CHECKING:  # let type-checkers see the lazily-provided symbol
    from quality_core.theme.style import apply_theme as apply_theme

__all__ = [
    "AMBER",
    "AMBER_DARK",
    "VIOLET",
    "BG_PRIMARY",
    "BG_SECONDARY",
    "BG_CARD",
    "BORDER",
    "TEXT_PRIMARY",
    "TEXT_SECONDARY",
    "SUCCESS",
    "DANGER",
    "PLOTLY_LAYOUT",
    "TIER_HEX",
    "TIER_RANK",
    "TIER_RGB",
    "TIER_FILL_HEX",
    "FAILURE_MODE_TRUNC",
    "apply_theme",
]


def __getattr__(name: str) -> object:
    # Lazy re-export so `from quality_core.theme import apply_theme` works without
    # importing streamlit for the pure-data consumers. Load-bearing since #202 made
    # streamlit an optional extra: without it, a base install could not import
    # `quality_core.theme` at all (an eager `from .style import ...` would raise).
    if name == "apply_theme":
        from quality_core.theme.style import apply_theme

        return apply_theme
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
