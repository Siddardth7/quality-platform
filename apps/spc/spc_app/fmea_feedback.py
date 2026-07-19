"""SPC out-of-control signal -> candidate FMEA occurrence feedback (W07-2, #89).

Closes the loop's second leg: **SPC -> FMEA**. When the selected Control-Plan
characteristic's chart trips a rule violation (Western Electric or Nelson —
whichever `rule_set` the SPC page has selected, OQ5), this module derives a
**candidate** occurrence-rating / CAPA payload naming the source FMEA cause —
it NEVER writes a new rating, it only proposes one for a human to review.

Pure functions only: no Streamlit import, no `controlplan_app` import (the
standalone SPC app never has `controlplan_app` on `sys.path` — mirrors
`spc_app/control_plan_config.py`'s discipline exactly).
"""

from __future__ import annotations

from typing import Mapping

#: Session-state key the SPC Control Charts page writes the candidate to, and
#: `apps/fmea/app.py::render_fmea` reads (as a plain dict — OQ4, no import).
FEEDBACK_STATE_KEY = "_spc_fmea_feedback"

#: Session-state key holding `controlplan_app.connector.source_index(...)`.
# ponytail: string contract mirrored from
# controlplan_app.pages.control_plan._SOURCE_INDEX_STATE_KEY — duplicated (not
# imported), same discipline as `control_plan_config.PLAN_STATE_KEY`.
SOURCE_INDEX_STATE_KEY = "_controlplan_source_index"


def summarize_violations(
    violations: list[dict[str, int | str]],
) -> tuple[int, list[str]]:
    """(# distinct violating point indices, sorted-unique rule names).

    A point flagged by two different rules counts once toward the index count,
    but both rule names still appear in the (deduped) list — the two counts are
    independent (see the module's edge-case tests). ``[]`` -> ``(0, [])``.
    """
    if not violations:
        return (0, [])
    indices = {int(violation["index"]) for violation in violations}
    rules = sorted({str(violation["rule"]) for violation in violations})
    return (len(indices), rules)


# ---------------------------------------------------------------------------
# Occurrence ranking table (OQ2 — rate-anchored, SME-directed & confirmed).
#
# This is the AIAG-family occurrence table whose ranks are keyed to a predicted
# incident rate (incidents per items/opportunities). That rate-band table is the
# standards basis this module maps an observed SPC out-of-control failing-rate
# onto, below.
#
# Source: **AIAG FMEA-4 (4th Ed., 2008) / SAE J1739 — Occurrence ranking table.**
# Each rank's value is that band's incident-rate upper bound (rank 10 = "very
# high / failure almost inevitable", ≥1 in 2; rank 1 = "remote", ≤1 in 1,500,000).
# The ten values below are exactly that published table.
#
# NOTE on standard edition (SME-confirmed, see .pipeline/spec.md OQ2 resolution):
# the harmonised AIAG-VDA FMEA Handbook (1st Ed., 2019) does NOT define a numeric
# incident-rate occurrence table — its Occurrence rating is qualitative, keyed to
# prevention-control effectiveness. So a rate→rank mapping can only be anchored to
# the legacy AIAG-4 / SAE J1739 rate table, which is what this module cites and
# uses. `suggested_occurrence` is a candidate under that standard; a shop running
# pure AIAG-VDA 2019 Occurrence criteria treats it as supporting SPC evidence.
_OCCURRENCE_BANDS: tuple[tuple[int, float], ...] = (
    (1, 1 / 1_500_000),  # <= 1 in 1,500,000  — remote
    (2, 1 / 150_000),    #    1 in 150,000    — low
    (3, 1 / 15_000),     #    1 in 15,000     — low
    (4, 1 / 2_000),      #    1 in 2,000      — moderate
    (5, 1 / 400),        #    1 in 400        — moderate
    (6, 1 / 80),         #    1 in 80         — moderate
    (7, 1 / 20),         #    1 in 20         — high
    (8, 1 / 8),          #    1 in 8          — high
    (9, 1 / 3),          #    1 in 3          — very high
    (10, 1 / 2),         # >= 1 in 2          — very high (almost inevitable)
)


