"""Acceptance smoke test for chunking + embedding + retrieval (#284).

Synthetic in-process records only — never the licensed corpus — so this runs on CI,
the same discipline as ``test_pipeline_smoke.py``. It covers the acceptance behaviours
in one pass: a query returns the right chunk with its page/clause/standard intact, a
metadata filter narrows the result set, never-ship chunks are stored but excluded by
default, and re-indexing the same corpus is byte-identical.
"""

import hashlib

import numpy as np
from quality_database_app.chunk import chunk_corpus
from quality_database_app.embed import FakeEmbedder
from quality_database_app.index import build_index
from quality_database_app.schema import SCHEMA_VERSION, Corpus, CorpusEnvelope, CorpusRecord
from quality_database_app.store import METADATA_FILE, VECTORS_FILE, VectorStore


def _record(**overrides):
    fields = {
        "source_id": "fmea-vda-2019",
        "region": "DFMEA-severity-and-AP-prose",
        "standard": "AIAG & VDA FMEA Handbook",
        "clause": "Severity",
        "page": 41,
        "text": "Severity is an estimate of how strongly the effect is felt.",
        "confidence": "high",
        "low_confidence": False,
        "extraction_quality": "clean",
        "serving_flag": "paraphrase-and-point",
        "license_class": "licensed-commercial",
    }
    fields.update(overrides)
    return CorpusRecord(**fields)


def _corpus():
    return Corpus(
        envelope=CorpusEnvelope(schema_version=SCHEMA_VERSION, generated_by="test"),
        records=[
            _record(),
            _record(clause="Occurrence", page=44, text="Occurrence rates the cause frequency."),
            _record(
                source_id="msa-4th",
                region="whole-document",
                standard="MSA Reference Manual",
                clause="Gage R&R",
                page=127,
                text="Gage R&R separates repeatability from reproducibility.",
            ),
            _record(
                region="PFMEA-O-D-tables-and-AP-band-labels",
                clause="Detection table",
                page=9,
                text="Mangled table text that may not be served verbatim.",
                confidence="low",
                low_confidence=True,
                extraction_quality="mangled",
                serving_flag="never-ship",
            ),
        ],
    )


def test_index_search_filters_never_ship_and_is_deterministic(tmp_path):
    corpus = _corpus()
    embedder = FakeEmbedder()
    chunks = chunk_corpus(corpus)

    # One record with no splitting -> one chunk each, in record order.
    assert len(chunks) == len(corpus.records)
    assert [chunk.chunk_id for chunk in chunks] == [
        "00000-00",
        "00001-00",
        "00002-00",
        "00003-00",
    ]

    store = build_index(chunks, embedder)
    store.save(tmp_path / "index")
    loaded = VectorStore.load(tmp_path / "index")

    # (a) a chunk's own vector retrieves that chunk, metadata intact.
    target = chunks[1]
    top = loaded.search(embedder.embed([target.text])[0], k=1)[0]
    assert top.chunk.chunk_id == target.chunk_id
    assert (top.chunk.clause, top.chunk.page, top.chunk.standard) == (
        "Occurrence",
        44,
        "AIAG & VDA FMEA Handbook",
    )
    assert top.score > 0.99

    # (b) the metadata filter narrows to one standard.
    msa = loaded.search(embedder.embed(["anything"])[0], k=10, standard="MSA Reference Manual")
    assert [hit.chunk.source_id for hit in msa] == ["msa-4th"]

    # (c) never-ship is stored, excluded by default, reachable when asked for.
    assert any(chunk.serving_flag == "never-ship" for chunk in loaded.chunks)
    default_hits = loaded.search(embedder.embed(["Mangled table text"])[0], k=10)
    assert all(hit.chunk.serving_flag != "never-ship" for hit in default_hits)
    with_never_ship = loaded.search(
        embedder.embed(["Mangled table text"])[0], k=10, exclude_never_ship=False
    )
    assert any(hit.chunk.serving_flag == "never-ship" for hit in with_never_ship)

    # (d) re-indexing the same corpus rewrites byte-identical files.
    first_metadata = hashlib.sha256((tmp_path / "index" / METADATA_FILE).read_bytes()).hexdigest()
    first_vectors = np.load(tmp_path / "index" / VECTORS_FILE)
    build_index(chunk_corpus(_corpus()), FakeEmbedder()).save(tmp_path / "index")
    assert (
        hashlib.sha256((tmp_path / "index" / METADATA_FILE).read_bytes()).hexdigest()
        == first_metadata
    )
    assert np.array_equal(np.load(tmp_path / "index" / VECTORS_FILE), first_vectors)
