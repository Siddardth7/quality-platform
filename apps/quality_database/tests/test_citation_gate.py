"""The citation-accuracy / copyright-safe-serving CI gate (M5-4, #290).

This module is the gate: it scores a hand-authored, correct-by-construction answer per
item of the committed ``docs/eval/gold_set.json`` and asserts the resulting
:class:`~quality_database_app.eval.GenerationReport` clears the four threshold constants
in ``generation_metrics``. Any regression in the scoring code, the serving-policy
helpers it reuses, or the gold set itself fails ``CI / gate`` — the new module runs
inside both the full-suite step and the existing "Quality Database coverage gate" step,
so no new CI wiring exists or is needed.

**What this proves:** that the *eval/report* layer catches a fabricated citation, an
answered-but-unanswerable question, and an over-cap or barred verbatim excerpt.

**What it does not prove:** anything about a real generator's citation quality. The
fixture below is correct by construction and the thresholds are the floor that fact
implies — a structural bar, not a calibrated measurement (ASSUMPTIONS_LOG RULE 17). CI
has no model and no network, so a real-generator-calibrated gate is deferred.

Complementary to ``test_query_unit.py``'s quote-cap and hallucinated-citation tests,
which prove the *engine* refuses at answer time. Different layer; not duplicated here.
"""

from __future__ import annotations

import pytest
from quality_database_app.eval import GenerationReport, run_generation_eval
from quality_database_app.evalset import GoldItem, load_gold_set
from quality_database_app.generation_metrics import (
    MAX_HALLUCINATION_RATE,
    MIN_CITATION_ACCURACY,
    MIN_GROUNDEDNESS,
    MIN_REFUSAL_CORRECTNESS,
    CandidateAnswer,
)

# The committed gold set, in file order. Hand-authored against
# ``docs/eval/gold_set.json`` so that adding, removing or renaming an item shows up in
# this diff rather than silently shrinking the gate's coverage.
GOLD_ITEM_IDS = (
    "msa-grr-acceptability",
    "msa-ndc-minimum",
    "msa-anova-preferred",
    "fmea-rpn-threshold",
    "fmea-ap-emphasis-order",
    "fmea-ap-tables-shared",
    "fmea-pfmea-occurrence-table-refusal",
    "spc-nelson-special-cause-tests",
    "spc-western-electric-zone-rules",
    "spc-nist-control-chart-chapter",
    "controlplan-montgomery-basis",
    "secom-assumptions-provenance",
    "spc-nelson-rules-reproduction-refusal",
)

# The two ``never-ship`` items, whose only correct answer is a refusal.
UNANSWERABLE_ITEM_IDS = frozenset(
    {"fmea-pfmea-occurrence-table-refusal", "spc-nelson-rules-reproduction-refusal"}
)

# The one ``quote``-tier item — the only gold item any verbatim excerpt is permitted
# from at all, and then only within the cap.
QUOTE_TIER_ITEM_ID = "spc-nist-control-chart-chapter"

# 51 words: one over ``evalset.MAX_QUOTE_WORDS``.
OVER_CAP_QUOTE = " ".join(["monitoring"] * 51)


def _gold_items() -> list[GoldItem]:
    return load_gold_set().items


def _scripted_correct_answers(items: list[GoldItem]) -> list[CandidateAnswer]:
    """One correct-by-construction answer per gold item.

    An answerable item gets a paraphrase citing its own locator and quoting nothing; a
    ``never-ship`` item gets a refusal. This is what a perfect generator would emit, so
    every metric scores 1.0 (and ``hallucination_rate`` 0.0) by construction.
    """
    answers = []
    for item in items:
        if item.item_id in UNANSWERABLE_ITEM_IDS:
            answers.append(
                CandidateAnswer(
                    item_id=item.item_id,
                    text="That source may not be reproduced.",
                    refused=True,
                )
            )
        else:
            answers.append(
                CandidateAnswer(
                    item_id=item.item_id,
                    text=f"Paraphrased answer, see [{item.source_id}:{item.region}].",
                    cited_source_id=item.source_id,
                    cited_region=item.region,
                    cited_page=item.page,
                )
            )
    return answers


