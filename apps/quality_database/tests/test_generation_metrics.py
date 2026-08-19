"""Generation metrics (M4-4, #285): serving-policy scoring, refusal, hallucination.

Includes the acceptance's mandatory negative control: a deliberately wrong citation is
caught (citation_accuracy < 1.0 and is_hallucination True).
"""

from __future__ import annotations

import pytest
from quality_database_app.evalset import GoldItem
from quality_database_app.generation_metrics import (
    CandidateAnswer,
    FakeAnswerGenerator,
    citation_accuracy,
    faithfulness,
    groundedness,
    hallucination_rate,
    is_hallucination,
    pair_answers,
    quoted_spans,
    refusal_correctness,
)


def _item(**over: object) -> GoldItem:
    base = dict(
        item_id="i1", domain="msa", tier="page-pinned", question="what is the MSA rule?",
        source_id="msa-4th", region="whole-document", standard="MSA", page=42,
        serving_flag="paraphrase-and-point", answerable=True, derived_from="RULE 1",
    )
    base.update(over)
    return GoldItem(**base)  # type: ignore[arg-type]


def _ans(**over: object) -> CandidateAnswer:
    base = dict(item_id="i1", text="the process is capable",
                cited_source_id="msa-4th", cited_region="whole-document", cited_page=42)
    base.update(over)
    return CandidateAnswer(**base)  # type: ignore[arg-type]


# ---- the mandatory negative control -------------------------------------------------
def test_wrong_citation_is_caught() -> None:
    item = _item()
    wrong = _ans(cited_page=999)                       # deliberately wrong page
    ca = citation_accuracy(item, wrong)
    assert ca.score < 1.0                               # locator scored field-by-field
    assert is_hallucination(item, wrong) is True        # a wrong citation is a hallucination
    # ...and a right citation is not
    assert citation_accuracy(item, _ans()).score == 1.0
    assert is_hallucination(item, _ans()) is False


def test_faithfulness_bars_verbatim_from_paraphrase_and_point() -> None:
    item = _item(serving_flag="paraphrase-and-point")
    quoting = _ans(text='the manual says "capability is 1.33"')
    assert faithfulness(item, quoting).score == 0.0     # any quoted span from p&p -> 0
    assert faithfulness(item, _ans(text="capability is adequate")).score == 1.0


def test_faithfulness_quote_tier_within_cap() -> None:
    item = _item(serving_flag="quote", tier="coarse", page=None)
    assert faithfulness(item, _ans(text='it notes "under 10 percent"')).score == 1.0
    over = _ans(text='"' + " ".join(["w"] * 60) + '"')
    assert faithfulness(item, over).score == 0.0        # quoted span exceeds the cap


def test_groundedness_locator_vs_excerpt() -> None:
    item = _item()
    assert groundedness(item, _ans()).score == 1.0
    assert groundedness(item, _ans(cited_region="other")).score == 0.0
    q = _item(serving_flag="quote", expected_excerpt="under 10 percent")
    assert groundedness(q, _ans(text="it is Under 10 Percent here")).score == 1.0
    assert groundedness(q, _ans(text="something else")).score == 0.0


def test_refusal_correctness_both_failure_modes() -> None:
    answerable = _item(answerable=True)
    unanswerable = _item(serving_flag="never-ship", answerable=False, tier="coarse", page=None)
    assert refusal_correctness(answerable, _ans()).score == 1.0            # answered, correct
    assert refusal_correctness(answerable, _ans(refused=True)).score == 0.0  # refused answerable
    assert refusal_correctness(unanswerable, _ans(refused=True)).score == 1.0  # correctly refused
    ans_never = refusal_correctness(unanswerable, _ans())
    assert ans_never.score == 0.0 and "must be refused" in ans_never.detail   # licensing breach


def test_refusal_scores_neutral_metrics() -> None:
    item = _item()
    refused = _ans(refused=True)
    assert faithfulness(item, refused).score == 1.0
    assert groundedness(item, refused).score == 1.0
    # refusing an answerable item -> citation_accuracy 0; refusing an unanswerable -> 1
    assert citation_accuracy(item, refused).score == 0.0
    unanswerable = _item(serving_flag="never-ship", answerable=False, tier="coarse", page=None)
    assert citation_accuracy(unanswerable, _ans(refused=True)).score == 1.0
    assert is_hallucination(item, refused) is False


def test_quoted_spans_straight_and_curly() -> None:
    assert quoted_spans('a "straight" and “curly” span') == ["straight", "curly"]
    assert quoted_spans("none here") == []


def test_pair_answers_and_hallucination_rate() -> None:
    items = [_item(item_id="a"), _item(item_id="b")]
    answers = [_ans(item_id="a"), _ans(item_id="b", cited_page=1)]  # b wrong
    assert hallucination_rate(items, answers) == 0.5
    with pytest.raises(ValueError, match="no answer for gold item"):
        pair_answers(items, [_ans(item_id="a")])
    with pytest.raises(ValueError, match="unknown gold item"):
        pair_answers(items, [_ans(item_id="a"), _ans(item_id="b"), _ans(item_id="z")])
    with pytest.raises(ValueError, match="empty eval"):
        hallucination_rate([], [])


def test_fake_answer_generator() -> None:
    gen = FakeAnswerGenerator({"q?": _ans()})
    assert gen.answer("q?").item_id == "i1"
    with pytest.raises(ValueError, match="no scripted answer"):
        gen.answer("unknown")
