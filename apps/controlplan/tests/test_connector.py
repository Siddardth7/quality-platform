"""Dedicated test suite for controlplan_app/connector.py (W06-4, #86, issue #84 engine).

Held to 100% line + branch (DoD gate 3, new module). Covers: field mapping per the
SME resolutions, AP-then-RPN prioritization (incl. ties), worst-link selection
(mid-list winner, non-update branch), the characteristic-collision fallback,
schema round-trip, empty FMEA, and the `recommend_chart` rule table cell-by-cell
(mirroring the `tests/test_scoring.py` AP-grid verification style).
"""

from __future__ import annotations

import pytest
from controlplan_app.connector import build_control_plan, recommend_chart
from controlplan_app.schema import ControlPlanDataset
from quality_core.schema.relational import (
    Cause,
    Control,
    Effect,
    FailureLink,
    FailureMode,
    Function,
    RelationalFMEA,
)
from quality_core.scoring import AP_ORDER, action_priority, rpn

# ---------------------------------------------------------------------------
# Fixture builders — one link per (effect, cause, control) unless a test needs
# multiple links on one failure mode (worst-link selection tests).
# ---------------------------------------------------------------------------


def _fm(
    fm_id: str,
    description: str,
    s: int,
    o: int,
    d: int,
    *,
    row_id: int,
    effect_desc: str = "Effect",
    cause_desc: str = "Cause",
    control_desc: str = "Control",
) -> FailureMode:
    """A FailureMode with exactly one effect/cause/control/link."""
    return FailureMode(
        id=fm_id,
        description=description,
        effects=[Effect(id=f"{fm_id}-E1", description=effect_desc, severity=s)],
        causes=[Cause(id=f"{fm_id}-C1", description=cause_desc, occurrence=o)],
        controls=[Control(id=f"{fm_id}-CT1", description=control_desc, detection=d)],
        links=[
            FailureLink(row_id=row_id, effect_id=f"{fm_id}-E1", cause_id=f"{fm_id}-C1", control_id=f"{fm_id}-CT1")
        ],
    )


def _function(fn_id: str, component: str, failure_modes: list[FailureMode], *, process_step: str = "Step") -> Function:
    return Function(
        id=fn_id, process_step=process_step, component=component, description="Function", failure_modes=failure_modes
    )


# ---------------------------------------------------------------------------
# Field mapping (Q2-Q4)
# ---------------------------------------------------------------------------


def test_field_mapping_single_row() -> None:
    fm = _fm(
        "F1-M1",
        "Incomplete weld",
        s=9,
        o=8,
        d=8,
        row_id=1,
        effect_desc="Joint fails in service",
        control_desc="Visual weld inspection",
    )
    fmea = RelationalFMEA(functions=[_function("F1", "Bracket", [fm])])

    dataset = build_control_plan(fmea)

    assert len(dataset.rows) == 1
    row = dataset.rows[0]
    assert row.characteristic == "Bracket — Incomplete weld"
    assert row.measurement_method == "Visual weld inspection"
    assert row.lsl is None
    assert row.usl is None
    assert row.target is None
    assert row.sample_size == 1
    assert row.frequency == "per shift"
    assert row.recommended_chart is None
    assert row.reaction_plan == "Contain and investigate; failure effect: Joint fails in service."


def test_one_row_per_failure_mode() -> None:
    fms = [
        _fm("F1-M1", "Mode A", s=3, o=3, d=3, row_id=1),
        _fm("F1-M2", "Mode B", s=4, o=4, d=4, row_id=2),
        _fm("F1-M3", "Mode C", s=5, o=5, d=5, row_id=3),
    ]
    fmea = RelationalFMEA(functions=[_function("F1", "Widget", fms)])

    dataset = build_control_plan(fmea)

    assert len(dataset.rows) == 3
    assert {r.characteristic for r in dataset.rows} == {
        "Widget — Mode A",
        "Widget — Mode B",
        "Widget — Mode C",
    }


