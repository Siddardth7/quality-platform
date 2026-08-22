"""The private hosted RAG endpoint tool (M5-2, #288): ``qdb_answer_question`` + loaders.

Hermetic by construction: no network, no live LLM, no model download, no real corpus.
The store is built in-process with the offline ``FakeEmbedder``; the generator is a fake
``(question, context) -> str`` closure; the embedder loader is only ever exercised with
``FastEmbedEmbedder`` monkeypatched to a stub, so the ``embed`` extra is never needed and
``fastembed`` is never imported.

The three ``lru_cache(maxsize=1)`` loaders (``_load_qdb_store`` / ``_load_qdb_embedder`` /
``_resolve_qdb_generator``) are reset in an autouse fixture so no resolved value leaks
across tests — mandatory, because on a developer machine that has the real corpus
``_load_qdb_store()`` *succeeds*, so a test that forgot to reset would behave differently
here than on CI.
"""

from __future__ import annotations

from typing import Any

import pytest
from fastmcp.exceptions import ToolError
from mcp_app import server
from mcp_app.server import GENERATOR_IMPORT_ENV, qdb_answer_question
from quality_database_app import query
from quality_database_app.chunk import Chunk
from quality_database_app.embed import FakeEmbedder
from quality_database_app.index import build_index
from quality_database_app.schema import IngestionError
from quality_database_app.store import VectorStore

# A unique marker that lives only inside the retrieved chunk's raw text. The corpus-
# never-leaves tests assert it appears in no field of the returned payload.
SENTINEL = "SENTINEL_CHUNK_TEXT_DOES_NOT_LEAVE"

# An unrelated query whose top-1 cosine against the fixtures sits far below any real
# refusal threshold; the refusal tests assert that precondition rather than trust it.
WEAK_QUERY = "zzz totally unrelated gibberish query string"

CORPUS_OUT_ENV = "QUALITY_DATABASE_CORPUS_OUT"


@pytest.fixture(autouse=True)
def _reset_loaders(monkeypatch: pytest.MonkeyPatch):
    """Clear the three lru_cache loaders and the two env vars before every test.

    Clearing at setup (not teardown) is deliberate: a test body may ``monkeypatch`` a
    loader to a plain lambda, and ``monkeypatch`` undoes those *after* this fixture's
    teardown — so reading ``server._load_qdb_store`` at teardown would hit the lambda,
    which has no ``cache_clear``. The real lru_cache objects are restored by
    ``monkeypatch.undo`` and re-cleared by the next test's setup.
    """
    monkeypatch.delenv(GENERATOR_IMPORT_ENV, raising=False)
    monkeypatch.delenv(CORPUS_OUT_ENV, raising=False)
    for loader in (
        server._load_qdb_store,
        server._load_qdb_embedder,
        server._resolve_qdb_generator,
    ):
        loader.cache_clear()


def _chunk(**overrides: object) -> Chunk:
    """One synthetic chunk carrying the sentinel; overridable field by field."""
    fields: dict[str, object] = {
        "chunk_id": "00000-00",
        "chunk_index": 0,
        "source_id": "msa-4th",
        "region": "whole-document",
        "standard": "MSA Reference Manual",
        "clause": None,
        "page": 78,
        "text": f"{SENTINEL} gage r and r separates repeatability from reproducibility",
        "confidence": "high",
        "low_confidence": False,
        "extraction_quality": "clean",
        "serving_flag": "paraphrase-and-point",
        "license_class": "licensed-commercial",
    }
    fields.update(overrides)
    return Chunk(**fields)  # type: ignore[arg-type]


def _locator(chunk: Chunk) -> str:
    return f"[{chunk.source_id}:{chunk.region}:{chunk.page}]"


def _wire(
    monkeypatch: pytest.MonkeyPatch,
    store: VectorStore,
    generate: Any,
    embedder: Any = None,
) -> None:
    """Inject the three loaders the tool reads through module globals."""
    monkeypatch.setattr(server, "_load_qdb_store", lambda: store)
    monkeypatch.setattr(server, "_load_qdb_embedder", lambda: embedder or FakeEmbedder())
    monkeypatch.setattr(server, "_resolve_qdb_generator", lambda: generate)


# The exact six fields CandidateAnswer.model_dump() emits — the wire contract.
_ALLOWED_FIELDS = {
    "item_id",
    "text",
    "cited_source_id",
    "cited_region",
    "cited_page",
    "refused",
}


# ---------------------------------------------------------------------------
# 1. Grounded answer -> cited locators (fake generator, stubbed retrieval)
# ---------------------------------------------------------------------------


