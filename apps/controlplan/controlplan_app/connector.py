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
  source; see the ``# ponytail:``-marked module constants below. Every emitted row
  therefore carries ``sample_plan_is_placeholder=True`` (F-10, #196) so a consumer
  cannot mistake a defaulted sample plan for an FMEA-derived one. ``lsl``/``usl``/
  ``target`` legitimately map to ``None`` (nullable in the schema).
- **Q5 row set:** every failure mode becomes a row (no threshold/``min_ap`` filter),
  sorted highest-risk first.
- **Q6 chart boundary:** ``2 <= n <= 9 -> Xbar-R``, ``10 <= n <= 12 -> Xbar-S`` (``n > 12``
  raises — F-07, #196; ``XBAR_S_CONSTANTS`` stops at 12). The 9-vs-10 switch point is flagged
  in ``apps/controlplan/docs/ASSUMPTIONS_LOG.md`` for primary-source (AIAG) confirmation.

Standards citation (chart-selection rule table): AIAG SPC Reference Manual, 4th Ed.
(2005) — variable-data chart selection (I-MR / Xbar-R / Xbar-S) and attribute-data
chart selection (p / c / u; ``np`` folds into ``p`` — the schema's ``SPCChart`` Literal
has no ``np`` key). Same source already cited by the SPC app
(``apps/spc/docs/ASSUMPTIONS_LOG.md``) and by ``quality_core.scoring`` for the AP table.

Prioritization (AP-then-RPN) reuses ``quality_core.scoring`` and mirrors the tie-break
discipline of ``apps/fmea/fmea_app/ap_engine.py:rank_by_ap``.

**W07-2 (#89) OQ1 — persisted join key.** ``build_control_plan`` also stamps each row's
``source_cause_id`` (``controlplan_app.schema.ControlPlanRow``) with a deterministic id
for its worst-risk cause (:func:`_source_cause_id`), and :func:`source_index` exposes the
same lookup (plus the cause's live description/occurrence/component) for the SPC page to
enrich at runtime. Both share :func:`_iter_named_modes` for the characteristic-naming
traversal, so their keys cannot diverge — the correctness-critical point (see spec
"Refactor").
"""
from __future__ import annotations

from typing import Iterator, Literal

from quality_core.schema.relational import Cause, FailureLink, FailureMode, Function, RelationalFMEA
from quality_core.scoring import AP_ORDER, action_priority, rpn
from quality_core.spc.constants import XBAR_S_CONSTANTS

from controlplan_app.schema import ControlPlanDataset, ControlPlanRow, SPCChart

DataType = Literal["variable", "attribute"]

#: Largest subgroup size the SPC engine can actually compute an X-bar/S chart for.
#: Read from the constants table rather than hard-coded, so the guard tracks the
#: table (F-07, #196). AIAG publishes no A3/B3/B4/c4 above n=12, so the table is
#: deliberately not extended — see `docs/ASSUMPTIONS_LOG.md` RULE 1.
_MAX_XBAR_S_N = max(XBAR_S_CONSTANTS)

# ponytail: no FMEA source for sample plan / inspection cadence / containment text —
# documented placeholders the W06-3 authoring UI will let a user edit per row. Every
# row build_control_plan emits is stamped `sample_plan_is_placeholder=True` (F-10,
# #196) so a downstream consumer can tell these apart from engineered values.
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
    ``10 <= n <= 12`` -> ``Xbar-S`` (the Xbar-R/Xbar-S boundary is flagged in
    ``apps/controlplan/docs/ASSUMPTIONS_LOG.md`` for primary-source confirmation).
    Above ``n = 12`` there is no computable variable chart — ``XBAR_S_CONSTANTS``
    stops there and ``compute_xbar_s`` rejects it — so this raises rather than
    naming a chart the engine cannot compute (F-07, #196).

    Attribute data: classifying units good/bad (``defect_based=False``) -> ``p``
    regardless of sample-size constancy (``np`` folds into ``p`` — no schema key);
    counting defects per unit (``defect_based=True``) -> ``c`` for a constant sample,
    ``u`` for a variable sample. The upper bound does **not** apply here: attribute
    sample sizes have no constants table and are routinely large.

    Raises ``ValueError`` if ``subgroup_size < 1``, or if it exceeds
    ``max(XBAR_S_CONSTANTS)`` (12) for variable data.
    """
    if subgroup_size < 1:
        raise ValueError(f"subgroup_size must be >= 1, got {subgroup_size!r}")

    if data_type == "variable":
        if subgroup_size == 1:
            return "I-MR"
        if subgroup_size <= 9:
            return "Xbar-R"
        if subgroup_size > _MAX_XBAR_S_N:
            raise ValueError(
                f"subgroup_size {subgroup_size} exceeds the largest supported X-bar/S "
                f"subgroup size ({_MAX_XBAR_S_N}); AIAG publishes no A3/B3/B4/c4 "
                f"constants above it."
            )
        return "Xbar-S"

    # attribute data
    if not defect_based:
        return "p"
    return "c" if constant_sample else "u"


def _worst_link(failure_mode: FailureMode) -> tuple[FailureLink, int, str]:
    """Return the failure mode's worst-risk link with its (rpn, ap), by (AP, RPN, row_id).

    S/O/D come from the effect/cause/control entity each link points to, resolved
    by ``FailureMode.resolve``.
    """
    best: tuple[FailureLink, int, str] | None = None
    best_key: tuple[int, int, int] | None = None
    for link in failure_mode.links:
        effect, cause, control = failure_mode.resolve(link)
        link_rpn = rpn(effect.severity, cause.occurrence, control.detection)
        link_ap = action_priority(effect.severity, cause.occurrence, control.detection)
        # Deterministic tie-break: AP, then RPN, then row_id (edge cases section).
        key = (AP_ORDER[link_ap], link_rpn, link.row_id)
        if best_key is None or key > best_key:
            best_key = key
            best = (link, link_rpn, link_ap)
    assert best is not None  # FailureMode.links has min_length=1
    return best


def _iter_named_modes(
    fmea: RelationalFMEA,
) -> Iterator[tuple[str, Function, FailureMode, FailureLink]]:
    """Yield ``(characteristic, function, failure_mode, worst_link)`` once per
    ``FailureMode``, in traversal order.

    The characteristic-naming + collision-suffix rule (Q2) lives here exactly
    once, so :func:`build_control_plan` and :func:`source_index` cannot derive
    diverging characteristic keys for the same FMEA (OQ1's correctness point).
    """
    seen_characteristics: set[str] = set()
    for function in fmea.functions:
        for failure_mode in function.failure_modes:
            link, _link_rpn, _link_ap = _worst_link(failure_mode)

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

            yield characteristic, function, failure_mode, link


def _source_cause_id(function: Function, failure_mode: FailureMode, cause: Cause) -> str:
    """Deterministic, dataset-wide-unique join key for a ``Cause`` (OQ1, #89).

    ``Cause.id`` is already stable but is only guaranteed unique *within* one
    ``FailureMode`` (``relational.py``'s ``check_ids_and_links``). Composing it
    with its ``Function``/``FailureMode`` — each unique at their own scope
    (``RelationalFMEA.check_global_uniqueness`` / ``Function.check_unique_
    failure_mode_ids``) — gives a dataset-wide-unique, deterministic string
    without inventing a new ID scheme. One place; both ``build_control_plan``
    and :func:`source_index` call this so the two never disagree.
    """
    return f"{function.id}::{failure_mode.id}::{cause.id}"


def build_control_plan(fmea: RelationalFMEA) -> ControlPlanDataset:
    """One ``ControlPlanRow`` per ``FailureMode`` (Q1), sorted highest-risk first.

    Fields with no FMEA source (`sample_size`, `frequency`, `reaction_plan`,
    `recommended_chart=None`, `lsl`/`usl`/`target=None`) are defaulted per the
    module docstring's Q3/Q4 decisions, and every row is stamped
    `sample_plan_is_placeholder=True` so the defaulted sample plan / frequency /
    reaction plan are distinguishable downstream (F-10, #196).
    `source_cause_id` (OQ1, #89) is the one
    field with a real FMEA-derived value beyond risk/description text — see
    :func:`_source_cause_id`.
    """
    # characteristic, method, rpn, ap, reaction, source_cause_id
    entries: list[tuple[str, str, int, str, str, str]] = []

    for characteristic, function, failure_mode, link in _iter_named_modes(fmea):
        worst_effect, worst_cause, worst_control = failure_mode.resolve(link)
        link_rpn = rpn(worst_effect.severity, worst_cause.occurrence, worst_control.detection)
        link_ap = action_priority(
            worst_effect.severity, worst_cause.occurrence, worst_control.detection
        )

        entries.append(
            (
                characteristic,
                worst_control.description,
                link_rpn,
                link_ap,
                _reaction_plan(worst_effect.description),
                _source_cause_id(function, failure_mode, worst_cause),
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
            source_cause_id=source_cause_id,
            sample_plan_is_placeholder=True,
        )
        for characteristic, measurement_method, _rpn, _ap, reaction_plan, source_cause_id in entries
    ]
    return ControlPlanDataset(rows=rows)


def source_index(fmea: RelationalFMEA) -> dict[str, dict[str, object]]:
    """Map each Control Plan characteristic -> its source-cause identity (OQ1, #89).

    Keys are identical to ``build_control_plan(fmea).rows[*].characteristic``
    (shared :func:`_iter_named_modes` — see its docstring, and the edge-case test
    asserting key-set parity). This is the *runtime* companion to
    ``ControlPlanRow.source_cause_id``: the persisted field only survives as an
    id string, but the SPC->FMEA feedback loop also wants the cause's live
    description/occurrence/component for the current session, which only the
    in-memory ``RelationalFMEA`` has.

    Value: ``{failure_mode_id, cause_id, cause_description, occurrence,
    component}`` — ``cause_id`` and ``occurrence``/``cause_description`` come
    from the same worst-risk cause :func:`build_control_plan` used
    (``_worst_link``).
    """
    index: dict[str, dict[str, object]] = {}
    for characteristic, function, failure_mode, link in _iter_named_modes(fmea):
        _, cause, _ = failure_mode.resolve(link)
        index[characteristic] = {
            "failure_mode_id": failure_mode.id,
            "cause_id": _source_cause_id(function, failure_mode, cause),
            "cause_description": cause.description,
            "occurrence": cause.occurrence,
            "component": function.component,
        }
    return index
