"""Tests for the MSA → SPC gate policy (M3-5, #280).

Holds ``spc_app.msa_gate.gate_for`` to 100% line+branch: the three verdict strings
``msa_app.gage_rr_engine`` actually emits, the no-study case, and the loud rejection of
anything else.
"""
from __future__ import annotations

import pytest

from spc_app.msa_gate import NO_STUDY_REASON, gate_for


@pytest.mark.parametrize(
    "verdict,expected",
    [("Accept", "pass"), ("Marginal", "warn"), ("Reject", "block")],
)
def test_gate_for_maps_each_verdict(verdict: str, expected: str) -> None:
    """SME-locked policy (#280): Accept passes, Marginal warns, Reject blocks."""
    status, reason = gate_for(verdict)
    assert status == expected
    assert reason


def test_reject_blocks_not_warns() -> None:
    """The one decision this module encodes — pinned separately so a drift to
    'warn' fails a test that names the policy, not just a parametrised case."""
    assert gate_for("Reject")[0] == "block"


def test_no_study_warns_never_passes() -> None:
    """Silence about measurement-system adequacy must not read as an accept."""
    assert gate_for(None) == ("warn", NO_STUDY_REASON)


@pytest.mark.parametrize("verdict", ["Acceptable", "accept", "REJECT", "", "Unknown"])
def test_unrecognised_verdict_raises(verdict: str) -> None:
    """Exactly the committed-fixture typo class ('Acceptable') — never a silent default."""
    with pytest.raises(ValueError, match="Unrecognised Gage R&R verdict"):
        gate_for(verdict)
