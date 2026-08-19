"""The eval runner: gold set in, scored report out (M4-4, #285).

Two halves that share one gold set. ``run_retrieval_eval`` asks the store the gold
questions and scores the ranking; ``run_generation_eval`` scores candidate answers.
``run()`` does whichever half it was given the machinery for, so the retrieval half can
be hand-run against a real embedder while CI exercises both against the fakes.

**What CI can and cannot conclude from this.** ``FakeEmbedder``'s vectors are
sha256-derived and carry no semantic similarity, so the Recall@k / MRR / nDCG numbers a
CI run produces are noise. Tests against it assert *plumbing* — report shape, item
count, that filters are honoured — never a numeric quality threshold. Real
retrieval-quality numbers are a local hand-run with the real embedder (see the app
README), the same posture as M4-3's real indexing run. ``write_report`` exists so M5-4
can gate on a report produced that way.

**``never-ship`` items score 0 recall, on purpose.** ``VectorStore.search`` filters
them out by default and this runner does not override that. Their expected chunk is
therefore unreachable, which is the correct behaviour of the licensing gate M4-3 built,
not a retrieval defect — those items are scored by ``refusal_correctness`` on the
generation side, where the right answer is a refusal.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path

from quality_database_app.embed import Embedder
from quality_database_app.evalset import GoldItem, is_relevant
from quality_database_app.generation_metrics import (
    AnswerGenerator,
    CandidateAnswer,
    ScoreResult,
    citation_accuracy,
    faithfulness,
    groundedness,
    hallucination_rate,
    pair_answers,
    refusal_correctness,
)
from quality_database_app.retrieval_metrics import mrr, ndcg_at_k, precision_at_k, recall_at_k
from quality_database_app.store import VectorStore

DEFAULT_K = 5


@dataclass(frozen=True)
class RetrievalReport:
    """Per-item retrieval scores plus their means. ``k`` is carried, not assumed."""

    k: int
    per_item: list[ScoreResult]
    recall_at_k: float
    precision_at_k: float
    mrr: float
    ndcg_at_k: float


@dataclass(frozen=True)
class GenerationReport:
    """Per-item generation scores plus their means, and the hallucination rate."""

    per_item: list[ScoreResult]
    faithfulness_mean: float
    groundedness_mean: float
    citation_accuracy_mean: float
    refusal_correctness_mean: float
    hallucination_rate: float


@dataclass(frozen=True)
class EvalReport:
    """Whichever halves were run. ``None`` means "not run", never "scored zero"."""

    retrieval: RetrievalReport | None
    generation: GenerationReport | None


def _mean(results: list[ScoreResult], metric: str) -> float:
    """Mean score for one metric across ``results``; the metric is always present."""
    scores = [result.score for result in results if result.metric == metric]
    return sum(scores) / len(scores)


def run_retrieval_eval(
    store: VectorStore,
    embedder: Embedder,
    gold_items: list[GoldItem],
    k: int = DEFAULT_K,
) -> RetrievalReport:
    """Query ``store`` with every gold question and score the ranking.

    Relevance comes from :func:`~quality_database_app.evalset.is_relevant`, so a
    page-pinned item is scored on its exact chunk and a coarse one on
    ``(source_id, region)`` — the tier difference lives there and nowhere else.
    """
    if not gold_items:
        raise ValueError("no gold items to score — an empty eval would be vacuous.")

    vectors = embedder.embed([item.question for item in gold_items])
    per_item: list[ScoreResult] = []
    for item, vector in zip(gold_items, vectors, strict=True):
        relevant = {chunk.chunk_id for chunk in store.chunks if is_relevant(item, chunk)}
        retrieved = [hit.chunk.chunk_id for hit in store.search(vector, k=k)]
        relevance = dict.fromkeys(relevant, 1.0)
        detail = f"{len(retrieved)} hit(s) for {len(relevant)} relevant chunk(s)"
        per_item.extend(
            [
                ScoreResult(item.item_id, "recall_at_k", recall_at_k(retrieved, relevant, k), detail),
                ScoreResult(
                    item.item_id, "precision_at_k", precision_at_k(retrieved, relevant, k), detail
                ),
                ScoreResult(item.item_id, "mrr", mrr(retrieved, relevant), detail),
                ScoreResult(
                    item.item_id, "ndcg_at_k", ndcg_at_k(retrieved, relevance, k), detail
                ),
            ]
        )
    return RetrievalReport(
        k=k,
        per_item=per_item,
        recall_at_k=_mean(per_item, "recall_at_k"),
        precision_at_k=_mean(per_item, "precision_at_k"),
        mrr=_mean(per_item, "mrr"),
        ndcg_at_k=_mean(per_item, "ndcg_at_k"),
    )


def run_generation_eval(
    gold_items: list[GoldItem], answers: list[CandidateAnswer]
) -> GenerationReport:
    """Score every candidate answer against its gold item.

    ``pair_answers`` fails loud on a missing or extra answer, so a partial run can
    never be reported as a full one.
    """
    pairs = pair_answers(gold_items, answers)
    per_item = [
        score(item, answer)
        for item, answer in pairs
        for score in (faithfulness, groundedness, citation_accuracy, refusal_correctness)
    ]
    return GenerationReport(
        per_item=per_item,
        faithfulness_mean=_mean(per_item, "faithfulness"),
        groundedness_mean=_mean(per_item, "groundedness"),
        citation_accuracy_mean=_mean(per_item, "citation_accuracy"),
        refusal_correctness_mean=_mean(per_item, "refusal_correctness"),
        hallucination_rate=hallucination_rate(gold_items, answers),
    )


def run(
    gold_items: list[GoldItem],
    store: VectorStore | None = None,
    embedder: Embedder | None = None,
    generator: AnswerGenerator | None = None,
    k: int = DEFAULT_K,
) -> EvalReport:
    """Run whichever halves the caller supplied the machinery for.

    A store needs an embedder to query it with, so both or neither; a generator is
    independent. Supplying nothing yields an all-``None`` report rather than an
    exception — "nothing was run" is a legitimate, and visible, outcome.
    """
    retrieval = (
        run_retrieval_eval(store, embedder, gold_items, k=k)
        if store is not None and embedder is not None
        else None
    )
    generation = (
        run_generation_eval(gold_items, [generator.answer(item.question) for item in gold_items])
        if generator is not None
        else None
    )
    return EvalReport(retrieval=retrieval, generation=generation)


def write_report(report: EvalReport, path: Path) -> None:
    """Write the report as deterministic JSON: pretty, ordered, no wall-clock content.

    ASSUMPTIONS_LOG RULE 7 again — a re-run over unchanged inputs must produce a
    byte-identical file, so M5-4 can diff two runs and see only real drift.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(asdict(report), indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
