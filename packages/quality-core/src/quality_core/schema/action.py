"""
action.py
FMEA action tracking + action effectiveness (W05-3).

The AIAG/VDA "optimization" loop: after a failure mode is assessed, you record an
`Action` (owner, due date, status) and — once the action is taken — re-rate
Severity / Occurrence / Detection. `Action.effectiveness(...)` compares the
original assessment against the revised one, reporting RPN and Action Priority
before → after plus the RPN delta. It never mutates the original scores: the
"before" S/O/D are passed in, the "after" live on the Action, and the result is a
fresh read-only value.

Scoring reuses the shared `quality_core.scoring` scorers (one standards-correct
AP table for the whole platform); the model reuses `StrictModel` so S/O/D stay
strict ints and text is stripped/blank-rejected like every other schema.
"""
from __future__ import annotations

import enum
from dataclasses import dataclass
from datetime import date
from typing import Annotated

import pydantic

from quality_core.schema._base import StrictModel
from quality_core.scoring import AP_ORDER, action_priority, rpn

Rating = Annotated[int, pydantic.Field(ge=1, le=10)]


class ActionStatus(enum.StrEnum):
    OPEN = "Open"
    IN_PROGRESS = "In-Progress"
    CLOSED = "Closed"


@dataclass(frozen=True)
class Effectiveness:
    """Read-only result of comparing an assessment before vs. after an action."""

    initial_rpn: int
    initial_ap: str
    revised_rpn: int
    revised_ap: str
    rpn_delta: int  # revised − initial; negative means risk was reduced
    ap_reduced: bool  # did Action Priority drop a band (Low < Medium < High)?


class Action(StrictModel):
    """A tracked action on a failure mode, with optional re-rated S/O/D.

    `s_after` / `o_after` / `d_after` are the ratings *after* the action; any left
    `None` are treated as unchanged from the original when computing effectiveness.
    """

    owner: Annotated[str, pydantic.Field(min_length=1, max_length=200)]
    status: Annotated[ActionStatus, pydantic.Field(strict=False)] = ActionStatus.OPEN
    due: Annotated[date | None, pydantic.Field(strict=False)] = None
    s_after: Rating | None = None
    o_after: Rating | None = None
    d_after: Rating | None = None

    def effectiveness(self, severity: int, occurrence: int, detection: int) -> Effectiveness:
        """Compare the original (severity, occurrence, detection) against the
        revised ratings (the `*_after` overrides, falling back to the original for
        any left unset). Original scores are never mutated.
        """
        revised_s = severity if self.s_after is None else self.s_after
        revised_o = occurrence if self.o_after is None else self.o_after
        revised_d = detection if self.d_after is None else self.d_after

        initial_ap = action_priority(severity, occurrence, detection)
        revised_ap = action_priority(revised_s, revised_o, revised_d)
        initial_rpn = rpn(severity, occurrence, detection)
        revised_rpn = rpn(revised_s, revised_o, revised_d)

        return Effectiveness(
            initial_rpn=initial_rpn,
            initial_ap=initial_ap,
            revised_rpn=revised_rpn,
            revised_ap=revised_ap,
            rpn_delta=revised_rpn - initial_rpn,
            ap_reduced=AP_ORDER[revised_ap] < AP_ORDER[initial_ap],
        )