def test_empty_fmea_yields_empty_dataset() -> None:
    dataset = build_control_plan(RelationalFMEA(functions=[]))
    assert dataset == ControlPlanDataset(rows=[])


# ---------------------------------------------------------------------------
# AP-then-RPN prioritization
# ---------------------------------------------------------------------------


def test_ap_is_primary_over_rpn() -> None:
    # (9, 6, 1) -> High AP, rpn=54; (3, 7, 10) -> Low AP, rpn=210.
    # A lower-RPN High-AP row must still outrank a higher-RPN Low-AP row.
    assert action_priority(9, 6, 1) == "High"
    assert action_priority(3, 7, 10) == "Low"
    assert rpn(9, 6, 1) < rpn(3, 7, 10)

    fm_high_ap_low_rpn = _fm("F1-M1", "High AP mode", s=9, o=6, d=1, row_id=1)
    fm_low_ap_high_rpn = _fm("F1-M2", "Low AP mode", s=3, o=7, d=10, row_id=2)
    fmea = RelationalFMEA(functions=[_function("F1", "Comp", [fm_low_ap_high_rpn, fm_high_ap_low_rpn])])

    dataset = build_control_plan(fmea)

    assert [r.characteristic for r in dataset.rows] == [
        "Comp — High AP mode",
        "Comp — Low AP mode",
    ]


def test_rpn_breaks_ties_within_same_ap_band() -> None:
    # Both High AP; rpn 576 > rpn 54, so it must rank first.
    assert action_priority(9, 8, 8) == "High"
    assert action_priority(9, 6, 1) == "High"
    assert rpn(9, 8, 8) > rpn(9, 6, 1)

    fm_low_rpn = _fm("F1-M1", "Low RPN mode", s=9, o=6, d=1, row_id=1)
    fm_high_rpn = _fm("F1-M2", "High RPN mode", s=9, o=8, d=8, row_id=2)
    fmea = RelationalFMEA(functions=[_function("F1", "Comp", [fm_low_rpn, fm_high_rpn])])

    dataset = build_control_plan(fmea)

    assert [r.characteristic for r in dataset.rows] == [
        "Comp — High RPN mode",
        "Comp — Low RPN mode",
    ]


def test_characteristic_breaks_ties_when_ap_and_rpn_are_equal() -> None:
    # Identical (S, O, D) on both -> identical AP and RPN; final tie-break is
    # the characteristic string itself, descending (per the reverse=True sort).
    fm_alpha = _fm("F1-M1", "Alpha failure", s=5, o=5, d=5, row_id=1)
    fm_beta = _fm("F1-M2", "Beta failure", s=5, o=5, d=5, row_id=2)
    fmea = RelationalFMEA(functions=[_function("F1", "Comp", [fm_alpha, fm_beta])])

    dataset = build_control_plan(fmea)

    assert [r.characteristic for r in dataset.rows] == [
        "Comp — Beta failure",  # "Beta" > "Alpha" lexicographically
        "Comp — Alpha failure",
    ]


# ---------------------------------------------------------------------------
# Worst-link selection (multi-link failure modes)
# ---------------------------------------------------------------------------


def _multi_link_fm(fm_id: str, description: str, triples: list[tuple[int, int, int, str, str]]) -> FailureMode:
    """A FailureMode with one link per (s, o, d, effect_desc, control_desc) triple."""
    effects = [Effect(id=f"{fm_id}-E{i}", description=eff, severity=s) for i, (s, _o, _d, eff, _ctl) in enumerate(triples, 1)]
    causes = [Cause(id=f"{fm_id}-C{i}", description="Cause", occurrence=o) for i, (_s, o, _d, _eff, _ctl) in enumerate(triples, 1)]
    controls = [
        Control(id=f"{fm_id}-CT{i}", description=ctl, detection=d) for i, (_s, _o, d, _eff, ctl) in enumerate(triples, 1)
    ]
    links = [
        FailureLink(row_id=i, effect_id=f"{fm_id}-E{i}", cause_id=f"{fm_id}-C{i}", control_id=f"{fm_id}-CT{i}")
        for i in range(1, len(triples) + 1)
    ]
    return FailureMode(id=fm_id, description=description, effects=effects, causes=causes, controls=controls, links=links)


