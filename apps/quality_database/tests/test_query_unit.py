"""Unit tests for the RAG query engine (M5-1, #287).

Synthetic in-process fixtures only — never the licensed corpus, never a real embedder,
never a live generator — so the whole suite runs on CI with ``FakeEmbedder`` alone, the
same discipline as ``test_retrieval_smoke.py``.

**Hermeticity.** No test depends on ``REFUSAL_SCORE_THRESHOLD``'s shipped numeric value
being semantically meaningful. "Above the gate" is engineered by querying with an
indexed chunk's own text (self-similarity ~1.0, robust to any real threshold in
``[0, 1)``); "below the gate" by an unrelated string (near-zero cosine, asserted as a
precondition so the case can never pass vacuously); and the one boundary test overrides
the constant directly with ``monkeypatch``.
"""

from __future__ import annotations

import pytest
from quality_database_app import eval as eval_runner
from quality_database_app import query
from quality_database_app.chunk import Chunk
from quality_database_app.embed import FakeEmbedder
from quality_database_app.evalset import GoldItem
from quality_database_app.index import build_index
from quality_database_app.store import SearchResult, VectorStore

# An unrelated query whose top-1 cosine against the fixtures below sits far under any
# real threshold; the tests that use it assert that precondition rather than trust it.
WEAK_QUERY = "zzz totally unrelated gibberish query string"


def _chunk(**overrides: object) -> Chunk:
    fields: dict[str, object] = {
        "chunk_id": "00000-00",
        "chunk_index": 0,
        "source_id": "msa-4th",
        "region": "whole-document",
        "standard": "MSA Reference Manual",
        "clause": None,
        "page": 78,
        "text": "Gage R&R separates repeatability from reproducibility.",
        "confidence": "high",
        "low_confidence": False,
        "extraction_quality": "clean",
        "serving_flag": "paraphrase-and-point",
        "license_class": "licensed-commercial",
    }
    fields.update(overrides)
    return Chunk(**fields)  # type: ignore[arg-type]


def _store(chunks: list[Chunk]) -> VectorStore:
    return build_index(chunks, FakeEmbedder())


def _locator(chunk: Chunk) -> str:
    return f"[{chunk.source_id}:{chunk.region}:{chunk.page}]"


def _embed_of(text: str) -> list[float]:
    return FakeEmbedder().embed([text])[0]


class _CountingGenerator:
    """A generator that records every call, to prove the gate short-circuits it."""

    def __init__(self, text: str) -> None:
        self.text = text
        self.calls = 0

    def __call__(self, question: str, context: str) -> str:
        self.calls += 1
        return self.text


# --- 1. Grounded, cited, non-refused path -----------------------------------------


def test_grounded_cited_answer_is_not_refused() -> None:
    target = _chunk()
    store = _store([target, _chunk(chunk_id="00001-00", source_id="fmea", page=41)])
    gen = _CountingGenerator(f"Repeatability vs reproducibility. {_locator(target)}")

    answer = query.answer_question(target.text, store, FakeEmbedder(), generate=gen)

    assert answer.refused is False
    assert (answer.cited_source_id, answer.cited_region, answer.cited_page) == (
        target.source_id,
        target.region,
        target.page,
    )
    assert gen.calls == 1


# --- 2. Refusal — empty retrieval, generator never called -------------------------


def test_empty_retrieval_refuses_without_calling_generator() -> None:
    target = _chunk()
    store = _store([target])
    gen = _CountingGenerator(f"whatever {_locator(target)}")

    answer = query.answer_question(
        target.text, store, FakeEmbedder(), generate=gen, standard="no-such-standard"
    )

    assert answer.refused is True
    assert answer.text == query.NOT_FOUND_TEXT
    assert gen.calls == 0


# --- 3. Refusal — weak retrieval, generator never called --------------------------


def test_weak_retrieval_refuses_without_calling_generator() -> None:
    target = _chunk()
    store = _store([target])
    gen = _CountingGenerator(f"whatever {_locator(target)}")

    # Precondition: the weak query really does land under the gate (never vacuous).
    hits = store.search(_embed_of(WEAK_QUERY), k=query.DEFAULT_K)
    assert hits and hits[0].score < query.REFUSAL_SCORE_THRESHOLD

    answer = query.answer_question(WEAK_QUERY, store, FakeEmbedder(), generate=gen)

    assert answer.refused is True
    assert gen.calls == 0


# --- 4. Refusal — hallucinated citation (negative control) ------------------------


