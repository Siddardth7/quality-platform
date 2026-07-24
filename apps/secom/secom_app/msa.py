"""
secom_app/msa.py
Structural AIAG-MSA applicability guard for SECOM (W09-4, #68).

SECOM is observational process-monitoring data: one reading per wafer per
sensor, with no `part`/`appraiser`/`trial` axis and none can be legitimately
constructed (different sensors measure different characteristics, not repeat
appraisals of one measurand; successive wafers are different parts, not
re-measurements of the same part). A Gage R&R needs a *designed* crossed
study — see `apps/secom/docs/MSA_APPLICABILITY.md` for the full AIAG-anchored
argument (AIAG MSA 4th ed. §3.1/§3.2, cross-referenced against the SME-
verified `apps/msa/docs/ASSUMPTIONS_LOG.md` RULE 1/RULE 11/RULE 12).

This module does NOT reimplement Gage R&R math — it only refuses. A real
study is run through the existing MSA app (`apps/msa`, `compute_gage_rr`).

# ponytail: the W08 engine (`gage_rr_engine.compute_gage_rr`) already raises
# on a column-less frame, so this guard's only value-add is the SECOM-
# specific, standards-anchored message + doc pointer — not new validation.
If SME instead picks OQ-1 shape (B) (docs only), delete this module.
"""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

__all__ = ["GAGE_RR_DIMENSIONS", "MsaApplicability", "gage_rr_applicability", "assert_gage_rr_applicable"]

#: The three crossed-study axes AIAG MSA requires (AIAG MSA 4th ed. §3.1/§3.2);
#: also the columns `compute_gage_rr` demands (`apps/msa/msa_app/gage_rr_engine.py:83`).
GAGE_RR_DIMENSIONS: tuple[str, str, str] = ("part", "appraiser", "trial")

_STANDARD_BASIS = (
    "A Gage R&R requires a designed crossed study — n parts x k appraisers x "
    "r>=2 trials (AIAG MSA 4th ed. Section 3.1/3.2; see apps/msa/docs/ASSUMPTIONS_LOG.md "
    "RULE 1/RULE 11/RULE 12) — with repeatability estimated within a (part, appraiser) "
    "cell and reproducibility estimated across appraisers."
)
_MISSING_REASON_TEMPLATE = (
    _STANDARD_BASIS + " This frame is missing {missing}, so no Gage R&R can be "
    "legitimately run on it. See apps/secom/docs/MSA_APPLICABILITY.md."
)
_PRESENT_REASON = (
    _STANDARD_BASIS + " This frame carries all three dimensions, so a Gage R&R "
    "may be run via apps/msa's compute_gage_rr (not reimplemented here)."
)


@dataclass(frozen=True)
class MsaApplicability:
    """Structural applicability verdict for a would-be Gage R&R frame."""

    applicable: bool
    missing_dimensions: tuple[str, ...]
    reason: str


def gage_rr_applicability(features: pd.DataFrame) -> MsaApplicability:
    """Structural AIAG-MSA applicability check for a would-be Gage R&R frame.

    Pure. SECOM's `features` carry none of `GAGE_RR_DIMENSIONS`, so this returns
    `applicable=False, missing_dimensions=("part", "appraiser", "trial")`.
    Returns `applicable=True` only when all three columns are present — the
    actual computation is then the MSA app's job via `compute_gage_rr`, never
    reimplemented here. Does not mutate `features`."""
    missing = tuple(dim for dim in GAGE_RR_DIMENSIONS if dim not in features.columns)
    applicable = not missing
    reason = _PRESENT_REASON if applicable else _MISSING_REASON_TEMPLATE.format(missing=", ".join(missing))
    return MsaApplicability(applicable=applicable, missing_dimensions=missing, reason=reason)


def assert_gage_rr_applicable(features: pd.DataFrame) -> None:
    """Raise `ValueError` with the AIAG-anchored `reason` when a frame cannot
    support a Gage R&R (i.e. `gage_rr_applicability(features).applicable` is
    `False`). Returns `None` otherwise. This is the executable form of the
    'no fabricated MSA on SECOM' rule."""
    verdict = gage_rr_applicability(features)
    if not verdict.applicable:
        raise ValueError(verdict.reason)