def test_worst_link_is_not_necessarily_first_or_last() -> None:
    # link1: (3,3,3) Low rpn=27; link2: (9,8,8) High rpn=576 <- worst; link3: (5,5,5) Low rpn=125.
    assert action_priority(3, 3, 3) == "Low"
    assert action_priority(9, 8, 8) == "High"
    assert action_priority(5, 5, 5) == "Low"

    fm = _multi_link_fm(
        "F1-M1",
        "Multi-link mode",
        [
            (3, 3, 3, "Effect 1", "Control 1"),
            (9, 8, 8, "Effect 2 (worst)", "Control 2 (worst)"),
            (5, 5, 5, "Effect 3", "Control 3"),
        ],
    )
    fmea = RelationalFMEA(functions=[_function("F1", "Comp", [fm])])

    dataset = build_control_plan(fmea)

    row = dataset.rows[0]
    assert row.measurement_method == "Control 2 (worst)"
    assert "Effect 2 (worst)" in row.reaction_plan


def test_worst_link_first_link_stays_best_when_later_link_is_weaker() -> None:
    # Exercises the "key is NOT greater than best_key" (non-update) branch: link1
    # is already the best, so link2 must not overwrite it.
    assert action_priority(9, 8, 8) == "High"
    assert action_priority(3, 3, 3) == "Low"

    fm = _multi_link_fm(
        "F1-M1",
        "Descending-risk mode",
        [
            (9, 8, 8, "Effect 1 (worst)", "Control 1 (worst)"),
            (3, 3, 3, "Effect 2", "Control 2"),
        ],
    )
    fmea = RelationalFMEA(functions=[_function("F1", "Comp", [fm])])

    dataset = build_control_plan(fmea)

    row = dataset.rows[0]
    assert row.measurement_method == "Control 1 (worst)"
    assert "Effect 1 (worst)" in row.reaction_plan


# ---------------------------------------------------------------------------
# Characteristic-collision fallback (Q2)
# ---------------------------------------------------------------------------


def test_characteristic_collision_falls_back_to_failure_mode_id() -> None:
    # Two functions share a component; each has a failure mode with the same
    # description, so the base characteristic string collides.
    fm1 = _fm("F1-M1", "Incomplete weld", s=9, o=6, d=1, row_id=1)  # High AP -> sorts first
    fm2 = _fm("F2-M1", "Incomplete weld", s=3, o=3, d=3, row_id=2)  # Low AP -> sorts second
    fmea = RelationalFMEA(
        functions=[
            _function("F1", "Bracket", [fm1], process_step="Weld"),
            _function("F2", "Bracket", [fm2], process_step="Rework"),
        ]
    )

    dataset = build_control_plan(fmea)

    characteristics = [r.characteristic for r in dataset.rows]
    assert characteristics == [
        "Bracket — Incomplete weld",
        "Bracket — Incomplete weld (F2-M1)",
    ]
    # Uniqueness holds (would raise on construction otherwise) and the fallback
    # itself can't re-collide, since FailureMode.id is unique within a function.
    assert len(set(characteristics)) == len(characteristics)


