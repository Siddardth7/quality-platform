"""Tests for spc_app/fmea_feedback.py — SPC OOC -> candidate FMEA feedback (W07-2, #89).

Pure module, held to 100% line+branch (a fresh module, DoD gate 3). Mirrors
apps/spc/tests/test_control_plan_config.py's structure.
"""

from __future__ import annotations

import pytest

from spc_app.fmea_feedback import (
    FEEDBACK_STATE_KEY,
    SOURCE_INDEX_STATE_KEY,
    _rate_to_occurrence,
    build_occurrence_feedback,
    summarize_violations,
)

SOURCE = {
    "failure_mode_id": "F1-M1",
    "cause_id": "F1::F1-M1::F1-M1-C1",
    "cause_description": "Resin starvation",
    "occurrence": 4,
    "component": "Prepreg Ply",
}


def _violations(*pairs: tuple[int, str]) -> list[dict[str, int | str]]:
    return [{"index": i, "rule": r} for i, r in pairs]


# ---------------------------------------------------------------------------
# State key contracts (cross-app string duplication discipline)
# ---------------------------------------------------------------------------


def test_state_key_contracts():
    assert FEEDBACK_STATE_KEY == "_spc_fmea_feedback"
    assert SOURCE_INDEX_STATE_KEY == "_controlplan_source_index"


# ---------------------------------------------------------------------------
# summarize_violations
# ---------------------------------------------------------------------------


def test_summarize_violations_empty():
    assert summarize_violations([]) == (0, [])


def test_summarize_violations_same_index_two_rules_counts_one_index_two_rules():
    violations = _violations((3, "WE Rule 1"), (3, "WE Rule 2"))
    count, rules = summarize_violations(violations)
    assert count == 1
    assert rules == ["WE Rule 1", "WE Rule 2"]


def test_summarize_violations_multiple_indices():
    violations = _violations((1, "WE Rule 1"), (5, "WE Rule 1"), (9, "WE Rule 1"))
    count, rules = summarize_violations(violations)
    assert count == 3
    assert rules == ["WE Rule 1"]


def test_summarize_violations_multiple_rules_deduped_and_sorted():
    violations = _violations((1, "Nelson Rule 5"), (2, "WE Rule 1"), (3, "Nelson Rule 5"))
    count, rules = summarize_violations(violations)
    assert count == 3
    assert rules == ["Nelson Rule 5", "WE Rule 1"]  # sorted


# ---------------------------------------------------------------------------
# _rate_to_occurrence — AIAG-4 (2008) / SAE J1739 occurrence rate table
# rank : upper bound
#  1 : 1/1,500,000   2 : 1/150,000   3 : 1/15,000   4 : 1/2,000   5 : 1/400
#  6 : 1/80          7 : 1/20        8 : 1/8        9 : 1/3       10 : 1/2 (>=)
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("rate", "expected_rank"),
    [
        (0.0, 1),
        (1 / 3_000_000, 1),
        (1 / 1_500_000, 1),  # exact boundary -> still rank 1
        (1 / 1_500_000 + 1e-12, 2),  # just above boundary -> next band
        (1 / 150_000, 2),
        (1 / 15_000, 3),
        (1 / 2_000, 4),
        (1 / 400, 5),
        (1 / 80, 6),
        (1 / 20, 7),
        (1 / 8, 8),
        (1 / 3, 9),
        (1 / 2, 10),  # exact boundary -> rank 10
        (0.9, 10),  # well above rank-10 band -> clamps to 10
        (1.0, 10),
    ],
)
def test_rate_to_occurrence_matches_aiag4_bands(rate, expected_rank):
    assert _rate_to_occurrence(rate) == expected_rank


# ---------------------------------------------------------------------------
# build_occurrence_feedback
# ---------------------------------------------------------------------------


def test_build_occurrence_feedback_returns_none_when_no_violations():
    assert (
        build_occurrence_feedback(
            characteristic="Ply misalignment",
            stream="ply_misalignment",
            rule_set="Western Electric",
            violations=[],
            total_points=100,
            source=SOURCE,
        )
        is None
    )