def _rate_to_occurrence(rate: float) -> int:
    """Map an observed OOC failing-rate onto the AIAG-4 / J1739 occurrence band table.

    Returns the lowest-numbered rank whose incident-rate upper bound is >= the
    observed rate (the smallest band the rate still fits inside). A rate above
    rank 10's own bound clamps to 10 — the scale's ceiling, matching how the
    standard's top band ("almost inevitable") is open-ended upward.
    """
    for rank, threshold in _OCCURRENCE_BANDS:
        if rate <= threshold:
            return rank
    return 10


def build_occurrence_feedback(
    *,
    characteristic: str,
    stream: str,
    rule_set: str,
    violations: list[dict[str, int | str]],
    total_points: int,
    source: Mapping[str, object] | None,
) -> dict[str, object] | None:
    """Candidate feedback payload, or ``None`` when ``violations`` is empty
    (loop only fires on OOC — the trigger, OQ5's `rule_set` is carried through
    for provenance).

    ``total_points`` is the chart's plotted point count (the "opportunities" in
    the AIAG-4 / J1739 rate definition); ``violating_points / total_points`` is the
    OOC failing-rate :func:`_rate_to_occurrence` maps onto the cited band table
    to produce ``suggested_occurrence`` (OQ2). This is a **candidate**: nothing
    in this module or its caller writes it back to the FMEA model — a human
    reviews and decides (see ``capa_prompt``).

    Payload keys (all plain / JSON-safe so the FMEA page reads without
    importing ``spc_app``): ``characteristic``, ``stream``, ``rule_set``,
    ``ooc=True``, ``violating_points``, ``rules``, ``ooc_rate``,
    ``source_failure_mode_id``, ``source_cause_id``, ``source_cause_description``,
    ``current_occurrence`` (unchanged — echoes the FMEA's present rating),
    ``suggested_occurrence`` (the candidate — never auto-applied), ``component``,
    ``capa_prompt``.

    ``source is None`` (characteristic not in the Control Plan source index, or
    no Control Plan loaded yet) still yields a payload — ``source_*`` fields are
    ``None`` and ``capa_prompt`` names the characteristic generically.
    """
    if not violations:
        return None

    violating_points, rules = summarize_violations(violations)
    ooc_rate = (violating_points / total_points) if total_points > 0 else 1.0
    suggested_occurrence = _rate_to_occurrence(ooc_rate)

    if source is None:
        failure_mode_id = cause_id = cause_description = component = None
        current_occurrence: object | None = None
    else:
        failure_mode_id = source.get("failure_mode_id")
        cause_id = source.get("cause_id")
        cause_description = source.get("cause_description")
        component = source.get("component")
        current_occurrence = source.get("occurrence")

    cause_label = cause_description or "an unlinked cause (no Control Plan source found)"
    current_label = current_occurrence if current_occurrence is not None else "unknown"
    # ponytail: fixed CAPA prompt template — a copy/paste starting point, not a
    # generated recommendation; W07-3+ can make this editable if SMEs want to
    # tailor wording per characteristic.
    capa_prompt = (
        f"Characteristic '{characteristic}' went out of statistical control "
        f"({violating_points} point(s), {', '.join(rules)}). Source cause "
        f"'{cause_label}' is currently rated Occurrence {current_label}; the "
        f"observed out-of-control rate maps to a candidate Occurrence "
        f"{suggested_occurrence} (AIAG-4 / SAE J1739 occurrence rate table). Review "
        "the occurrence rating / open a CAPA — this is a candidate, not an "
        "applied change."
    )

    return {
        "characteristic": characteristic,
        "stream": stream,
        "rule_set": rule_set,
        "ooc": True,
        "violating_points": violating_points,
        "rules": rules,
        "ooc_rate": ooc_rate,
        "source_failure_mode_id": failure_mode_id,
        "source_cause_id": cause_id,
        "source_cause_description": cause_description,
        "current_occurrence": current_occurrence,
        "suggested_occurrence": suggested_occurrence,
        "component": component,
        "capa_prompt": capa_prompt,
    }
