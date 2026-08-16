"""Scoring a generated answer against a gold item (M4-4, #285).

There is **no LLM here.** #285 defines the metrics and the seam; the generator is M5.
:class:`AnswerGenerator` is the seam and :class:`FakeAnswerGenerator` is the only
implementation CI runs — exactly the split ``embed.py`` uses for
``Embedder``/``FakeEmbedder``, and for the same reason: CI has no network and no model.

Because there is no judge model, every metric below is a **deterministic, rule-based**
score over the answer's *locator* and its *serving-policy compliance*, not a semantic
entailment judgement. That is a real ceiling, stated plainly rather than implied:

- ``faithfulness`` scores faithfulness **to the source's serving contract** — an answer
  that reproduces text it is not permitted to reproduce is unfaithful to the source,
  and this is the one form of unfaithfulness that is checkable without the source in
  hand. Semantic faithfulness needs a judge and arrives with M5.
- ``groundedness`` scores whether the answer is anchored to the right source (and, for
  a ``quote``-tier item, whether it actually carries the expected excerpt).
- ``citation_accuracy`` scores the locator field by field.

**The serving-flag branch (SME-locked, #285 Q4).** A ``paraphrase-and-point`` item
carries no ``expected_excerpt`` — ``evalset.GoldItem`` forbids it — so no scorer here
*can* reward verbatim reproduction from one. It goes further: a quoted span in an
answer to such an item scores ``faithfulness`` 0.0, because the policy bars "any
verbatim excerpt, however short". Only a ``quote``/``serve`` item is scored against
stored text, and only within the cap.

**Refusals.** A refusal makes no claim, so ``faithfulness`` and ``groundedness`` score
it 1.0 and ``citation_accuracy`` scores it by whether refusing was right (there is no
citation to grade). Whether the refusal itself was correct is
:func:`refusal_correctness`'s job alone — one metric owns that verdict, so a wrong
refusal is never double-counted or, worse, averaged away.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Protocol

from quality_core.schema._base import StrictModel

from quality_database_app.evalset import (
    QUOTABLE_FLAGS,
    GoldItem,
    normalise,
    within_quote_cap,
)

#: Straight and curly double-quoted spans. Deliberately simple: this detects that the
#: answer *presents text as a quotation*, which is what the serving policy governs. It
#: does not need the source text to do that — and it must not, since the whole point of
#: a paraphrase-and-point item is that its source text is not committed anywhere here.
_QUOTED_SPAN = re.compile(r'"([^"]+)"|“([^”]+)”')


class CandidateAnswer(StrictModel):
    """One generated (or, in CI, hand-written) answer to a gold item's question."""

    item_id: str
    text: str
    cited_source_id: str | None = None
    cited_region: str | None = None
    cited_page: int | None = None
    refused: bool = False


class AnswerGenerator(Protocol):
    """Anything that answers a question. M5 plugs a real one in here."""

    def answer(self, question: str) -> CandidateAnswer:
        """Answer ``question`` with a citable :class:`CandidateAnswer`."""


class FakeAnswerGenerator:
    """Deterministic stand-in for CI: returns a pre-scripted answer per question.

    Keyed by question rather than by ``item_id`` so it satisfies
    :class:`AnswerGenerator` exactly — the runner asks a question, it does not hand the
    generator the gold item (which would leak the answer key into the generator).
    """

    def __init__(self, scripted: dict[str, CandidateAnswer]) -> None:
        self._scripted = dict(scripted)

    def answer(self, question: str) -> CandidateAnswer:
        if question not in self._scripted:
            raise ValueError(f"FakeAnswerGenerator has no scripted answer for {question!r}.")
        return self._scripted[question]


@dataclass(frozen=True)
class ScoreResult:
    """One metric's verdict on one item, with the reason it reached that verdict."""

    item_id: str
    metric: str
    score: float
    detail: str


def quoted_spans(text: str) -> list[str]:
    """Every span the answer presents as a verbatim quotation."""
    return [straight or curly for straight, curly in _QUOTED_SPAN.findall(text)]


def pair_answers(
    items: list[GoldItem], answers: list[CandidateAnswer]
) -> list[tuple[GoldItem, CandidateAnswer]]:
    """Pair items with their answers by ``item_id``, in gold-set order.

    Fails loud on a missing or extra answer: silently scoring a subset would report a
    partial run as a full one, which is exactly the vacuous pass this eval exists to
    prevent.
    """
    if not items:
        raise ValueError("no gold items to score — an empty eval would be vacuous.")
    by_id = {answer.item_id: answer for answer in answers}
    missing = [item.item_id for item in items if item.item_id not in by_id]
    if missing:
        raise ValueError(f"no answer for gold item(s): {sorted(missing)}")
    extra = sorted(set(by_id) - {item.item_id for item in items})
    if extra:
        raise ValueError(f"answer(s) for unknown gold item(s): {extra}")
    return [(item, by_id[item.item_id]) for item in items]