def test_build_occurrence_feedback_happy_path_with_source():
    violations = _violations((1, "WE Rule 1"), (2, "WE Rule 1"), (3, "WE Rule 2"))
    payload = build_occurrence_feedback(
        characteristic="Prepreg Ply — Ply misalignment (>±2°)",
        stream="ply_misalignment",
        rule_set="Western Electric",
        violations=violations,
        total_points=20,
        source=SOURCE,
    )
    assert payload is not None
    assert payload["characteristic"] == "Prepreg Ply — Ply misalignment (>±2°)"
    assert payload["stream"] == "ply_misalignment"
    assert payload["rule_set"] == "Western Electric"
    assert payload["ooc"] is True
    assert payload["violating_points"] == 3
    assert payload["rules"] == ["WE Rule 1", "WE Rule 2"]
    assert payload["ooc_rate"] == pytest.approx(3 / 20)
    assert payload["source_failure_mode_id"] == "F1-M1"
    assert payload["source_cause_id"] == "F1::F1-M1::F1-M1-C1"
    assert payload["source_cause_description"] == "Resin starvation"
    assert payload["component"] == "Prepreg Ply"
    # current_occurrence echoes source, unchanged
    assert payload["current_occurrence"] == 4
    assert payload["current_occurrence"] == SOURCE["occurrence"]
    # suggested_occurrence is a distinct key, computed, never mutating current
    assert "suggested_occurrence" in payload
    assert isinstance(payload["suggested_occurrence"], int)
    assert 1 <= payload["suggested_occurrence"] <= 10
    assert payload["suggested_occurrence"] == _rate_to_occurrence(3 / 20)
    assert payload["suggested_occurrence"] != payload["current_occurrence"]
    assert "Occurrence 4" in payload["capa_prompt"]
    assert "Prepreg Ply — Ply misalignment (>±2°)" in payload["capa_prompt"]
    assert "AIAG-4" in payload["capa_prompt"]


def test_build_occurrence_feedback_source_none_yields_none_source_fields():
    violations = _violations((0, "WE Rule 1"))
    payload = build_occurrence_feedback(
        characteristic="Unlinked characteristic",
        stream="some_stream",
        rule_set="Nelson",
        violations=violations,
        total_points=10,
        source=None,
    )
    assert payload is not None
    assert payload["source_failure_mode_id"] is None
    assert payload["source_cause_id"] is None
    assert payload["source_cause_description"] is None
    assert payload["component"] is None
    assert payload["current_occurrence"] is None
    # generic prompt still names the characteristic and doesn't crash
    assert "Unlinked characteristic" in payload["capa_prompt"]
    assert "unknown" in payload["capa_prompt"]
    assert "unlinked cause" in payload["capa_prompt"]
    # suggested_occurrence is still computed even with no source
    assert isinstance(payload["suggested_occurrence"], int)


def test_build_occurrence_feedback_total_points_zero_defensive_rate():
    # Defensive guard: violations non-empty but total_points<=0 shouldn't
    # divide-by-zero; ooc_rate defaults to 1.0 (worst case) per the module.
    violations = _violations((0, "WE Rule 1"))
    payload = build_occurrence_feedback(
        characteristic="Edge case",
        stream="stream",
        rule_set="Western Electric",
        violations=violations,
        total_points=0,
        source=None,
    )
    assert payload is not None
    assert payload["ooc_rate"] == 1.0
    assert payload["suggested_occurrence"] == 10


def test_build_occurrence_feedback_capa_prompt_names_current_and_suggested():
    violations = _violations((0, "WE Rule 1"))
    payload = build_occurrence_feedback(
        characteristic="Char X",
        stream="stream_x",
        rule_set="Western Electric",
        violations=violations,
        total_points=1000,  # tiny rate -> low suggested rank
        source=SOURCE,
    )
    assert payload["suggested_occurrence"] == _rate_to_occurrence(1 / 1000)
    assert f"Occurrence {SOURCE['occurrence']}" in payload["capa_prompt"]
    assert "candidate Occurrence" in payload["capa_prompt"]


def test_build_occurrence_feedback_never_mutates_source_mapping():
    # Human-in-the-loop guarantee: the function must not write back into the
    # source mapping it was given (pure read).
    source = dict(SOURCE)
    violations = _violations((0, "WE Rule 1"))
    build_occurrence_feedback(
        characteristic="Char",
        stream="stream",
        rule_set="Western Electric",
        violations=violations,
        total_points=10,
        source=source,
    )
    assert source == SOURCE