def test_grounded_answer_returns_cited_locators(monkeypatch: pytest.MonkeyPatch) -> None:
    target = _chunk()
    store = build_index([target], FakeEmbedder())

    def generate(question: str, context: str) -> str:
        return f"Gage R and R separates repeatability. {_locator(target)}"

    _wire(monkeypatch, store, generate)
    # Querying with the chunk's own text yields self-similarity ~1.0 -> clears the gate
    # for any real threshold in [0, 1); no dependence on the shipped constant's value.
    result = qdb_answer_question(target.text)

    assert set(result) == _ALLOWED_FIELDS
    assert result["refused"] is False
    assert result["cited_source_id"] == target.source_id
    assert result["cited_region"] == target.region
    assert result["cited_page"] == target.page


# ---------------------------------------------------------------------------
# 2. Refusal -> refused=True, no fabricated citation
# ---------------------------------------------------------------------------


def test_refusal_returns_refused_true_and_no_citation(monkeypatch: pytest.MonkeyPatch) -> None:
    target = _chunk()
    store = build_index([target], FakeEmbedder())
    # Precondition: the weak query genuinely scores below the gate, so the refusal is
    # earned, not vacuous.
    hits = store.search(FakeEmbedder().embed([WEAK_QUERY])[0])
    assert not hits or hits[0].score < query.REFUSAL_SCORE_THRESHOLD

    calls: list[tuple[str, str]] = []

    def generate(question: str, context: str) -> str:
        calls.append((question, context))
        return f"fabricated answer {_locator(target)}"

    _wire(monkeypatch, store, generate)
    result = qdb_answer_question(WEAK_QUERY)

    assert result["refused"] is True
    assert result["text"] == query.NOT_FOUND_TEXT
    assert result["cited_source_id"] is None
    assert result["cited_region"] is None
    assert result["cited_page"] is None
    # The gate short-circuits the generator: no fabricated citation could reach the wire.
    assert calls == []


# ---------------------------------------------------------------------------
# 3. Corpus never leaves the server — the load-bearing boundary
# ---------------------------------------------------------------------------


