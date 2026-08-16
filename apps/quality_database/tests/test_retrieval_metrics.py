"""Retrieval metric math (M4-4, #285) — deterministic, over synthetic ranked lists."""

from __future__ import annotations

import math

import pytest
from quality_database_app.retrieval_metrics import (
    mrr,
    ndcg_at_k,
    precision_at_k,
    recall_at_k,
)


def test_recall_at_k() -> None:
    assert recall_at_k(["a", "b", "c"], {"a", "c"}, 3) == 1.0
    assert recall_at_k(["a", "x", "y"], {"a", "c"}, 3) == 0.5
    assert recall_at_k(["x"], {"a"}, 3) == 0.0
    assert recall_at_k(["a"], set(), 3) == 0.0  # empty relevant -> 0, not error


def test_precision_at_k_denominator_is_min_k_len() -> None:
    assert precision_at_k(["a", "b"], {"a"}, 5) == 0.5  # only 2 retrieved -> /2, not /5
    assert precision_at_k(["a", "b", "c"], {"a", "b", "c"}, 3) == 1.0
    assert precision_at_k([], {"a"}, 3) == 0.0


def test_mrr_first_relevant_rank() -> None:
    assert mrr(["x", "a", "y"], {"a"}) == 0.5
    assert mrr(["a"], {"a"}) == 1.0
    assert mrr(["x", "y"], {"a"}) == 0.0


def test_ndcg_perfect_and_imperfect() -> None:
    assert ndcg_at_k(["a", "b"], {"a": 1.0, "b": 1.0}, 2) == 1.0
    # relevant item at rank 2 instead of 1 -> discounted below 1.0
    got = ndcg_at_k(["x", "a"], {"a": 1.0}, 2)
    assert math.isclose(got, (1.0 / math.log2(3)) / 1.0)
    assert ndcg_at_k(["x"], {}, 2) == 0.0  # no relevance -> 0, not error


def test_k_below_one_is_a_caller_bug() -> None:
    for fn in (recall_at_k, precision_at_k):
        with pytest.raises(ValueError, match="k must be >= 1"):
            fn(["a"], {"a"}, 0)
    with pytest.raises(ValueError, match="k must be >= 1"):
        ndcg_at_k(["a"], {"a": 1.0}, 0)
