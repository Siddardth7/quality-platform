"""Ranked-retrieval metrics: Recall@k, Precision@k, MRR, nDCG@k (M4-4, #285).

Pure functions over a ranked list of ids and a relevance judgement. They import
nothing from ``store.py`` / ``chunk.py`` on purpose: the metric *math* is what CI can
verify deterministically, against synthetic ranked lists of known relevance. Retrieval
*quality* numbers need a real embedder and are a local hand-run (ASSUMPTIONS_LOG
RULE 10 / RULE 14) — ``FakeEmbedder``'s hash vectors carry no semantic similarity, so
any threshold asserted against them would be noise dressed as a gate.

Conventions, applied uniformly:

- An empty relevance judgement scores **0.0, never an exception** — the same
  "an empty result is a legitimate answer" convention as
  :meth:`~quality_database_app.store.VectorStore.search`.
- ``k`` beyond the length of ``retrieved`` truncates; it never pads and never raises.
- ``k < 1`` is a caller bug and fails loud.
- Duplicate ids in ``retrieved`` are counted once toward recall (a set intersection)
  but still consume a rank slot in precision — a store that returns the same chunk
  twice has wasted a slot, and the score should say so.
"""

from __future__ import annotations

import math


def _top_k(retrieved: list[str], k: int) -> list[str]:
    """The first ``k`` ranked ids, rejecting a non-positive ``k``."""
    if k < 1:
        raise ValueError(f"k must be >= 1, got {k}.")
    return retrieved[:k]


def recall_at_k(retrieved: list[str], relevant: set[str], k: int) -> float:
    """Fraction of the relevant ids that appear in the top ``k``."""
    top = _top_k(retrieved, k)
    if not relevant:
        return 0.0
    return len(set(top) & relevant) / len(relevant)


def precision_at_k(retrieved: list[str], relevant: set[str], k: int) -> float:
    """Fraction of the top ``k`` ranked ids that are relevant.

    The denominator is ``min(k, len(retrieved))``: scoring a store that could only
    return three hits as if it had returned ``k`` would punish it for the filter, not
    for the ranking.
    """
    top = _top_k(retrieved, k)
    if not top:
        return 0.0
    return sum(1 for item_id in top if item_id in relevant) / len(top)


def mrr(retrieved: list[str], relevant: set[str]) -> float:
    """Reciprocal of the rank of the first relevant id; 0.0 if none is retrieved."""
    for rank, item_id in enumerate(retrieved, start=1):
        if item_id in relevant:
            return 1.0 / rank
    return 0.0


def ndcg_at_k(retrieved: list[str], relevance: dict[str, float], k: int) -> float:
    """Normalized discounted cumulative gain over the top ``k``.

    Binary or graded relevance both work: ``relevance`` maps an id to its gain, and an
    id absent from it has gain 0. The ideal ranking is the ``k`` highest gains in the
    judgement, so an unretrievable relevant id (a ``never-ship`` chunk filtered out by
    default) legitimately drags the score down rather than being quietly excused.
    """
    top = _top_k(retrieved, k)
    dcg = sum(
        relevance.get(item_id, 0.0) / math.log2(position + 2)
        for position, item_id in enumerate(top)
    )
    ideal = sorted(relevance.values(), reverse=True)[:k]
    idcg = sum(gain / math.log2(position + 2) for position, gain in enumerate(ideal))
    if idcg == 0:
        return 0.0
    return dcg / idcg