def test_grounded_payload_has_only_the_six_allowed_fields_and_no_raw_chunk(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    target = _chunk()
    store = build_index([target], FakeEmbedder())

    def generate(question: str, context: str) -> str:
        # The generator's own words never echo the raw chunk text (the sentinel).
        return f"A paraphrased answer. {_locator(target)}"

    _wire(monkeypatch, store, generate)
    result = qdb_answer_question(target.text)

    # Exactly the six CandidateAnswer fields cross the wire — no hits, no context, no
    # vectors, no raw chunk text. A regression that added any of those would break this.
    assert set(result) == _ALLOWED_FIELDS
    # The raw chunk text (sentinel) is present in the retrieved context but must not
    # appear anywhere in the returned payload.
    assert SENTINEL not in str(result)
    assert all(SENTINEL not in str(value) for value in result.values())


def test_refusal_payload_carries_no_raw_chunk_text(monkeypatch: pytest.MonkeyPatch) -> None:
    target = _chunk()
    store = build_index([target], FakeEmbedder())
    _wire(monkeypatch, store, lambda q, c: f"unused {_locator(target)}")
    result = qdb_answer_question(WEAK_QUERY)

    assert result["refused"] is True
    assert set(result) == _ALLOWED_FIELDS
    assert SENTINEL not in str(result)


# ---------------------------------------------------------------------------
# 4. ValueError raised inside answer_question -> ToolError via _call
# ---------------------------------------------------------------------------


def test_engine_valueerror_becomes_toolerror(monkeypatch: pytest.MonkeyPatch) -> None:
    target = _chunk()
    store = build_index([target], FakeEmbedder())

    class _WrongWidthEmbedder:
        dimension = 4

        def embed(self, texts: list[str]) -> list[list[float]]:
            # Wrong vector width -> VectorStore.search raises ValueError, which is raised
            # *inside* answer_question (i.e. inside _call) and must surface as ToolError.
            return [[0.0, 0.0, 0.0, 0.0] for _ in texts]

    _wire(monkeypatch, store, lambda q, c: "x", embedder=_WrongWidthEmbedder())
    with pytest.raises(ToolError, match="dimension"):
        qdb_answer_question("anything")


# ---------------------------------------------------------------------------
# 5. The env-var generator resolver — every branch
# ---------------------------------------------------------------------------


def test_generator_unset_raises_toolerror_naming_var(monkeypatch: pytest.MonkeyPatch) -> None:
    # Env deleted by the autouse fixture -> "" -> empty module_name.
    with pytest.raises(ToolError) as exc:
        server._resolve_qdb_generator()
    assert GENERATOR_IMPORT_ENV in str(exc.value)


def test_generator_empty_module_raises(monkeypatch: pytest.MonkeyPatch) -> None:
    # ":fn" -> module_name == "" -> the `not module_name` operand fires.
    monkeypatch.setenv(GENERATOR_IMPORT_ENV, ":fn")
    with pytest.raises(ToolError, match=GENERATOR_IMPORT_ENV):
        server._resolve_qdb_generator()


def test_generator_no_colon_raises(monkeypatch: pytest.MonkeyPatch) -> None:
    # "no-colon-here" -> attribute == "" -> the `not attribute` operand fires.
    monkeypatch.setenv(GENERATOR_IMPORT_ENV, "no-colon-here")
    with pytest.raises(ToolError, match=GENERATOR_IMPORT_ENV):
        server._resolve_qdb_generator()


def test_generator_unresolvable_module_raises_naming_no_value(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv(GENERATOR_IMPORT_ENV, "definitely_not_a_module_xyz:generate")
    with pytest.raises(ToolError) as exc:
        server._resolve_qdb_generator()
    message = str(exc.value)
    assert GENERATOR_IMPORT_ENV in message
    # The message names the exception class, never the path value (secret-hygiene).
    assert "definitely_not_a_module_xyz" not in message
    assert "ModuleNotFoundError" in message or "ImportError" in message


def test_generator_unresolvable_attribute_raises(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(GENERATOR_IMPORT_ENV, "os:this_attribute_does_not_exist")
    with pytest.raises(ToolError) as exc:
        server._resolve_qdb_generator()
    assert "AttributeError" in str(exc.value)


def test_generator_happy_resolve_returns_the_callable(monkeypatch: pytest.MonkeyPatch) -> None:
    # importlib + getattr returns the real object; the resolver does not validate the
    # signature, so any importable "module:function" resolves. json.dumps stands in for
    # an operator-supplied generator — no LLM, no network.
    import json

    monkeypatch.setenv(GENERATOR_IMPORT_ENV, "json:dumps")
    assert server._resolve_qdb_generator() is json.dumps


# ---------------------------------------------------------------------------
# 6. The store / embedder loader bodies
# ---------------------------------------------------------------------------


def test_load_qdb_store_calls_load_index_and_fails_closed(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Any
) -> None:
    # Point the store at an empty dir (no index/ subdir) -> load_index fails closed.
    monkeypatch.setenv(CORPUS_OUT_ENV, str(tmp_path))
    with pytest.raises(IngestionError):
        server._load_qdb_store()


def test_load_qdb_embedder_instantiates_fastembed(monkeypatch: pytest.MonkeyPatch) -> None:
    # Cover `return FastEmbedEmbedder()` without the `embed` extra or a model download by
    # substituting a stub class for FastEmbedEmbedder.
    sentinel = object()
    monkeypatch.setattr(server, "FastEmbedEmbedder", lambda: sentinel)
    assert server._load_qdb_embedder() is sentinel


# ---------------------------------------------------------------------------
# 7. Loader failures become a structured ToolError (reviewer fix, #288)
# ---------------------------------------------------------------------------


def test_missing_corpus_becomes_toolerror(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Any
) -> None:
    """A missing index surfaces as a ``ToolError``, not a raw ``IngestionError``.

    The tool docstring and #288 obligation 6 promise a structured tool error. The loaders
    are resolved inside the tool's own ``try/except`` (not as ``_call`` arguments, which
    would escape before ``_call`` runs), so ``_load_qdb_store()``'s ``IngestionError`` (a
    ``ValueError``) is converted — a client never depends on ``mask_error_details``.
    """
    monkeypatch.setenv(CORPUS_OUT_ENV, str(tmp_path))
    monkeypatch.setenv(GENERATOR_IMPORT_ENV, "json:dumps")
    with pytest.raises(ToolError):
        qdb_answer_question("anything")


def test_missing_embed_extra_becomes_toolerror(monkeypatch: pytest.MonkeyPatch) -> None:
    """A serving process without the ``embed`` extra surfaces as a ``ToolError`` too.

    ``_load_qdb_embedder()`` raises a plain ``ImportError`` (not a ``ValueError``), so the
    tool's ``except`` clause must name ``ImportError`` as well — this arm proves it does.
    The store loader is stubbed past so the embedder is the failing loader.
    """
    def _raise_import_error() -> Any:
        raise ImportError("fastembed is not installed")

    monkeypatch.setattr(server, "_load_qdb_store", lambda: object())
    monkeypatch.setattr(server, "_load_qdb_embedder", _raise_import_error)
    monkeypatch.setenv(GENERATOR_IMPORT_ENV, "json:dumps")
    with pytest.raises(ToolError):
        qdb_answer_question("anything")
