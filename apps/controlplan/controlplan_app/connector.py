"""
connector.py
FMEA → Control Plan connector engine (W06-2, issue #84).

Engine + typed output only — no UI (W06-3, #85) and no CP→SPC→FMEA loop (Week 7).
Maps a relational FMEA (``quality_core.schema.relational.RelationalFMEA``) into the
existing #83 Control Plan output contract (``controlplan_app.schema.ControlPlanDataset``)
— that schema is NOT redefined here.

Decisions taken (SME-confirmed — see ``.pipeline/spec.md`` "SME RESOLUTIONS"):

- **Q1 granularity:** one ``ControlPlanRow`` per ``FailureMode``.
- **Q2 characteristic:** ``f"{function.component} — {failure_mode.description}"``;
  on collision, append the failure-mode id and, if that still collides (``FailureMode.id``
  is unique only within a Function, not across the dataset), keep extending with an
  incrementing counter suffix until genuinely unique — so ``ControlPlanDataset``'s
  unique-characteristic rule never raises on legitimately distinct rows. This is a
  naming convention, not an FMEA field.
- **Q3 recommended_chart:** always ``None`` from :func:`build_control_plan` — the
  relational FMEA carries no data-type/subgroup-size input, and the engine must not
  fabricate one. :func:`recommend_chart` still ships as the standards core for
  W06-3/enrichment to call once a characteristic is classified.
- **Q4 placeholders:** ``sample_size``, ``frequency``, ``reaction_plan`` have no FMEA
  source; see the ``# ponytail:``-marked module constants below. ``lsl``/``usl``/
  ``target`` legitimately map to ``None`` (nullable in the schema).
- **Q5 row set:** every failure mode becomes a row (no threshold/``min_ap`` filter),
  sorted highest-risk first.
- **Q6 chart boundary:** ``2 <= n <= 9 -> Xbar-R``, ``n >= 10 -> Xbar-S`` — flagged in
  ``apps/controlplan/docs/ASSUMPTIONS_LOG.md`` for primary-source (AIAG) confirmation.

Standards citation (chart-selection rule table): AIAG SPC Reference Manual, 4th Ed.
(2005) — variable-data chart selection (I-MR / Xbar-R / Xbar-S) and attribute-data
chart selection (p / c / u; ``np`` folds into ``p`` — the schema's ``SPCChart`` Literal
has no ``np`` key). Same source already cited by the SPC app
(``apps/spc/docs/ASSUMPTIONS_LOG.md``) and by ``quality_core.scoring`` for the AP table.

Prioritization (AP-then-RPN) reuses ``quality_core.scoring`` and mirrors the tie-break
discipline of ``apps/fmea/fmea_app/ap_engine.py:rank_by_ap``.
"""
from __future__ import annotations

from typing import Literal

from quality_core.schema.relational import FailureLink, FailureMode, RelationalFMEA
from quality_core.scoring import AP_ORDER, action_priority, rpn

from controlplan_app.schema import ControlPlanDataset, ControlPlanRow, SPCChart

DataType = Literal["variable", "attribute"]

# ponytail: no FMEA source for sample plan / inspection cadence / containment text —
# documented placeholders the W06-3 authoring UI will let a user edit per row.
_DEFAULT_SAMPLE_SIZE = 1
_DEFAULT_FREQUENCY = "per shift"


def _reaction_plan(effect_description: str) -> str:
    # ponytail: templated stub, not an FMEA field — W06-3 UI makes this editable.
    return f"Contain and investigate; failure effect: {effect_description}."


def recommend_chart(
    data_type: DataType,
    subgroup_size: int,
    *,
    defect_based: bool = False,
    constant_sample: bool = True,
) -> SPCChart:
    """Standards rule table (AIAG SPC Reference Manual, 4th Ed.) -> an ``SPCChart`` key.

    Variable data: ``n == 1`` -> ``I-MR``; ``2 <= n <= 9`` -> ``Xbar-R``;
    ``n >= 10`` -> ``Xbar-S`` (the Xbar-R/Xbar-S boundary is flagged in
    ``apps/controlplan/docs/ASSUMPTIONS_LOG.md`` for primary-source confirmation).

    Attribute data: classifying units good/bad (``defect_based=False``) -> ``p``
    regardless of sample-size constancy (``np`` folds into ``p`` — no schema key);
    counting defects per unit (``defect_based=True``) -> ``c`` for a constant sample,
    ``u`` for a variable sample.

    Raises ``ValueError`` if ``subgroup_size < 1``.
    """
    if subgroup_size < 1:
        raise ValueError(f"subgroup_size must be >= 1, got {subgroup_size!r}")

    if data_type == "variable":
        if subgroup_size == 1:
            return "I-MR"
        if subgroup_size <= 9:
            return "Xbar-R"
        return "Xbar-S"

    # attribute data
    if not defect_based:
        return "p"
    return "c" if constant_sample else "u"


