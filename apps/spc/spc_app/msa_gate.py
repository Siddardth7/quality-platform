"""
msa_gate.py
MSA → SPC gate (M3-5, issue #280) — how far a Gage R&R verdict lets SPC be trusted.

One decision, one function: :func:`gate_for` maps the Gage R&R verdict string onto a
gate status. **No measurement-system math lives here.** The %GRR / ndc thresholds that
produce the verdict are ``msa_app.gage_rr_engine._compute_verdict``'s and are cited in
``apps/msa/docs/ASSUMPTIONS_LOG.md`` RULE 7 (ndc, AIAG MSA 4th Ed. Ch. II Sec. D) and
RULE 8 (%GRR, Ch. III Sec. B) — this module re-derives none of them and introduces no
new AIAG number. It consumes the three already-decided strings verbatim.

Policy (SME decision, #280):

===========  =============  ==========================================================
verdict      gate_status    why
===========  =============  ==========================================================
``Accept``   ``pass``       the measurement system is adequate; trust the SPC result.
``Marginal`` ``warn``       usable under reservation — proceed, annotated.
``Reject``   ``block``      trust is withheld: the SPC numbers rest on a measurement
                            system AIAG says must be improved before use.
``None``     ``warn``       no study on file — unknown, not "known good": silence about
                            measurement-system adequacy must never read as an accept.
===========  =============  ==========================================================

**Block never touches SPC chart math.** It is recorded in ``spc/msa-gate.json`` and read
by the MCP tool / a future UI, which decide not to *present* the result as trustworthy.
Nothing here deletes, refuses to write, or alters an SPC result.

Unrecognised verdict strings raise. ``MSAGageRRArtifact.verdict`` is a free-form
``Label``, not a ``Literal``, so a typo (the committed fixture said ``"Acceptable"``
until #280) loads cleanly and would silently match no band. Failing loud beats gating a
process on a string nobody read.
"""
from __future__ import annotations

from typing import Literal

__all__ = ["GateStatus", "NO_STUDY_REASON", "VERDICT_GATES", "gate_for"]

GateStatus = Literal["pass", "warn", "block"]

#: verdict -> (gate_status, reason). Exhaustive over the three strings
#: ``msa_app.gage_rr_engine._compute_verdict`` returns, exact case.
VERDICT_GATES: dict[str, tuple[GateStatus, str]] = {
    "Accept": (
        "pass",
        "Gage R&R accepted the measurement system — SPC results for this "
        "characteristic can be trusted.",
    ),
    "Marginal": (
        "warn",
        "Gage R&R found the measurement system marginal — SPC results are usable "
        "but should be read with reservation; improving the gage is recommended.",
    ),
    "Reject": (
        "block",
        "Gage R&R rejected the measurement system — trust is withheld: improve the "
        "measurement system before acting on SPC results for this characteristic.",
    ),
}

#: Used when no Gage R&R study on file covers the characteristic.
NO_STUDY_REASON = (
    "No Gage R&R study on file for this characteristic — measurement system "
    "adequacy is unverified."
)


def gate_for(verdict: str | None) -> tuple[GateStatus, str]:
    """Map a Gage R&R ``verdict`` onto ``(gate_status, reason)``.

    ``None`` means no study on file for this characteristic and gates as ``warn``.
    Raises ``ValueError`` for any other unrecognised string — never defaults.
    """
    if verdict is None:
        return ("warn", NO_STUDY_REASON)
    gate = VERDICT_GATES.get(verdict)
    if gate is None:
        raise ValueError(
            f"Unrecognised Gage R&R verdict {verdict!r}. Expected one of "
            f"{', '.join(repr(key) for key in VERDICT_GATES)} (exact case)."
        )
    return gate