def _mutated(item_id: str, **changes: object) -> list[CandidateAnswer]:
    """A fresh scripted fixture with one item's answer mutated — never shared state."""
    return [
        answer.model_copy(update=changes) if answer.item_id == item_id else answer
        for answer in _scripted_correct_answers(_gold_items())
    ]


def _report(answers: list[CandidateAnswer]) -> GenerationReport:
    return run_generation_eval(_gold_items(), answers)


# --- 1. The gold set is the one this fixture was authored against -----------------


def test_fixture_covers_every_committed_gold_item() -> None:
    items = _gold_items()
    assert [item.item_id for item in items] == list(GOLD_ITEM_IDS)
    assert {item.item_id for item in items if not item.answerable} == set(UNANSWERABLE_ITEM_IDS)


# --- 2. The gate --------------------------------------------------------------------


def test_gate_passes_on_the_known_correct_fixture() -> None:
    report = _report(_scripted_correct_answers(_gold_items()))

    assert report.citation_accuracy_mean >= MIN_CITATION_ACCURACY
    assert report.groundedness_mean >= MIN_GROUNDEDNESS
    assert report.refusal_correctness_mean >= MIN_REFUSAL_CORRECTNESS
    assert report.hallucination_rate <= MAX_HALLUCINATION_RATE


# --- 3. Negative control A — a fabricated citation ----------------------------------


def test_fabricated_citation_fails_the_gate() -> None:
    # A wrong ``source_id`` also drops groundedness for that item (the answer no longer
    # points at the gold region) and makes it a hallucination — all three are asserted.
    answers = _mutated("msa-grr-acceptability", cited_source_id="not-a-real-source")

    report = _report(answers)

    assert report.citation_accuracy_mean < MIN_CITATION_ACCURACY
    assert report.groundedness_mean < MIN_GROUNDEDNESS
    assert report.hallucination_rate > MAX_HALLUCINATION_RATE


# --- 4. Negative control B — an unanswerable question answered ----------------------


def test_answering_a_never_ship_question_fails_the_gate() -> None:
    # Answering a ``never-ship`` question is a hallucination by definition too, however
    # well-cited the answer looks; refusal_correctness is the metric this control owns.
    answers = _mutated(
        "spc-nelson-rules-reproduction-refusal",
        text="The Nelson rules read as follows...",
        refused=False,
        cited_source_id="nelson-rules-repro",
        cited_region="whole-document",
    )

    report = _report(answers)

    assert report.refusal_correctness_mean < MIN_REFUSAL_CORRECTNESS
    assert report.hallucination_rate > MAX_HALLUCINATION_RATE


# --- 5. Negative control C — verbatim reproduction beyond the serving policy ---------


@pytest.mark.parametrize(
    ("item_id", "quoted"),
    [
        # Over the quote cap, from the one source quoting is permitted from at all.
        (QUOTE_TIER_ITEM_ID, OVER_CAP_QUOTE),
        # Any verbatim excerpt at all, from a paraphrase-and-point source.
        ("msa-grr-acceptability", "a short verbatim span"),
    ],
)
def test_barred_verbatim_excerpt_fails_the_gate(item_id: str, quoted: str) -> None:
    # Locator and refusal are left correct, so citation_accuracy, groundedness and
    # refusal_correctness all still score 1.0 — hallucination_rate is the only metric
    # this control can move, which is exactly what makes it load-bearing.
    answers = _mutated(item_id, text=f'Answer: "{quoted}"')

    report = _report(answers)

    assert report.hallucination_rate > MAX_HALLUCINATION_RATE
    assert report.citation_accuracy_mean >= MIN_CITATION_ACCURACY
