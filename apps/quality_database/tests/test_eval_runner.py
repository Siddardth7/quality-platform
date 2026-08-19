"""The eval runner (M4-4, #285): plumbing over the fakes, offline and deterministic.

Retrieval assertions check report SHAPE and filter behaviour, never a quality threshold —
FakeEmbedder's hash vectors carry no semantic similarity (eval.py module docstring).
"""

from __future__ import annotations

import json

import pytest
from quality_database_app.chunk import Chunk
from quality_database_app.embed import FakeEmbedder
from quality_database_app.eval import (
    EvalReport,
    run,
    run_generation_eval,
    run_retrieval_eval,
    write_report,
)
from quality_database_app.evalset import GoldItem, is_relevant
from quality_database_app.generation_metrics import CandidateAnswer, FakeAnswerGenerator
from quality_database_app.index import build_index
from quality_database_app.store import VectorStore


def _chunk(cid: str, source_id: str = "msa-4th", serving_flag: str = "paraphrase-and-point") -> Chunk:
    return Chunk(
        chunk_id=cid, chunk_index=0, source_id=source_id, region="whole-document",
        standard="MSA", clause=None, page=1, text=f"text {cid}",
        confidence="high", low_confidence=False, extraction_quality="clean",
        serving_flag=serving_flag, license_class="licensed-commercial",
    )


def _item(item_id: str, source_id: str = "msa-4th", **over: object) -> GoldItem:
    base = dict(
        item_id=item_id, domain="msa", tier="coarse", question=f"q {item_id}?",
        source_id=source_id, region="whole-document", standard="MSA",
        serving_flag="paraphrase-and-point", answerable=True, derived_from="RULE 1",
    )
    base.update(over)
    return GoldItem(**base)  # type: ignore[arg-type]


def _store() -> VectorStore:
    return build_index([_chunk("c1"), _chunk("c2", source_id="fmea-vda-2019")], FakeEmbedder())


def test_run_retrieval_eval_reports_shape() -> None:
    report = run_retrieval_eval(_store(), FakeEmbedder(), [_item("i1")], k=2)
    assert report.k == 2
    metrics = {r.metric for r in report.per_item}
    assert metrics == {"recall_at_k", "precision_at_k", "mrr", "ndcg_at_k"}
    assert 0.0 <= report.recall_at_k <= 1.0


def test_run_generation_eval_means_and_hallucination() -> None:
    items = [_item("a"), _item("b")]
    answers = [
        CandidateAnswer(item_id="a", text="ok", cited_source_id="msa-4th", cited_region="whole-document"),
        CandidateAnswer(item_id="b", text="ok", cited_source_id="WRONG", cited_region="whole-document"),
    ]
    report = run_generation_eval(items, answers)
    assert report.citation_accuracy_mean < 1.0        # b is wrong
    assert report.hallucination_rate == 0.5
    assert report.refusal_correctness_mean == 1.0     # both answered, both answerable


def test_run_dispatches_on_supplied_machinery() -> None:
    items = [_item("i1")]
    # nothing supplied -> both halves None ("not run", not "scored zero")
    assert run(items) == EvalReport(retrieval=None, generation=None)
    # generator only -> generation half runs, retrieval None
    gen = FakeAnswerGenerator({
        "q i1?": CandidateAnswer(item_id="i1", text="ok", cited_source_id="msa-4th",
                                 cited_region="whole-document"),
    })
    rep = run(items, generator=gen)
    assert rep.retrieval is None and rep.generation is not None
    # store + embedder -> retrieval half runs
    rep2 = run(items, store=_store(), embedder=FakeEmbedder())
    assert rep2.retrieval is not None and rep2.generation is None


def test_is_relevant_exact_chunk_vs_coarse_fallback() -> None:
    # page-pinned item with a resolved chunk_id -> exact chunk match only
    pinned = _item("p", tier="page-pinned", page=1, expected_chunk_id="c1")
    assert is_relevant(pinned, _chunk("c1")) is True
    assert is_relevant(pinned, _chunk("c2")) is False
    # coarse item (no expected_chunk_id) -> (source_id, region) fallback
    coarse = _item("co")
    assert is_relevant(coarse, _chunk("anything")) is True                 # same source/region
    assert is_relevant(coarse, _chunk("x", source_id="fmea-vda-2019")) is False


def test_run_retrieval_eval_empty_items_is_vacuous() -> None:
    with pytest.raises(ValueError, match="empty eval would be vacuous"):
        run_retrieval_eval(_store(), FakeEmbedder(), [], k=2)


def test_write_report_is_deterministic(tmp_path) -> None:
    report = run([_item("i1")], store=_store(), embedder=FakeEmbedder())
    p = tmp_path / "report.json"
    write_report(report, p)
    first = p.read_bytes()
    write_report(report, p)
    assert p.read_bytes() == first
    loaded = json.loads(p.read_text())
    assert loaded["generation"] is None and loaded["retrieval"]["k"] == 5