def test_characteristic_collision_across_many_functions_with_same_fm_id() -> None:
    # Regression (NEEDS-WORK fix): >=3 Functions sharing component AND
    # failure_mode.description AND failure_mode.id. FailureMode.id is only
    # unique *within* a Function, so the single `(failure_mode.id)` fallback
    # alone would still collide from the 3rd function onward. The fix loops
    # with an incrementing `#N` suffix until genuinely unique.
    fms = [_fm("M1", "weld", s=1, o=1, d=1, row_id=i) for i in range(1, 6)]  # 5 functions
    fmea = RelationalFMEA(
        functions=[
            _function(f"F{i}", "Bracket", [fm], process_step=f"Step{i}")
            for i, fm in enumerate(fms, start=1)
        ]
    )

    dataset = build_control_plan(fmea)  # must not raise

    assert len(dataset.rows) == 5
    characteristics = {r.characteristic for r in dataset.rows}
    assert len(characteristics) == 5
    # Insertion order (F1..F5, matching fmea.functions) drives the fallback
    # sequence: first row keeps the base string; each subsequent collision
    # extends via `(failure_mode.id)` then an incrementing `#N` counter —
    # exercises the while loop's multi-iteration body, not just entry.
    assert characteristics == {
        "Bracket — weld",
        "Bracket — weld (M1)",
        "Bracket — weld (M1) #2",
        "Bracket — weld (M1) #3",
        "Bracket — weld (M1) #4",
    }


def test_dataset_round_trips_cleanly_through_schema_with_many_rows() -> None:
    fms = [_fm(f"F1-M{i}", f"Mode {i}", s=(i % 10) + 1, o=(i % 10) + 1, d=(i % 10) + 1, row_id=i) for i in range(1, 21)]
    fmea = RelationalFMEA(functions=[_function("F1", "Comp", fms)])

    dataset = build_control_plan(fmea)

    assert isinstance(dataset, ControlPlanDataset)
    assert len(dataset.rows) == 20
    assert len({r.characteristic for r in dataset.rows}) == 20


# ---------------------------------------------------------------------------
# recommend_chart — rule table, cell by cell (AIAG SPC Reference Manual, 4th Ed.)
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("data_type", "n", "kwargs", "expected"),
    [
        # Variable: I-MR at n=1, Xbar-R across 2..9 (boundary at 9), Xbar-S at
        # n=10 and beyond (boundary at 10).
        ("variable", 1, {}, "I-MR"),
        ("variable", 2, {}, "Xbar-R"),
        ("variable", 5, {}, "Xbar-R"),
        ("variable", 9, {}, "Xbar-R"),
        ("variable", 10, {}, "Xbar-S"),
        ("variable", 50, {}, "Xbar-S"),
        # Attribute: defectives -> p regardless of sample-size constancy (np folds
        # into p); defects -> c (constant sample) or u (variable sample).
        ("attribute", 5, {"defect_based": False, "constant_sample": True}, "p"),
        ("attribute", 5, {"defect_based": False, "constant_sample": False}, "p"),
        ("attribute", 5, {"defect_based": True, "constant_sample": True}, "c"),
        ("attribute", 5, {"defect_based": True, "constant_sample": False}, "u"),
        # Defaults: defect_based=False, constant_sample=True -> p.
        ("attribute", 5, {}, "p"),
    ],
)
def test_recommend_chart_rule_table_every_cell(data_type, n, kwargs, expected) -> None:
    assert recommend_chart(data_type, n, **kwargs) == expected


@pytest.mark.parametrize("subgroup_size", [0, -1, -100])
def test_recommend_chart_rejects_invalid_subgroup_size(subgroup_size: int) -> None:
    with pytest.raises(ValueError, match="subgroup_size"):
        recommend_chart("variable", subgroup_size)


def test_recommend_chart_never_returns_np() -> None:
    # `np` is intentionally absent from the SPCChart Literal (folds into `p`).
    results = set()
    for n in range(1, 15):
        results.add(recommend_chart("variable", n))
    for defect_based in (False, True):
        for constant_sample in (False, True):
            results.add(recommend_chart("attribute", 5, defect_based=defect_based, constant_sample=constant_sample))
    assert "np" not in results
    assert results <= {"I-MR", "Xbar-R", "Xbar-S", "p", "c", "u"}
