"""Unit tests for store.py (#284) — filters, round-trip, and the loud failures."""

import json

import numpy as np
import pytest
from quality_database_app.chunk import Chunk
from quality_database_app.schema import SCHEMA_VERSION, IngestionError
from quality_database_app.store import METADATA_FILE, VECTORS_FILE, VectorStore


def _chunk(index=0, **overrides):
    fields = {
        "chunk_id": f"0000{index}-00",
        "chunk_index": 0,
        "source_id": "fmea-vda-2019",
        "region": "DFMEA-severity-and-AP-prose",
        "standard": "AIAG & VDA FMEA Handbook",
        "clause": "Severity",
        "page": 41,
        "text": f"text {index}",
        "confidence": "high",
        "low_confidence": False,
        "extraction_quality": "clean",
        "serving_flag": "paraphrase-and-point",
        "license_class": "licensed-commercial",
    }
    fields.update(overrides)
    return Chunk(**fields)


def _store():
    chunks = [
        _chunk(0),
        _chunk(1, source_id="msa-4th", standard="MSA Reference Manual", region="whole-document"),
        _chunk(2, serving_flag="never-ship"),
    ]
    vectors = [[1.0, 0.0], [0.0, 1.0], [1.0, 0.0]]
    return VectorStore.build(chunks, vectors)


def test_search_orders_by_cosine_and_returns_the_whole_chunk():
    hits = _store().search([0.0, 1.0], k=5)
    assert hits[0].chunk.chunk_id == "00001-00"
    assert hits[0].score == pytest.approx(1.0)
    assert hits[0].chunk.page == 41


def test_k_larger_than_the_store_returns_everything_in_scope():
    # The never-ship chunk is excluded by default, so 3 stored -> 2 returned.
    assert len(_store().search([1.0, 0.0], k=99)) == 2


def test_k_truncates():
    assert len(_store().search([1.0, 0.0], k=1, exclude_never_ship=False)) == 1


@pytest.mark.parametrize(
    ("filters", "expected"),
    [
        ({"standard": "MSA Reference Manual"}, ["00001-00"]),
        ({"standard": "Nothing At All"}, []),
        ({"source_id": "msa-4th"}, ["00001-00"]),
        ({"source_id": "nope"}, []),
        ({"region": "whole-document"}, ["00001-00"]),
        ({"region": "nope"}, []),
        ({"exclude_never_ship": False}, ["00000-00", "00002-00", "00001-00"]),
    ],
)
def test_metadata_filters(filters, expected):
    hits = _store().search([1.0, 0.0], k=99, **filters)
    assert [hit.chunk.chunk_id for hit in hits] == expected


def test_never_ship_is_stored_but_excluded_by_default():
    store = _store()
    assert any(chunk.serving_flag == "never-ship" for chunk in store.chunks)
    assert [hit.chunk.chunk_id for hit in store.search([1.0, 0.0], k=99)] == [
        "00000-00",
        "00001-00",
    ]


def test_zero_norm_vectors_score_zero_rather_than_dividing_by_zero():
    store = VectorStore.build([_chunk(0)], [[0.0, 0.0]])
    assert store.search([1.0, 0.0], k=1)[0].score == 0.0


def test_empty_store_round_trips_and_searches_empty(tmp_path):
    store = VectorStore.build([], [])
    assert store.vectors.shape == (0, 0)
    assert store.search([1.0, 0.0]) == []
    store.save(tmp_path)
    assert VectorStore.load(tmp_path).search([1.0, 0.0]) == []


def test_build_rejects_mismatched_lengths():
    with pytest.raises(ValueError, match="1 chunks but 0 vectors"):
        VectorStore.build([_chunk(0)], [])


def test_query_dimension_mismatch_fails_loud():
    with pytest.raises(ValueError, match="3 dimensions"):
        _store().search([1.0, 0.0, 0.0])


def test_save_load_round_trip_preserves_chunks_and_vectors(tmp_path):
    store = _store()
    store.save(tmp_path / "index")
    loaded = VectorStore.load(tmp_path / "index")
    assert loaded.chunks == store.chunks
    assert np.array_equal(loaded.vectors, store.vectors)


def test_load_reports_a_missing_index(tmp_path):
    with pytest.raises(IngestionError, match="could not be read"):
        VectorStore.load(tmp_path)


def test_load_reports_bad_json(tmp_path):
    (tmp_path / METADATA_FILE).write_text("{not json", encoding="utf-8")
    with pytest.raises(IngestionError, match="not valid JSON"):
        VectorStore.load(tmp_path)


def test_load_reports_a_wrong_schema_version(tmp_path):
    (tmp_path / METADATA_FILE).write_text(
        json.dumps({"schema_version": SCHEMA_VERSION + 1, "chunks": []}), encoding="utf-8"
    )
    with pytest.raises(IngestionError, match="schema_version"):
        VectorStore.load(tmp_path)


def test_load_reports_an_invalid_chunk(tmp_path):
    (tmp_path / METADATA_FILE).write_text(
        json.dumps({"schema_version": SCHEMA_VERSION, "chunks": [{"chunk_id": "x"}]}),
        encoding="utf-8",
    )
    with pytest.raises(IngestionError, match="not a valid chunk index"):
        VectorStore.load(tmp_path)


def test_load_reports_a_vector_count_mismatch(tmp_path):
    store = _store()
    store.save(tmp_path)
    payload = json.loads((tmp_path / METADATA_FILE).read_text(encoding="utf-8"))
    payload["chunks"] = payload["chunks"][:1]
    (tmp_path / METADATA_FILE).write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(IngestionError, match="3 vectors for 1 chunks"):
        VectorStore.load(tmp_path)


def test_save_is_byte_identical_on_a_rebuild(tmp_path):
    _store().save(tmp_path)
    first = (tmp_path / METADATA_FILE).read_bytes()
    vectors = np.load(tmp_path / VECTORS_FILE)
    _store().save(tmp_path)
    assert (tmp_path / METADATA_FILE).read_bytes() == first
    assert np.array_equal(np.load(tmp_path / VECTORS_FILE), vectors)
