"""
tests/test_action.py
Tests for quality_core/schema/action.py — action tracking + effectiveness (W05-3).

Locks the `Action` field contracts (strict S/O/D, status enum, optional due-date
parse, blank owner rejection) and the `effectiveness` math: RPN/AP before → after,
the RPN delta and AP-reduced flag, partial re-rating (unset `*_after` falls back
to the original), and that the original scores are never mutated.
"""

from __future__ import annotations

from datetime import date

import pydantic
import pytest
from quality_core.schema import Action, ActionStatus, Effectiveness

# --- Action: construction + field contracts -----------------------------------


def test_defaults_are_open_and_unset() -> None:
    a = Action(owner="Quality Eng")
    assert a.status is ActionStatus.OPEN
    assert a.due is None
    assert a.s_after is None and a.o_after is None and a.d_after is None


def test_due_parses_from_iso_string_and_date() -> None:
    assert Action(owner="QE", due="2026-08-01").due == date(2026, 8, 1)
    assert Action(owner="QE", due=date(2026, 8, 1)).due == date(2026, 8, 1)


@pytest.mark.parametrize(
    ("value", "expected"),
    [("Open", ActionStatus.OPEN), ("In-Progress", ActionStatus.IN_PROGRESS), ("Closed", ActionStatus.CLOSED)],
)
def test_status_accepts_enum_string(value: str, expected: ActionStatus) -> None:
    assert Action(owner="QE", status=value).status is expected


def test_invalid_status_rejected() -> None:
    with pytest.raises(pydantic.ValidationError):
        Action(owner="QE", status="Done")


def test_blank_owner_rejected() -> None:
    with pytest.raises(pydantic.ValidationError, match="blank"):
        Action(owner="   ")


@pytest.mark.parametrize("field", ["s_after", "o_after", "d_after"])
@pytest.mark.parametrize("bad", [0, 11])
def test_after_rating_out_of_range_rejected(field: str, bad: int) -> None:
    with pytest.raises(pydantic.ValidationError):
        Action(owner="QE", **{field: bad})


@pytest.mark.parametrize("bad", [3.0, True])
def test_after_rating_rejects_non_strict_int(bad: object) -> None:
    # bool is an int subclass; strict mode must still reject it (matches FMEARow).
    with pytest.raises(pydantic.ValidationError):
        Action(owner="QE", s_after=bad)


# --- effectiveness: before → after --------------------------------------------


def test_full_rerating_reduces_rpn_and_ap() -> None:
    # S9/O8/D5 = High, RPN 360 → drop occurrence to 1 → Low, RPN 45.
    eff = Action(owner="QE", s_after=9, o_after=1, d_after=5).effectiveness(9, 8, 5)
    assert isinstance(eff, Effectiveness)
    assert (eff.initial_ap, eff.initial_rpn) == ("High", 360)
    assert (eff.revised_ap, eff.revised_rpn) == ("Low", 45)
    assert eff.rpn_delta == -315
    assert eff.ap_reduced is True


def test_partial_rerating_falls_back_to_original() -> None:
    # Only occurrence re-rated; severity and detection fall back to the originals.
    eff = Action(owner="QE", o_after=1).effectiveness(9, 8, 5)
    assert eff.revised_rpn == 9 * 1 * 5
    assert eff.initial_rpn == 9 * 8 * 5


def test_no_rerating_is_identity_and_does_not_mutate() -> None:
    action = Action(owner="QE")
    eff = action.effectiveness(9, 8, 5)
    assert eff.initial_rpn == eff.revised_rpn == 360
    assert eff.initial_ap == eff.revised_ap
    assert eff.rpn_delta == 0
    assert eff.ap_reduced is False
    # original assessment untouched: the Action carries no scores of its own.
    assert action.s_after is None and action.o_after is None and action.d_after is None


def test_rpn_can_worsen_when_rerating_is_higher() -> None:
    # A revised assessment that raises occurrence increases RPN (positive delta).
    eff = Action(owner="QE", o_after=10).effectiveness(5, 4, 5)
    assert eff.rpn_delta > 0
    assert eff.ap_reduced is False