def faithfulness(item: GoldItem, answer: CandidateAnswer) -> ScoreResult:
    """1.0 when the answer respects the source's serving flag, 0.0 when it does not."""
    if answer.refused:
        return ScoreResult(item.item_id, "faithfulness", 1.0, "refused: nothing asserted")
    spans = quoted_spans(answer.text)
    if item.serving_flag not in QUOTABLE_FLAGS:
        if spans:
            return ScoreResult(
                item.item_id,
                "faithfulness",
                0.0,
                f"serving_flag {item.serving_flag!r} bars any verbatim excerpt, but the "
                f"answer quotes {len(spans)} span(s)",
            )
        return ScoreResult(
            item.item_id, "faithfulness", 1.0, "no verbatim excerpt from a non-quotable source"
        )
    over_cap = [span for span in spans if not within_quote_cap(span)]
    if over_cap:
        return ScoreResult(
            item.item_id, "faithfulness", 0.0, f"{len(over_cap)} quoted span(s) exceed the cap"
        )
    return ScoreResult(item.item_id, "faithfulness", 1.0, "quoted spans are within the cap")


def groundedness(item: GoldItem, answer: CandidateAnswer) -> ScoreResult:
    """1.0 when the answer is anchored to the gold source, 0.0 when it is not.

    For a ``quote``-tier item the anchor is the stored excerpt, matched
    formatting-tolerantly (:func:`~quality_database_app.evalset.normalise`) so markdown
    emphasis or a curly quote cannot produce a false "not grounded" verdict. For a
    ``paraphrase-and-point`` item there is no stored text by policy, so the anchor is
    the ``(source_id, region)`` the answer points at.
    """
    if answer.refused:
        return ScoreResult(item.item_id, "groundedness", 1.0, "refused: nothing to ground")
    if item.expected_excerpt is not None:
        if normalise(item.expected_excerpt) in normalise(answer.text):
            return ScoreResult(
                item.item_id, "groundedness", 1.0, "answer carries the expected excerpt"
            )
        return ScoreResult(
            item.item_id, "groundedness", 0.0, "answer does not carry the expected excerpt"
        )
    if (answer.cited_source_id, answer.cited_region) == (item.source_id, item.region):
        return ScoreResult(
            item.item_id, "groundedness", 1.0, "answer points at the expected source region"
        )
    return ScoreResult(
        item.item_id,
        "groundedness",
        0.0,
        f"answer points at ({answer.cited_source_id}, {answer.cited_region}), expected "
        f"({item.source_id}, {item.region})",
    )


def citation_accuracy(item: GoldItem, answer: CandidateAnswer) -> ScoreResult:
    """Fraction of the gold locator's fields the answer cites correctly.

    Only the fields the gold item actually holds are scored: a coarse item has no
    ``page``, so an answer is neither credited nor punished for one. ``source_id`` and
    ``region`` are always present, so the denominator is never zero.
    """
    if answer.refused:
        score = 0.0 if item.answerable else 1.0
        return ScoreResult(
            item.item_id, "citation_accuracy", score, "refused: no citation offered"
        )
    expected: dict[str, str | int | None] = {
        "source_id": item.source_id,
        "region": item.region,
        "page": item.page,
    }
    actual: dict[str, str | int | None] = {
        "source_id": answer.cited_source_id,
        "region": answer.cited_region,
        "page": answer.cited_page,
    }
    scored = [field for field, value in expected.items() if value is not None]
    wrong = [field for field in scored if actual[field] != expected[field]]
    detail = (
        "locator matches the gold item"
        if not wrong
        else "wrong " + ", ".join(f"{f} ({actual[f]!r} != {expected[f]!r})" for f in wrong)
    )
    return ScoreResult(
        item.item_id, "citation_accuracy", (len(scored) - len(wrong)) / len(scored), detail
    )


def refusal_correctness(item: GoldItem, answer: CandidateAnswer) -> ScoreResult:
    """1.0 when the answer refuses exactly when it should, 0.0 otherwise.

    The two failure modes are reported distinctly, because they are different bugs:
    answering a ``never-ship`` question is a licensing breach, while refusing an
    answerable one is a usability failure. Refusing when required outranks citation
    quality — a right-sounding, correctly-cited answer to an unanswerable question
    still scores 0.0 here.
    """
    if answer.refused == (not item.answerable):
        outcome = "correctly refused" if answer.refused else "correctly answered"
        return ScoreResult(item.item_id, "refusal_correctness", 1.0, outcome)
    if answer.refused:
        return ScoreResult(
            item.item_id, "refusal_correctness", 0.0, "refused an answerable question"
        )
    return ScoreResult(
        item.item_id,
        "refusal_correctness",
        0.0,
        f"answered a question whose source is {item.serving_flag!r} and must be refused",
    )


def is_hallucination(item: GoldItem, answer: CandidateAnswer) -> bool:
    """Whether this answer asserts something it cannot support.

    Three ways to qualify, all of them a claim the source does not back: answering a
    question that had to be refused, citing a locator that is wrong in any field, or
    reproducing text the serving flag bars. A refusal is never a hallucination.
    """
    if answer.refused:
        return False
    return (
        not item.answerable
        or citation_accuracy(item, answer).score < 1.0
        or faithfulness(item, answer).score < 1.0
    )


def hallucination_rate(items: list[GoldItem], answers: list[CandidateAnswer]) -> float:
    """Fraction of gold items whose answer hallucinated. Empty input fails loud."""
    pairs = pair_answers(items, answers)
    return sum(1 for item, answer in pairs if is_hallucination(item, answer)) / len(pairs)