def _worst_link(failure_mode: FailureMode) -> tuple[FailureLink, int, str]:
    """Return the failure mode's worst-risk link with its (rpn, ap), by (AP, RPN, row_id).

    Copies the entity-lookup traversal of ``relational_to_flat``
    (``quality_core.schema.relational:247``): S/O/D come from the effect/cause/control
    an entity each link points to.
    """
    effects = {e.id: e for e in failure_mode.effects}
    causes = {c.id: c for c in failure_mode.causes}
    controls = {c.id: c for c in failure_mode.controls}

    best: tuple[FailureLink, int, str] | None = None
    best_key: tuple[int, int, int] | None = None
    for link in failure_mode.links:
        effect = effects[link.effect_id]
        cause = causes[link.cause_id]
        control = controls[link.control_id]
        link_rpn = rpn(effect.severity, cause.occurrence, control.detection)
        link_ap = action_priority(effect.severity, cause.occurrence, control.detection)
        # Deterministic tie-break: AP, then RPN, then row_id (edge cases section).
        key = (AP_ORDER[link_ap], link_rpn, link.row_id)
        if best_key is None or key > best_key:
            best_key = key
            best = (link, link_rpn, link_ap)
    assert best is not None  # FailureMode.links has min_length=1
    return best


def build_control_plan(fmea: RelationalFMEA) -> ControlPlanDataset:
    """One ``ControlPlanRow`` per ``FailureMode`` (Q1), sorted highest-risk first.

    Fields with no FMEA source (`sample_size`, `frequency`, `reaction_plan`,
    `recommended_chart=None`, `lsl`/`usl`/`target=None`) are defaulted per the
    module docstring's Q3/Q4 decisions.
    """
    entries: list[tuple[str, str, int, str, str]] = []  # characteristic, method, rpn, ap, reaction
    seen_characteristics: set[str] = set()

    for function in fmea.functions:
        for failure_mode in function.failure_modes:
            link, link_rpn, link_ap = _worst_link(failure_mode)
            effects = {e.id: e for e in failure_mode.effects}
            controls = {c.id: c for c in failure_mode.controls}
            worst_effect = effects[link.effect_id]
            worst_control = controls[link.control_id]

            characteristic = f"{function.component} — {failure_mode.description}"
            if characteristic in seen_characteristics:
                # ponytail: failure_mode.id is unique only within a Function, not
                # across the dataset — keep extending with a counter suffix until
                # the value is genuinely unique (see spec "NEEDS-WORK FIX").
                base = f"{characteristic} ({failure_mode.id})"
                characteristic, suffix = base, 2
                while characteristic in seen_characteristics:
                    characteristic = f"{base} #{suffix}"
                    suffix += 1
            seen_characteristics.add(characteristic)

            entries.append(
                (
                    characteristic,
                    worst_control.description,
                    link_rpn,
                    link_ap,
                    _reaction_plan(worst_effect.description),
                )
            )

    # Sort descending by (AP ordinal, RPN); stable tie-break on characteristic
    # (final tie-break, per "edge cases" — repeated runs stay reproducible).
    entries.sort(key=lambda e: (AP_ORDER[e[3]], e[2], e[0]), reverse=True)

    rows = [
        ControlPlanRow(
            characteristic=characteristic,
            lsl=None,
            usl=None,
            target=None,
            measurement_method=measurement_method,
            sample_size=_DEFAULT_SAMPLE_SIZE,
            frequency=_DEFAULT_FREQUENCY,
            recommended_chart=None,
            reaction_plan=reaction_plan,
        )
        for characteristic, measurement_method, _rpn, _ap, reaction_plan in entries
    ]
    return ControlPlanDataset(rows=rows)