def test_hallucinated_citation_refuses() -> None:
    target = _chunk(page=78)
    store = _store([target])
    # Right source_id/region, wrong page -> a locator not among the retrieved hits.
    gen = _CountingGenerator("Answer. [msa-4th:whole-document:999]")

    answer = query.answer_question(target.text, store, FakeEmbedder(), generate=gen)

    assert answer.refused is True
    assert answer.text == query.NOT_FOUND_TEXT


# --- 5. Refusal — no locator cited ------------------------------------------------


def test_no_locator_cited_refuses() -> None:
    target = _chunk()
    store = _store([target])
    gen = _CountingGenerator("A confident answer with no citation at all.")

    answer = query.answer_question(target.text, store, FakeEmbedder(), generate=gen)

    assert answer.refused is True


# --- 6. Quote-cap enforcement (negative control) ----------------------------------


def test_quote_from_non_quotable_chunk_refuses() -> None:
    # serving_flag is paraphrase-and-point: no verbatim excerpt allowed, any span refuses.
    target = _chunk(serving_flag="paraphrase-and-point")
    store = _store([target])
    gen = _CountingGenerator(f'It says "a short excerpt" here. {_locator(target)}')

    answer = query.answer_question(target.text, store, FakeEmbedder(), generate=gen)

    assert answer.refused is True


# --- 7. Quote-cap allows an in-cap quote from a quotable chunk --------------------


def test_in_cap_quote_from_quotable_chunk_is_allowed() -> None:
    target = _chunk(serving_flag="serve")
    store = _store([target])
    gen = _CountingGenerator(f'The manual states "a short excerpt". {_locator(target)}')

    answer = query.answer_question(target.text, store, FakeEmbedder(), generate=gen)

    assert answer.refused is False
    assert answer.cited_page == target.page


# --- 8. Quote-cap still refuses an over-cap quote from a quotable chunk -----------


def test_over_cap_quote_from_quotable_chunk_refuses() -> None:
    target = _chunk(serving_flag="serve")
    store = _store([target])
    # Three sentences -> over the <=2-sentence cap even though it is short.
    gen = _CountingGenerator(
        f'It reads "One point here. Two point here. Three point here." {_locator(target)}'
    )

    answer = query.answer_question(target.text, store, FakeEmbedder(), generate=gen)

    assert answer.refused is True


# --- 9. generate=None with a passing gate raises ValueError -----------------------


def test_passing_gate_without_generator_raises() -> None:
    target = _chunk()
    store = _store([target])

    with pytest.raises(ValueError, match="no default generator"):
        query.answer_question(target.text, store, FakeEmbedder(), generate=None)


# --- 10. page=None locator round-trip ---------------------------------------------


def test_page_none_locator_round_trips() -> None:
    target = _chunk(page=None)
    store = _store([target])
    gen = _CountingGenerator(f"Coarse source, no page. {_locator(target)}")
    # Sanity: the emitted locator carries the literal None token.
    assert _locator(target) == "[msa-4th:whole-document:None]"

    answer = query.answer_question(target.text, store, FakeEmbedder(), generate=gen)

    assert answer.refused is False
    assert answer.cited_page is None


# --- 11. Default item_id determinism ----------------------------------------------


def test_default_item_id_is_deterministic_and_question_specific() -> None:
    store = _store([_chunk()])
    # Empty-retrieval refusal path needs no generator; item_id is still set.
    kwargs = dict(store=store, embedder=FakeEmbedder(), standard="no-such-standard")
    first = query.answer_question("same question", **kwargs)  # type: ignore[arg-type]
    again = query.answer_question("same question", **kwargs)  # type: ignore[arg-type]
    other = query.answer_question("a different question", **kwargs)  # type: ignore[arg-type]

    assert first.item_id == again.item_id
    assert first.item_id != other.item_id
    assert first.item_id == query._default_item_id("same question")


# --- 12. format_context / extract_locators unit tests -----------------------------


def test_extract_locators_zero_one_and_many_tokens() -> None:
    assert query.extract_locators("no tokens here") == []
    assert query.extract_locators("one [a:b:5] token") == [("a", "b", 5)]
    assert query.extract_locators("[a:b:5] then [c:d:None]") == [
        ("a", "b", 5),
        ("c", "d", None),
    ]


def test_extract_locators_ignores_malformed_bracket() -> None:
    # A malformed bracket must not raise and must simply find no locator.
    assert query.extract_locators("[incomplete and [x:y:notanumber]") == []


def test_format_context_stamps_locator_and_serving_flag() -> None:
    hits = [
        SearchResult(chunk=_chunk(page=78, serving_flag="serve"), score=0.9),
        SearchResult(chunk=_chunk(chunk_id="00001-00", page=None), score=0.8),
    ]
    context = query.format_context(hits)

    assert "[msa-4th:whole-document:78] (serving_flag: serve)" in context
    assert "[msa-4th:whole-document:None]" in context
    assert context.count("\n\n") == 1  # one block separator between the two hits


# --- 13. Acceptance loop against the real M4-4 scorers ----------------------------


def _gold_item(item_id: str, chunk: Chunk) -> GoldItem:
    return GoldItem(
        item_id=item_id,
        domain="msa",
        tier="page-pinned",
        question=f"question for {item_id}",
        source_id=chunk.source_id,
        region=chunk.region,
        standard=chunk.standard,
        page=chunk.page,
        serving_flag=chunk.serving_flag,
        answerable=True,
        derived_from="synthetic test fixture",
    )


def _acceptance_fixtures() -> tuple[list[GoldItem], list[Chunk], VectorStore]:
    chunks = [
        _chunk(chunk_id="00000-00", source_id="msa-4th", region="whole-document", page=78),
        _chunk(chunk_id="00001-00", source_id="fmea-2019", region="dfmea", page=41),
    ]
    store = _store(chunks)
    items = [_gold_item("item-0", chunks[0]), _gold_item("item-1", chunks[1])]
    return items, chunks, store


def test_acceptance_loop_scores_perfect_groundedness_and_citation() -> None:
    items, chunks, store = _acceptance_fixtures()
    answers = []
    for item, chunk in zip(items, chunks, strict=True):
        gen = query.answer_question(
            chunk.text,
            store,
            FakeEmbedder(),
            generate=lambda q, ctx, loc=_locator(chunk): f"Grounded answer. {loc}",
            item_id=item.item_id,
        )
        answers.append(gen)

    report = eval_runner.run_generation_eval(items, answers)

    assert all(a.refused is False for a in answers)
    assert report.groundedness_mean == 1.0
    assert report.citation_accuracy_mean == 1.0


def test_acceptance_loop_wrong_citation_drops_the_metric() -> None:
    items, chunks, store = _acceptance_fixtures()
    answers = []
    for index, (item, chunk) in enumerate(zip(items, chunks, strict=True)):
        # Item 0 cites a wrong page: fails locator verification -> refused -> its
        # citation_accuracy scores 0.0 for an answerable item, dragging the mean down.
        page = 12345 if index == 0 else chunk.page
        loc = f"[{chunk.source_id}:{chunk.region}:{page}]"
        gen = query.answer_question(
            chunk.text,
            store,
            FakeEmbedder(),
            generate=lambda q, ctx, loc=loc: f"Answer. {loc}",
            item_id=item.item_id,
        )
        answers.append(gen)

    report = eval_runner.run_generation_eval(items, answers)

    assert answers[0].refused is True
    assert report.citation_accuracy_mean < 1.0


# --- 14. Threshold boundary, via monkeypatch --------------------------------------


def test_gate_reads_module_constant_at_the_boundary(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(query, "REFUSAL_SCORE_THRESHOLD", 0.5)
    above = [SearchResult(chunk=_chunk(), score=0.5000001)]
    below = [SearchResult(chunk=_chunk(), score=0.4999999)]
    at = [SearchResult(chunk=_chunk(), score=0.5)]  # >= is inclusive

    assert query.passes_retrieval_gate(above) is True
    assert query.passes_retrieval_gate(at) is True
    assert query.passes_retrieval_gate(below) is False
    assert query.passes_retrieval_gate([]) is False


# --- 15. derive_threshold self-check (calibration script, fastembed-guarded) ------


def test_derive_threshold_clean_and_overlap_branches() -> None:
    # Importing the calibration module pulls embed_fastembed (the optional `embed`
    # extra); skip cleanly on a machine — like CI — without it.
    calib = pytest.importorskip(
        "quality_database_app.calibrate_refusal_threshold",
        reason="fastembed (the `embed` extra) is not installed",
    )

    threshold, branch = calib.derive_threshold([0.6, 0.7], [0.2, 0.3])
    assert branch == calib.CLEAN_SEPARATION
    assert threshold == (0.6 + 0.3) / 2

    threshold, branch = calib.derive_threshold([0.5], [0.4, 0.6])
    assert branch == calib.OVERLAP
    assert threshold == 0.5

    # Tie-break resolves to the higher candidate (conservative: refuse rather than guess).
    threshold, branch = calib.derive_threshold([0.5, 0.9], [0.5, 0.9])
    assert branch == calib.OVERLAP
    assert threshold == 0.9
